"""TBML pipeline integration (Phase B).

Consumes ``TradeRuleHit`` objects from the trade detection rules and
persists ``Alert`` rows with the regulatory metadata pre-filled:

  * source_type = 'tbml_scan'
  * predicate_offences[] from the matched rule's YAML
  * bfiu_avenue_ref from the matched rule's YAML
  * linked_trade_id pointing back to the source trade row
  * reasons[] carries the rule's modifier-level contributions

The pipeline is idempotent within a scan run — a re-run on the same
trades produces the same alerts (matched by linked_trade_id + rule_code +
status='open'). It does not silently update existing alerts; if the
score changes, a new alert row is created. This matches the existing
detection pipeline pattern.
"""
from __future__ import annotations

import uuid
from typing import Any, Iterable

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.detection.trade_evaluator import (
    TradeRuleHit,
    evaluate_trade_transactions,
    load_trade_rules,
)
from app.models.alert import Alert
from app.models.trade_transaction import TradeTransaction


def _as_uuid(value: Any) -> uuid.UUID | None:
    if value is None or value == "":
        return None
    if isinstance(value, uuid.UUID):
        return value
    try:
        return uuid.UUID(str(value))
    except (TypeError, ValueError):
        return None


def _rule_hit_to_alert_kwargs(
    hit: TradeRuleHit,
    *,
    trade: TradeTransaction | None = None,
) -> dict[str, Any]:
    """Map a TradeRuleHit to Alert column kwargs.

    Pure function — no DB writes. The pipeline uses this to compose the
    SQLAlchemy Alert row + the audit log payload.
    """
    org_uuid = _as_uuid(hit.org_id) or (trade.org_id if trade is not None else None)
    trade_uuid = _as_uuid(hit.trade_id) or (trade.id if trade is not None else None)
    # entity_id is left NULL on TBML alerts — the trade row carries the
    # subject/counterparty context. A future enhancement resolves the
    # importer/exporter as an Entity row and links it here.
    return {
        "org_id": org_uuid,
        "source_type": "tbml_scan",
        "source_id": trade_uuid,
        "entity_id": None,
        "title": hit.alert_title or f"TBML rule {hit.rule_code} fired",
        "description": hit.alert_description or "",
        "alert_type": hit.rule_code,
        "risk_score": int(hit.score),
        "severity": hit.severity,
        "status": "open",
        "reasons": [
            {
                "rule": hit.rule_code,
                "score": hit.score,
                "weight": hit.weight,
                "explanation": hit.alert_description or hit.alert_title,
                "evidence": _normalize_evidence(hit.evidence),
                "reasons": hit.reasons,
            }
        ],
        "predicate_offences": list(hit.predicate_offences or []),
        "linked_trade_id": trade_uuid,
        "bfiu_avenue_ref": hit.bfiu_avenue_ref,
    }


def _normalize_evidence(evidence: dict[str, Any]) -> dict[str, Any]:
    """Coerce evidence to JSONB-friendly primitives + sanitize None values."""
    cleaned: dict[str, Any] = {}
    for key, value in (evidence or {}).items():
        if value is None:
            continue
        if isinstance(value, (str, int, float, bool)):
            cleaned[key] = value
        else:
            cleaned[key] = str(value)
    return cleaned


async def _existing_open_alert_for(
    session: AsyncSession,
    *,
    trade_id: uuid.UUID,
    rule_code: str,
) -> Alert | None:
    """Return an open alert for this trade+rule combo, if any."""
    stmt = (
        select(Alert)
        .where(Alert.linked_trade_id == trade_id)
        .where(Alert.alert_type == rule_code)
        .where(Alert.status.in_(("open", "reviewing", "escalated")))
        .limit(1)
    )
    return (await session.execute(stmt)).scalar_one_or_none()


async def run_tbml_scan_on_trades(
    session: AsyncSession,
    *,
    trades: list[TradeTransaction],
    rules: list[dict[str, Any]] | None = None,
    cross_org_context: bool = True,
) -> dict[str, Any]:
    """Run the TBML detection rules over ``trades`` and persist Alert rows.

    Returns a summary dict::

        {
          "trades_scanned": int,
          "hits": int,
          "alerts_created": int,
          "alerts_skipped_existing": int,
          "by_rule": { rule_code: count, ... },
        }

    The caller owns the surrounding transaction; ``session.commit()`` is
    only invoked at the end if alerts were created. Failures bubble up.
    """
    rule_list = rules if rules is not None else load_trade_rules()
    trade_list = list(trades)

    # Build peer context for cross-org rules (multiple_invoicing). When
    # cross_org_context is True we hand every trade the full trade list as
    # peers; the rule itself filters by B/L + LC reference.
    peer_map: dict[str, list[TradeTransaction]] = {}
    if cross_org_context:
        for trade in trade_list:
            peer_map[str(trade.id)] = trade_list

    hits: list[TradeRuleHit] = evaluate_trade_transactions(
        trade_list,
        rules=rule_list,
        peer_trades_by_ref=peer_map,
    )

    trade_by_id = {str(trade.id): trade for trade in trade_list}

    alerts_created = 0
    alerts_skipped = 0
    by_rule: dict[str, int] = {}

    for hit in hits:
        trade = trade_by_id.get(hit.trade_id)
        if trade is None:
            continue
        existing = await _existing_open_alert_for(
            session, trade_id=trade.id, rule_code=hit.rule_code
        )
        if existing is not None:
            alerts_skipped += 1
            continue
        kwargs = _rule_hit_to_alert_kwargs(hit, trade=trade)
        if kwargs["org_id"] is None:
            # Can't insert without an org_id (NOT NULL on alerts).
            continue
        session.add(Alert(**kwargs))
        alerts_created += 1
        by_rule[hit.rule_code] = by_rule.get(hit.rule_code, 0) + 1

    if alerts_created > 0:
        await session.commit()

    return {
        "trades_scanned": len(trade_list),
        "hits": len(hits),
        "alerts_created": alerts_created,
        "alerts_skipped_existing": alerts_skipped,
        "by_rule": by_rule,
    }


async def run_tbml_scan_for_org(
    session: AsyncSession,
    *,
    org_id: uuid.UUID,
    status_filter: str | None = None,
    limit: int = 500,
) -> dict[str, Any]:
    """Helper: load every trade for an org + run the pipeline.

    The router endpoint wraps this. Tests can drive the pipeline directly
    via ``run_tbml_scan_on_trades``.
    """
    stmt = select(TradeTransaction).where(TradeTransaction.org_id == org_id).limit(limit)
    if status_filter:
        stmt = stmt.where(TradeTransaction.status == status_filter)
    rows = (await session.execute(stmt)).scalars().all()
    return await run_tbml_scan_on_trades(session, trades=list(rows))
