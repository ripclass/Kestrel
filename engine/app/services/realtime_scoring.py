"""Real-time per-transaction scoring (V2 phase 3.1).

Decisioning surface for `POST /transactions/score`. Optimised for sub-500ms
end-to-end latency: read-only against the shared entity + matches tables,
in-memory rule evaluation, no entity upserts and no transaction writes from
the scoring path itself. Every call is persisted to ``realtime_scoring_log``
and ``audit_log`` for audit + the eventual ML feedback loop.

Decision bands (from `KESTREL-WORLD-CLASS-BUILD-V2.md` Phase 3 Task 3.1):

    score < 30          -> approve
    30 <= score < 60    -> review
    60 <= score < 80    -> hold
    score >= 80         -> reject

The score is composed from explainable rule-style contributions: amount
thresholds, channel/rail risk, age signals from supplied account metadata,
existing entity risk-scores in the shared intelligence pool, and cross-bank
match signals. Each contribution is recorded as a reason in the response.
"""

from __future__ import annotations

import logging
import time
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import Integer, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import AuthenticatedUser
from app.core.resolver import normalize_identifier
from app.models.audit import AuditLog
from app.models.entity import Entity
from app.models.match import Match
from app.models.realtime_scoring import RealtimeScoringLog
from app.observability import current_request_id
from app.services.screening import (
    ScreeningMatch,
    ScreeningRequest,
    parse_screening_date,
    screen_entity,
)

logger = logging.getLogger("kestrel.realtime")


# Thresholds tuned for BDT-denominated retail + corporate flows. These can be
# made configurable per bank tier in Phase 6.2; for v1 they are global.
_LARGE_AMOUNT_BDT = 1_000_000          # 10 lakh
_VERY_LARGE_AMOUNT_BDT = 5_000_000     # 50 lakh
_STRUCTURING_FLOOR_BDT = 900_000       # within 10% of CTR threshold
_STRUCTURING_CEILING_BDT = 1_000_000
_NEW_ACCOUNT_DAYS = 30

_HIGH_RISK_CHANNELS = {"CASH", "CHEQUE", "DRAFT"}
_MEDIUM_RISK_CHANNELS = {"MFS_BKASH", "MFS_NAGAD", "MFS_ROCKET"}

_DECISION_APPROVE_MAX = 30
_DECISION_REVIEW_MAX = 60
_DECISION_HOLD_MAX = 80

# Sanctions screening: a hit at or above this similarity-weighted score
# forces a 50-point contribution. Two hits (both parties) push the score
# past the rejection band even if every other signal is benign.
_SANCTIONS_HIT_THRESHOLD = 0.7
_SANCTIONS_HIT_POINTS = 50

# ---- TBML modifiers (Phase B) --------------------------------------------
# Read from the transaction metadata's `trade` block. Keep in sync with the
# trade_evaluator high-risk list (DEFAULT_HIGH_RISK_JURISDICTIONS) so the
# batch scan and the realtime path classify the same jurisdictions.
_TBML_HIGH_RISK_JURISDICTIONS = frozenset({"IR", "KP", "SY", "VE", "MM", "CU"})

# LC variants per migration 027 — when transaction-level metadata names one
# of these, we know we're scoring an LC-backed leg.
_TBML_LC_PAYMENT_MODES = frozenset({
    "lc_sight",
    "lc_usance",
    "lc_btb",
    "lc_transferable",
    "lc_standby",
    "lc_red_clause",
})

# Non-LC modes that we treat as elevated TBML risk on trade-shaped transactions.
_TBML_NON_LC_RISKY_MODES = frozenset({"open_account", "cash_in_advance"})

# Trigger TBML modifiers only when the transaction looks trade-shaped:
# channel is LC/WIRE/CARD, OR the metadata contains explicit trade keys.
_TBML_TRADE_CHANNELS = frozenset({"LC", "WIRE", "CARD"})

# HS-code anomaly thresholds — same shape as the batch rule but tuned for
# inline single-transaction scoring (more conservative).
_TBML_OVER_INVOICE_RATIO = 2.0     # invoice / market_ref >= 2x
_TBML_UNDER_INVOICE_RATIO = 0.5    # invoice / market_ref <= 0.5x


@dataclass
class RealtimeScoringRequest:
    """Inbound payload normalised into a dataclass before scoring."""

    transaction_id: str
    from_account: str
    to_account: str
    amount: float
    channel: str
    transaction_type: str  # credit | debit
    currency: str = "BDT"
    from_account_metadata: dict[str, Any] | None = None
    to_account_metadata: dict[str, Any] | None = None
    timestamp: datetime | None = None


@dataclass
class RealtimeScoringResult:
    """Structured output, mirrors the JSON contract documented in the V2 prompt."""

    score: int
    decision: str
    confidence: float
    reasons: list[dict[str, Any]]
    evidence: dict[str, Any]
    cross_bank_flag: bool
    request_id: str
    latency_ms: int
    log_id: str


def _decide(score: int) -> str:
    if score < _DECISION_APPROVE_MAX:
        return "approve"
    if score < _DECISION_REVIEW_MAX:
        return "review"
    if score < _DECISION_HOLD_MAX:
        return "hold"
    return "reject"


def _confidence_from_signals(reasons: list[dict[str, Any]]) -> float:
    """Confidence is a normalized signal density (more independent reasons =>
    higher confidence in the decision). Capped at 0.95 because we're never
    100% sure on a single transaction."""
    if not reasons:
        return 0.5
    return min(0.5 + 0.08 * len(reasons), 0.95)


def _account_age_days(metadata: dict[str, Any] | None, *, reference: datetime) -> int | None:
    if not metadata:
        return None
    raw = metadata.get("account_open_date") or metadata.get("opened_at")
    if not raw:
        return None
    try:
        opened = datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None
    if opened.tzinfo is None:
        opened = opened.replace(tzinfo=UTC)
    return max(0, (reference - opened).days)


def _add_reason(
    reasons: list[dict[str, Any]],
    *,
    rule: str,
    points: int,
    reason_text: str,
    detail: dict[str, Any] | None = None,
) -> int:
    """Append a contribution and return the points (so the caller can accumulate)."""
    entry: dict[str, Any] = {
        "rule": rule,
        "score": int(points),
        "reason_text": reason_text,
    }
    if detail:
        entry["detail"] = detail
    reasons.append(entry)
    return int(points)


def _normalize_for_lookup(entity_type: str, raw: str | None) -> str | None:
    if not raw:
        return None
    try:
        return normalize_identifier(entity_type, raw)
    except ValueError:
        return None


async def _lookup_entities(
    session: AsyncSession,
    *,
    canonicals: list[str],
) -> dict[str, Entity]:
    """One read-only query for all parties' entity rows. Keyed by canonical_value."""
    if not canonicals:
        return {}
    stmt = (
        select(Entity)
        .where(Entity.entity_type == "account")
        .where(Entity.canonical_value.in_(canonicals))
    )
    result = await session.execute(stmt)
    return {entity.canonical_value: entity for entity in result.scalars().all()}


async def _lookup_matches(
    session: AsyncSession,
    *,
    canonicals: list[str],
) -> dict[str, Match]:
    """Cross-bank match rows for either party. Keyed by match_key."""
    if not canonicals:
        return {}
    stmt = (
        select(Match)
        .where(Match.match_type == "account")
        .where(Match.match_key.in_(canonicals))
    )
    result = await session.execute(stmt)
    return {match.match_key: match for match in result.scalars().all()}


def _score_amount(
    amount: float, reasons: list[dict[str, Any]], evidence: dict[str, Any]
) -> int:
    """Amount-band contributions + the structuring sub-threshold rule."""
    contribution = 0
    if amount >= _VERY_LARGE_AMOUNT_BDT:
        contribution += _add_reason(
            reasons,
            rule="amount_very_large",
            points=40,
            reason_text=f"Transaction amount BDT {amount:,.0f} exceeds 50 lakh.",
            detail={"amount": amount, "threshold": _VERY_LARGE_AMOUNT_BDT},
        )
    elif amount >= _LARGE_AMOUNT_BDT:
        contribution += _add_reason(
            reasons,
            rule="amount_large",
            points=20,
            reason_text=f"Transaction amount BDT {amount:,.0f} exceeds 10 lakh.",
            detail={"amount": amount, "threshold": _LARGE_AMOUNT_BDT},
        )
    elif _STRUCTURING_FLOOR_BDT <= amount < _STRUCTURING_CEILING_BDT:
        contribution += _add_reason(
            reasons,
            rule="structuring_suspect",
            points=30,
            reason_text=(
                f"Amount BDT {amount:,.0f} sits within 10% of the CTR threshold — "
                f"possible structuring."
            ),
            detail={
                "amount": amount,
                "floor": _STRUCTURING_FLOOR_BDT,
                "ceiling": _STRUCTURING_CEILING_BDT,
            },
        )
    evidence["amount_band"] = (
        "very_large" if amount >= _VERY_LARGE_AMOUNT_BDT
        else "large" if amount >= _LARGE_AMOUNT_BDT
        else "structuring_band" if _STRUCTURING_FLOOR_BDT <= amount < _STRUCTURING_CEILING_BDT
        else "normal"
    )
    return contribution


def _score_channel(
    channel: str, reasons: list[dict[str, Any]], evidence: dict[str, Any]
) -> int:
    code = (channel or "").upper()
    evidence["channel"] = code
    if code in _HIGH_RISK_CHANNELS:
        return _add_reason(
            reasons,
            rule="channel_cash_like",
            points=15,
            reason_text=f"Channel {code} carries elevated AML risk (cash-like rail).",
            detail={"channel": code},
        )
    if code in _MEDIUM_RISK_CHANNELS:
        return _add_reason(
            reasons,
            rule="channel_mfs",
            points=8,
            reason_text=f"Channel {code} is a mobile-financial-services rail.",
            detail={"channel": code},
        )
    return 0


def _score_account_age(
    metadata: dict[str, Any] | None,
    amount: float,
    *,
    reference: datetime,
    reasons: list[dict[str, Any]],
    evidence: dict[str, Any],
) -> int:
    age_days = _account_age_days(metadata, reference=reference)
    if age_days is None:
        return 0
    evidence["from_account_age_days"] = age_days
    if age_days < _NEW_ACCOUNT_DAYS and amount >= _LARGE_AMOUNT_BDT:
        return _add_reason(
            reasons,
            rule="new_account_high_value",
            points=20,
            reason_text=(
                f"Originating account opened {age_days} days ago is sending "
                f"BDT {amount:,.0f}."
            ),
            detail={"account_age_days": age_days, "amount": amount},
        )
    return 0


def _score_entity_risk(
    *,
    entity: Entity | None,
    side: str,
    reasons: list[dict[str, Any]],
    evidence: dict[str, Any],
) -> int:
    """Pull a contribution from the shared-pool entity risk_score, if any.
    Bank persona only sees their own bank's exposure to this entity through
    the scoring API — the entity risk_score is itself derived from STRs and
    cross-bank matches across the system, so reading it here is the cross-
    institutional signal a single-bank scorer otherwise has no access to."""
    if entity is None:
        return 0
    score = int(entity.risk_score or 0)
    evidence[f"{side}_entity_risk_score"] = score
    evidence[f"{side}_entity_severity"] = entity.severity
    if score < 50:
        return 0
    points = int(min(30, max(10, round(score * 0.3))))
    return _add_reason(
        reasons,
        rule=f"{side}_entity_flagged",
        points=points,
        reason_text=(
            f"{side.capitalize()} party is a known flagged entity "
            f"(severity={entity.severity or 'medium'}, risk_score={score})."
        ),
        detail={"entity_id": str(entity.id), "severity": entity.severity, "risk_score": score},
    )


def _score_cross_bank(
    *,
    match: Match | None,
    side: str,
    reasons: list[dict[str, Any]],
    evidence: dict[str, Any],
) -> int:
    if match is None:
        return 0
    bank_count = int(match.match_count or 0)
    risk = int(match.risk_score or 0)
    evidence[f"{side}_cross_bank_count"] = bank_count
    if bank_count < 2:
        return 0
    points = 15 if bank_count == 2 else 25
    return _add_reason(
        reasons,
        rule=f"{side}_cross_bank_flagged",
        points=points,
        reason_text=(
            f"{side.capitalize()} party is reported by {bank_count} institutions "
            f"(cross-bank match severity={match.severity or 'low'}, "
            f"risk_score={risk})."
        ),
        detail={
            "match_id": str(match.id),
            "bank_count": bank_count,
            "risk_score": risk,
            "severity": match.severity,
        },
    )


def _trade_block(metadata: dict[str, Any] | None) -> dict[str, Any]:
    """Pluck the optional `trade` sub-dict out of party metadata.

    Bank integrations carry the trade context — HS code, country, payment
    mode, invoice + market reference values — under a stable `trade` key
    inside the per-side metadata. We accept either side and merge; the
    most-recent non-None wins for each key.
    """
    if not isinstance(metadata, dict):
        return {}
    raw = metadata.get("trade")
    if not isinstance(raw, dict):
        return {}
    return raw


def _merge_trade_context(
    from_meta: dict[str, Any] | None,
    to_meta: dict[str, Any] | None,
) -> dict[str, Any]:
    merged: dict[str, Any] = {}
    for side_meta in (_trade_block(from_meta), _trade_block(to_meta)):
        for key, value in side_meta.items():
            if value is None or value == "":
                continue
            merged.setdefault(key, value)
    return merged


def _score_tbml_payment_mode(
    *,
    channel: str,
    trade: dict[str, Any],
    amount: float,
    reasons: list[dict[str, Any]],
    evidence: dict[str, Any],
) -> int:
    """LC-vs-open-account modifier.

    Open-account or cash-in-advance settlement on trade-shaped transactions
    above 5 lakh BDT picks up 15 points — settlement without bank-to-bank
    documentary verification is the highest TBML-risk payment mode per the
    BFIU TBML Guidelines.
    """
    payment_mode = (trade.get("payment_mode") or "").lower()
    upper_channel = (channel or "").upper()
    is_trade = upper_channel in _TBML_TRADE_CHANNELS or bool(trade)
    if not is_trade:
        return 0
    if payment_mode in _TBML_NON_LC_RISKY_MODES and amount >= 500_000:
        evidence["tbml_payment_mode"] = payment_mode
        return _add_reason(
            reasons,
            rule="tbml_payment_mode_open_account",
            points=15,
            reason_text=(
                f"Trade payment via {payment_mode} above 5 lakh BDT — no bank-to-bank "
                f"documentary verification, elevated TBML risk per BFIU TBML Guidelines."
            ),
            detail={
                "payment_mode": payment_mode,
                "channel": upper_channel,
                "amount": amount,
            },
        )
    return 0


def _score_tbml_hs_code_anomaly(
    *,
    trade: dict[str, Any],
    reasons: list[dict[str, Any]],
    evidence: dict[str, Any],
) -> int:
    """HS-code anomaly modifier.

    When the trade context carries both invoice and market-reference values
    on a known HS code, flag invoice/market ratios outside [0.5, 2.0] as
    over- or under-invoicing. Mirror of the batch ``over_invoicing`` and
    ``under_invoicing`` detection rules — same predicate offences apply.
    """
    invoice = trade.get("invoice_value")
    market_ref = trade.get("market_reference_value")
    hs_code = trade.get("hs_code")
    try:
        inv = float(invoice) if invoice is not None else 0.0
        ref = float(market_ref) if market_ref is not None else 0.0
    except (TypeError, ValueError):
        return 0
    if inv <= 0 or ref <= 0:
        return 0
    ratio = inv / ref
    if ratio >= _TBML_OVER_INVOICE_RATIO:
        evidence["tbml_invoice_to_market_ratio"] = round(ratio, 2)
        return _add_reason(
            reasons,
            rule="tbml_hs_code_over_invoicing",
            points=25,
            reason_text=(
                f"Invoice value {inv:,.0f} is {ratio:.1f}x the HS-{hs_code} market "
                f"reference {ref:,.0f} — over-invoicing red flag (BFIU §2.4.1.iv)."
            ),
            detail={"invoice_value": inv, "market_reference_value": ref, "hs_code": hs_code, "ratio": round(ratio, 2)},
        )
    if ratio <= _TBML_UNDER_INVOICE_RATIO:
        evidence["tbml_invoice_to_market_ratio"] = round(ratio, 2)
        return _add_reason(
            reasons,
            rule="tbml_hs_code_under_invoicing",
            points=25,
            reason_text=(
                f"Invoice value {inv:,.0f} is {ratio:.1f}x the HS-{hs_code} market "
                f"reference {ref:,.0f} — under-invoicing / duty evasion red flag (BFIU §2.4.1.iv)."
            ),
            detail={"invoice_value": inv, "market_reference_value": ref, "hs_code": hs_code, "ratio": round(ratio, 2)},
        )
    return 0


def _score_tbml_country_pair(
    *,
    trade: dict[str, Any],
    reasons: list[dict[str, Any]],
    evidence: dict[str, Any],
) -> int:
    """Country-pair plausibility modifier.

    A counterparty country in the global high-risk list (Iran, North Korea,
    Syria, Venezuela, Myanmar, Cuba per BFIU + UN sanctions overlay) adds 20
    points. Same list as the batch transshipment_routing rule for
    consistency across the two paths.
    """
    counterparty_country = (trade.get("counterparty_country") or "").upper()
    if not counterparty_country:
        return 0
    if counterparty_country in _TBML_HIGH_RISK_JURISDICTIONS:
        evidence["tbml_counterparty_country"] = counterparty_country
        return _add_reason(
            reasons,
            rule="tbml_country_pair_high_risk",
            points=20,
            reason_text=(
                f"Counterparty in high-risk jurisdiction {counterparty_country} — "
                f"FATF / BFIU listed for AML or sanctions concern."
            ),
            detail={"counterparty_country": counterparty_country},
        )
    return 0


def _score_trade_context(
    *,
    request: "RealtimeScoringRequest",
    reasons: list[dict[str, Any]],
    evidence: dict[str, Any],
) -> int:
    """Compose the three TBML modifiers for one transaction.

    Returns total points contributed. No side effects beyond appending
    to ``reasons`` and writing trade-context keys onto ``evidence``.
    """
    trade = _merge_trade_context(
        request.from_account_metadata, request.to_account_metadata
    )
    if not trade:
        return 0
    evidence["tbml_trade_context"] = True
    score = 0
    score += _score_tbml_payment_mode(
        channel=request.channel,
        trade=trade,
        amount=request.amount,
        reasons=reasons,
        evidence=evidence,
    )
    score += _score_tbml_hs_code_anomaly(trade=trade, reasons=reasons, evidence=evidence)
    score += _score_tbml_country_pair(trade=trade, reasons=reasons, evidence=evidence)
    return score


async def _screen_party(
    session: AsyncSession,
    *,
    metadata: dict[str, Any] | None,
) -> list[ScreeningMatch]:
    """Run sanctions screening for one transaction party.

    Returns an empty list when the metadata doesn't carry a name (most
    machine-to-machine integrations send NID + account number only — no
    screening is possible without a candidate name). Bounded by the
    `screen_entity` query (200 rows max from the watchlist pool); typical
    latency stays well within the realtime budget.
    """
    if not metadata or not isinstance(metadata, dict):
        return []
    name = metadata.get("name") or metadata.get("full_name")
    if not name or not str(name).strip():
        return []
    request = ScreeningRequest(
        name=str(name),
        date_of_birth=parse_screening_date(
            metadata.get("date_of_birth") or metadata.get("dob")
        ),
        nationality=metadata.get("nationality"),
        nid=metadata.get("nid") or metadata.get("national_id"),
        passport=metadata.get("passport"),
        minimum_match_score=_SANCTIONS_HIT_THRESHOLD,
    )
    return await screen_entity(session, request=request)


def _score_sanctions(
    *,
    matches: list[ScreeningMatch],
    side: str,
    reasons: list[dict[str, Any]],
    evidence: dict[str, Any],
) -> int:
    if not matches:
        return 0
    top = matches[0]
    evidence[f"{side}_sanctions_hit"] = {
        "list_source": top.list_source,
        "match_score": top.match_score,
        "matched_name": top.matched_name,
    }
    return _add_reason(
        reasons,
        rule=f"{side}_sanctions_hit",
        points=_SANCTIONS_HIT_POINTS,
        reason_text=(
            f"{side.capitalize()} party matches {top.list_source} watchlist entry "
            f"'{top.matched_name}' (score={top.match_score:.2f})."
        ),
        detail={
            "list_source": top.list_source,
            "list_version": top.list_version,
            "entry_id": top.entry_id,
            "match_score": top.match_score,
            "match_reasons": top.match_reasons,
            "additional_hits": len(matches) - 1,
        },
    )


async def score_transaction(
    session: AsyncSession,
    *,
    user: AuthenticatedUser,
    request: RealtimeScoringRequest,
) -> RealtimeScoringResult:
    """Score one transaction. Read-only against shared intel; persists log row."""
    started_at = time.perf_counter()
    reference = request.timestamp or datetime.now(UTC)
    if reference.tzinfo is None:
        reference = reference.replace(tzinfo=UTC)
    request_id = current_request_id() or uuid.uuid4().hex

    from_canonical = _normalize_for_lookup("account", request.from_account)
    to_canonical = _normalize_for_lookup("account", request.to_account)

    canonicals = [c for c in {from_canonical, to_canonical} if c]
    entities_by_canonical = await _lookup_entities(session, canonicals=canonicals)
    matches_by_canonical = await _lookup_matches(session, canonicals=canonicals)

    reasons: list[dict[str, Any]] = []
    evidence: dict[str, Any] = {
        "from_account_canonical": from_canonical,
        "to_account_canonical": to_canonical,
        "transaction_type": request.transaction_type,
    }

    score = 0
    score += _score_amount(request.amount, reasons, evidence)
    score += _score_channel(request.channel, reasons, evidence)
    score += _score_account_age(
        request.from_account_metadata,
        request.amount,
        reference=reference,
        reasons=reasons,
        evidence=evidence,
    )
    score += _score_entity_risk(
        entity=entities_by_canonical.get(from_canonical or ""),
        side="from",
        reasons=reasons,
        evidence=evidence,
    )
    score += _score_entity_risk(
        entity=entities_by_canonical.get(to_canonical or ""),
        side="to",
        reasons=reasons,
        evidence=evidence,
    )
    from_match = matches_by_canonical.get(from_canonical or "")
    to_match = matches_by_canonical.get(to_canonical or "")
    score += _score_cross_bank(match=from_match, side="from", reasons=reasons, evidence=evidence)
    score += _score_cross_bank(match=to_match, side="to", reasons=reasons, evidence=evidence)
    cross_bank_flag = bool(from_match) or bool(to_match)

    from_sanctions = await _screen_party(session, metadata=request.from_account_metadata)
    to_sanctions = await _screen_party(session, metadata=request.to_account_metadata)
    score += _score_sanctions(matches=from_sanctions, side="from", reasons=reasons, evidence=evidence)
    score += _score_sanctions(matches=to_sanctions, side="to", reasons=reasons, evidence=evidence)
    sanctions_flag = bool(from_sanctions) or bool(to_sanctions)
    if sanctions_flag:
        evidence["sanctions_flag"] = True

    # TBML trade-context modifiers — fires only when the per-side metadata
    # carries a `trade` sub-dict (HS code, country, payment_mode, etc.).
    # Pure function — no DB lookup, no extra latency.
    score += _score_trade_context(request=request, reasons=reasons, evidence=evidence)

    score = max(0, min(100, score))
    decision = _decide(score)
    confidence = _confidence_from_signals(reasons)
    latency_ms = int(round((time.perf_counter() - started_at) * 1000))

    log = RealtimeScoringLog(
        id=uuid.uuid4(),
        org_id=uuid.UUID(str(user.org_id)),
        transaction_external_id=request.transaction_id,
        request_payload={
            "transaction_id": request.transaction_id,
            "from_account": request.from_account,
            "to_account": request.to_account,
            "amount": request.amount,
            "currency": request.currency,
            "channel": request.channel,
            "transaction_type": request.transaction_type,
            "from_account_metadata": request.from_account_metadata or {},
            "to_account_metadata": request.to_account_metadata or {},
            "timestamp": reference.isoformat(),
        },
        score=score,
        decision=decision,
        reasons=reasons,
        cross_bank_flag=cross_bank_flag,
        latency_ms=latency_ms,
        request_id=request_id,
        feedback_received=False,
    )
    session.add(log)

    session.add(
        AuditLog(
            org_id=uuid.UUID(str(user.org_id)),
            user_id=None,
            action="realtime.score",
            resource_type="realtime_scoring_log",
            resource_id=log.id,
            details={
                "transaction_external_id": request.transaction_id,
                "score": score,
                "decision": decision,
                "cross_bank_flag": cross_bank_flag,
                "latency_ms": latency_ms,
                "request_id": request_id,
            },
        )
    )
    await session.flush()
    await session.commit()

    logger.info(
        "realtime.score",
        extra={
            "transaction_external_id": request.transaction_id,
            "org_id": str(user.org_id),
            "score": score,
            "decision": decision,
            "cross_bank_flag": cross_bank_flag,
            "latency_ms": latency_ms,
            "reason_count": len(reasons),
        },
    )

    return RealtimeScoringResult(
        score=score,
        decision=decision,
        confidence=round(confidence, 2),
        reasons=reasons,
        evidence=evidence,
        cross_bank_flag=cross_bank_flag,
        request_id=request_id,
        latency_ms=latency_ms,
        log_id=str(log.id),
    )


async def record_feedback(
    session: AsyncSession,
    *,
    user: AuthenticatedUser,
    log_id: uuid.UUID,
    outcome: str,
    note: str | None = None,
) -> dict[str, Any]:
    """Bank reports the ground-truth outcome for a previously scored transaction.

    Foundation for the ML loop in the sovereign-AI track. RLS enforces that a
    bank can only update its own org's log rows; we additionally guard at the
    service layer so the engine surfaces a clean 404 vs. a generic RLS error.
    """
    if outcome not in {"legitimate", "fraud", "unsure"}:
        raise ValueError(f"Unsupported outcome '{outcome}'")
    log = await session.get(RealtimeScoringLog, log_id)
    if log is None:
        raise LookupError(f"Scoring log {log_id} not found")
    if str(log.org_id) != str(user.org_id) and (user.org_type or "").lower() != "regulator":
        raise PermissionError("Cannot edit feedback on another org's scoring log")
    log.feedback_received = True
    log.feedback_outcome = outcome
    log.feedback_at = datetime.now(UTC)
    detail: dict[str, Any] = {"outcome": outcome}
    if note:
        detail["note"] = note
    session.add(
        AuditLog(
            org_id=uuid.UUID(str(user.org_id)),
            user_id=None,
            action="realtime.feedback",
            resource_type="realtime_scoring_log",
            resource_id=log.id,
            details=detail,
        )
    )
    await session.commit()

    return {
        "id": str(log.id),
        "feedback_received": True,
        "feedback_outcome": outcome,
        "feedback_at": log.feedback_at.isoformat(),
    }


def _percentile(values: list[int], pct: float) -> int:
    """Linear-interpolated percentile. ``pct`` is 0-100. Returns 0 on empty."""
    if not values:
        return 0
    if len(values) == 1:
        return int(values[0])
    ordered = sorted(values)
    rank = (pct / 100.0) * (len(ordered) - 1)
    lo = int(rank)
    hi = min(lo + 1, len(ordered) - 1)
    weight = rank - lo
    return int(round(ordered[lo] * (1 - weight) + ordered[hi] * weight))


async def build_realtime_metrics(
    session: AsyncSession,
    *,
    user: AuthenticatedUser,
    window_hours: int = 24,
    top_limit: int = 5,
) -> dict[str, Any]:
    """Aggregate metrics for the Phase 3.4 monitoring dashboard.

    - decision distribution + counts in the window
    - latency p50 / p95 / p99 across the window
    - top scored transactions in the last hour (by score, then by recency)
    - cross-bank flagged count in the window

    Persona-aware: bank persona sees its own org. Regulator persona sees the
    cross-system aggregate. Read-only against ``realtime_scoring_log``.
    """
    now = datetime.now(UTC)
    window = max(1, min(int(window_hours or 24), 168))  # 1h ≤ window ≤ 7 days
    window_start = now - timedelta(hours=window)
    last_hour = now - timedelta(hours=1)

    is_regulator = (user.org_type or "").lower() == "regulator"

    base_filters = [RealtimeScoringLog.created_at >= window_start]
    if not is_regulator:
        try:
            org_uuid = uuid.UUID(str(user.org_id))
        except (TypeError, ValueError):
            return {
                "window_hours": window,
                "total": 0,
                "decisions": {"approve": 0, "review": 0, "hold": 0, "reject": 0},
                "cross_bank_flag_count": 0,
                "latency_ms": {"p50": 0, "p95": 0, "p99": 0, "avg": 0},
                "top_recent": [],
                "persona_view": "bank",
            }
        base_filters.append(RealtimeScoringLog.org_id == org_uuid)

    # Decision distribution + cross-bank flag count + simple counters.
    counter_stmt = (
        select(
            RealtimeScoringLog.decision,
            func.count().label("count"),
            func.sum(
                func.cast(RealtimeScoringLog.cross_bank_flag, Integer)
            ).label("cross_bank_count"),
        )
        .where(*base_filters)
        .group_by(RealtimeScoringLog.decision)
    )
    decision_counts = {"approve": 0, "review": 0, "hold": 0, "reject": 0}
    cross_bank_count = 0
    total = 0
    result = await session.execute(counter_stmt)
    for row in result.all():
        decision = row[0] or "approve"
        count = int(row[1] or 0)
        cross_bank = int(row[2] or 0)
        decision_counts[decision] = decision_counts.get(decision, 0) + count
        cross_bank_count += cross_bank
        total += count

    # Latency percentiles — pull all latencies in the window. Bounded by the
    # window cap above, so this stays tight at our scale (single bank tenants
    # generate well under ten thousand calls per day in v1).
    latency_stmt = select(RealtimeScoringLog.latency_ms).where(*base_filters)
    latency_result = await session.execute(latency_stmt)
    latencies = [int(value or 0) for (value,) in latency_result.all()]
    latency_payload = {
        "p50": _percentile(latencies, 50),
        "p95": _percentile(latencies, 95),
        "p99": _percentile(latencies, 99),
        "avg": int(round(sum(latencies) / len(latencies))) if latencies else 0,
    }

    # Top scored transactions in the last hour (or window, whichever is shorter)
    top_window_start = max(last_hour, window_start)
    top_stmt = (
        select(RealtimeScoringLog)
        .where(*base_filters)
        .where(RealtimeScoringLog.created_at >= top_window_start)
        .order_by(
            RealtimeScoringLog.score.desc(),
            RealtimeScoringLog.created_at.desc(),
        )
        .limit(max(1, min(int(top_limit or 5), 25)))
    )
    top_rows = (await session.execute(top_stmt)).scalars().all()
    top_recent = [
        {
            "id": str(row.id),
            "transaction_external_id": row.transaction_external_id,
            "score": int(row.score),
            "decision": row.decision,
            "cross_bank_flag": bool(row.cross_bank_flag),
            "latency_ms": int(row.latency_ms),
            "created_at": row.created_at.isoformat() if row.created_at else None,
        }
        for row in top_rows
    ]

    return {
        "window_hours": window,
        "total": total,
        "decisions": decision_counts,
        "cross_bank_flag_count": cross_bank_count,
        "latency_ms": latency_payload,
        "top_recent": top_recent,
        "persona_view": "regulator" if is_regulator else "bank",
        "generated_at": now.isoformat(),
    }


async def list_recent_scores(
    session: AsyncSession,
    *,
    user: AuthenticatedUser,
    limit: int = 50,
) -> list[dict[str, Any]]:
    """Recent scoring rows for the caller's org (or all orgs for regulator).

    Backs the Phase 3.4 monitoring dashboard. Persona-aware: bank persona sees
    only its own org; regulator sees the cross-system stream.
    """
    stmt = select(RealtimeScoringLog).order_by(RealtimeScoringLog.created_at.desc()).limit(limit)
    if (user.org_type or "").lower() != "regulator":
        stmt = stmt.where(RealtimeScoringLog.org_id == uuid.UUID(str(user.org_id)))
    result = await session.execute(stmt)
    rows = list(result.scalars().all())
    return [
        {
            "id": str(row.id),
            "transaction_external_id": row.transaction_external_id,
            "score": int(row.score),
            "decision": row.decision,
            "cross_bank_flag": bool(row.cross_bank_flag),
            "latency_ms": int(row.latency_ms),
            "feedback_received": bool(row.feedback_received),
            "feedback_outcome": row.feedback_outcome,
            "created_at": row.created_at.isoformat() if row.created_at else None,
        }
        for row in rows
    ]
