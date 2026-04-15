"""Detection rule evaluators.

Each public ``evaluate_*`` function takes:

- ``account``: a ``SimpleNamespace`` or SQLAlchemy ``Account`` with at least
  ``id``, ``account_number``, ``account_name``, ``bank_code``, ``created_at``,
  ``metadata_json``.
- ``account_txns``: list of Transaction-like objects where ``src_account_id``
  or ``dst_account_id`` equals ``account.id``.
- ``rule_config``: the YAML-loaded rule dict.
- ``graph`` + ``flagged_entity_ids``: only used by ``evaluate_proximity_to_bad``.

Each returns ``RuleHit`` on trigger or ``None``.

Determinism: evaluators never read wall-clock time; all temporal reasoning
derives from transaction ``posted_at`` values.
"""

from __future__ import annotations

import uuid
from collections import defaultdict
from datetime import UTC, datetime, timedelta
from typing import Any, Callable, Iterable

import networkx as nx

from app.core.detection.rule_hit import RuleHit


def _txn_dt(txn: Any) -> datetime:
    value = txn.posted_at
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _as_float(value: Any) -> float:
    if value is None:
        return 0.0
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _group_transactions_by_account(
    transactions: Iterable[Any],
) -> dict[uuid.UUID, list[Any]]:
    """Return ``{account_id: [txn, ...]}``.

    Each transaction appears in at most two lists (source and destination).
    """
    grouped: dict[uuid.UUID, list[Any]] = defaultdict(list)
    for txn in transactions:
        src = getattr(txn, "src_account_id", None)
        dst = getattr(txn, "dst_account_id", None)
        if src is not None:
            grouped[src].append(txn)
        if dst is not None and dst != src:
            grouped[dst].append(txn)
    return dict(grouped)


class _DefaultDict(dict):
    def __missing__(self, key: str) -> str:
        return f"{{{key}}}"


def _render_template(template: str, evidence: dict[str, Any]) -> str:
    try:
        return template.format_map(_DefaultDict(evidence))
    except Exception:
        return template


def _account_age_days(account: Any, reference: datetime) -> int:
    created = getattr(account, "created_at", None)
    if created is None:
        return 365
    if created.tzinfo is None:
        created = created.replace(tzinfo=UTC)
    return max(0, (reference - created).days)


def _apply_modifiers(
    rule_config: dict[str, Any],
    modifier_map: dict[str, bool],
) -> tuple[int, list[dict[str, Any]]]:
    base = int(rule_config["scoring"]["base"])
    reasons: list[dict[str, Any]] = []
    for modifier in rule_config["scoring"]["modifiers"]:
        when = modifier["when"]
        if modifier_map.get(when, False):
            base += int(modifier["add"])
            reasons.append(
                {
                    "modifier": when,
                    "score_added": int(modifier["add"]),
                    "reason": modifier["reason"],
                }
            )
    return min(base, 100), reasons


def _sliding_window_groups(
    events: list[Any],
    *,
    window: timedelta,
) -> list[list[Any]]:
    """All maximal sliding windows of ``events`` sorted by time."""
    if not events:
        return []
    events = sorted(events, key=_txn_dt)
    windows: list[list[Any]] = []
    for i in range(len(events)):
        end = _txn_dt(events[i]) + window
        group = [events[i]]
        for j in range(i + 1, len(events)):
            if _txn_dt(events[j]) <= end:
                group.append(events[j])
            else:
                break
        windows.append(group)
    return windows


def _amounts_similar(amounts: list[float], *, tolerance_pct: float = 10.0) -> bool:
    if len(amounts) < 2:
        return False
    mean = sum(amounts) / len(amounts)
    if mean == 0:
        return False
    max_dev = max(abs(a - mean) / mean * 100 for a in amounts)
    return max_dev <= tolerance_pct


def _build_hit(
    *,
    account: Any,
    rule_config: dict[str, Any],
    modifier_map: dict[str, bool],
    evidence: dict[str, Any],
) -> RuleHit:
    score, reasons = _apply_modifiers(rule_config, modifier_map)
    return RuleHit(
        account_id=account.id,
        rule_code=rule_config["code"],
        score=score,
        weight=float(rule_config["weight"]),
        reasons=reasons,
        evidence=evidence,
        alert_title=_render_template(rule_config["alert_template"]["title"], evidence),
        alert_description=_render_template(rule_config["alert_template"]["description"], evidence),
    )


def evaluate_rapid_cashout(
    *,
    account: Any,
    account_txns: list[Any],
    rule_config: dict[str, Any],
) -> RuleHit | None:
    """Fire when a credit is followed by >=X% in debits within the time window."""
    params = rule_config["conditions"]["params"]
    debit_pct_min = float(params["debit_pct_min"])
    time_window = timedelta(minutes=int(params["time_window_minutes"]))
    min_credit = float(params["min_credit_amount"])

    credits = sorted(
        (t for t in account_txns if t.dst_account_id == account.id and _as_float(t.amount) > 0),
        key=_txn_dt,
    )
    if not credits:
        return None

    best_hit: RuleHit | None = None

    for credit in credits:
        credit_amount = _as_float(credit.amount)
        if credit_amount < min_credit:
            continue
        window_end = _txn_dt(credit) + time_window
        following_debits = [
            t
            for t in account_txns
            if t.src_account_id == account.id
            and _txn_dt(t) >= _txn_dt(credit)
            and _txn_dt(t) <= window_end
        ]
        if not following_debits:
            continue
        debit_total = sum(_as_float(t.amount) for t in following_debits)
        debit_pct = (debit_total / credit_amount) * 100 if credit_amount else 0
        if debit_pct < debit_pct_min:
            continue

        last_debit = max(following_debits, key=_txn_dt)
        time_gap_minutes = (_txn_dt(last_debit) - _txn_dt(credit)).total_seconds() / 60

        account_age_days = _account_age_days(account, _txn_dt(credit))
        total_credit = sum(_as_float(t.amount) for t in credits)
        account_bank = getattr(account, "bank_code", None)
        debit_bank_hints: set[str | None] = set()
        for t in following_debits:
            bank = getattr(t, "dst_account_bank_code", None)
            if bank is None:
                meta = getattr(t, "metadata_json", None) or {}
                bank = meta.get("dst_bank_code") if isinstance(meta, dict) else None
            debit_bank_hints.add(bank)
        cross_bank_debit = any(b and b != account_bank for b in debit_bank_hints)

        modifier_map = {
            "time_gap_minutes < 30": time_gap_minutes < 30,
            "total_credit > 1000000": total_credit > 1_000_000,
            "account_age_days < 90": account_age_days < 90,
            "cross_bank_debit == true": cross_bank_debit,
            "proximity_to_flagged <= 2": False,
        }
        # Display debit_pct is capped at 100. The raw value can exceed 100 when
        # the account has unrelated outflows in the same window; the trigger
        # still fires correctly above, the cap is just a UI safeguard.
        evidence = {
            "account_name": getattr(account, "account_name", None) or getattr(account, "account_number", ""),
            "credit_amount": f"{credit_amount:,.0f}",
            "debit_pct": f"{min(debit_pct, 100):.0f}",
            "time_gap": f"{time_gap_minutes:.0f}",
            "debit_channel": getattr(following_debits[0], "channel", None) or "transfer",
            "time_gap_minutes": time_gap_minutes,
            "total_credit": total_credit,
            "account_age_days": account_age_days,
        }
        candidate = _build_hit(
            account=account,
            rule_config=rule_config,
            modifier_map=modifier_map,
            evidence=evidence,
        )
        if best_hit is None or candidate.score > best_hit.score:
            best_hit = candidate

    return best_hit


def evaluate_fan_in_burst(
    *,
    account: Any,
    account_txns: list[Any],
    rule_config: dict[str, Any],
) -> RuleHit | None:
    """Fire when N+ unique senders transfer to this account inside the window."""
    params = rule_config["conditions"]["params"]
    min_senders = int(params["min_unique_senders"])
    window = timedelta(minutes=int(params["time_window_minutes"]))
    min_total = float(params["min_total_amount"])

    credits = [t for t in account_txns if t.dst_account_id == account.id]
    best_hit: RuleHit | None = None

    for group in _sliding_window_groups(credits, window=window):
        unique_senders = {t.src_account_id for t in group if t.src_account_id is not None}
        total_amount = sum(_as_float(t.amount) for t in group)
        if len(unique_senders) < min_senders or total_amount < min_total:
            continue
        amounts = [_as_float(t.amount) for t in group]
        modifier_map = {
            "unique_senders > 10": len(unique_senders) > 10,
            "total_amount > 2000000": total_amount > 2_000_000,
            "senders_from_multiple_banks == true": False,
            "all_similar_amounts == true": _amounts_similar(amounts),
        }
        evidence = {
            "account_name": getattr(account, "account_name", None) or getattr(account, "account_number", ""),
            "unique_senders": len(unique_senders),
            "total_amount": f"{total_amount:,.0f}",
            "time_window": int(params["time_window_minutes"]),
        }
        candidate = _build_hit(
            account=account,
            rule_config=rule_config,
            modifier_map=modifier_map,
            evidence=evidence,
        )
        if best_hit is None or candidate.score > best_hit.score:
            best_hit = candidate
    return best_hit


def evaluate_fan_out_burst(
    *,
    account: Any,
    account_txns: list[Any],
    rule_config: dict[str, Any],
) -> RuleHit | None:
    """Fire when N+ unique recipients receive from this account inside the window."""
    params = rule_config["conditions"]["params"]
    min_recipients = int(params["min_unique_recipients"])
    window = timedelta(minutes=int(params["time_window_minutes"]))
    min_total = float(params["min_total_amount"])

    debits = [t for t in account_txns if t.src_account_id == account.id]
    best_hit: RuleHit | None = None

    for group in _sliding_window_groups(debits, window=window):
        unique = {t.dst_account_id for t in group if t.dst_account_id is not None}
        total_amount = sum(_as_float(t.amount) for t in group)
        if len(unique) < min_recipients or total_amount < min_total:
            continue
        amounts = [_as_float(t.amount) for t in group]
        modifier_map = {
            "unique_recipients > 8": len(unique) > 8,
            "total_amount > 2000000": total_amount > 2_000_000,
            "recipients_at_different_banks == true": False,
            "all_similar_amounts == true": _amounts_similar(amounts),
        }
        evidence = {
            "account_name": getattr(account, "account_name", None) or getattr(account, "account_number", ""),
            "unique_recipients": len(unique),
            "total_amount": f"{total_amount:,.0f}",
            "time_window": int(params["time_window_minutes"]),
        }
        candidate = _build_hit(
            account=account,
            rule_config=rule_config,
            modifier_map=modifier_map,
            evidence=evidence,
        )
        if best_hit is None or candidate.score > best_hit.score:
            best_hit = candidate
    return best_hit


def evaluate_structuring(
    *,
    account: Any,
    account_txns: list[Any],
    rule_config: dict[str, Any],
) -> RuleHit | None:
    """Fire when N+ transactions cluster just under the CTR threshold."""
    params = rule_config["conditions"]["params"]
    threshold = float(params["threshold_amount"])
    margin_pct = float(params["margin_pct"])
    min_count = int(params["min_count"])
    window = timedelta(hours=int(params["time_window_hours"]))

    lower_bound = threshold * (1 - margin_pct / 100)

    candidates = [
        t
        for t in account_txns
        if t.src_account_id == account.id and lower_bound <= _as_float(t.amount) < threshold
    ]
    if len(candidates) < min_count:
        return None

    best_hit: RuleHit | None = None
    for group in _sliding_window_groups(candidates, window=window):
        if len(group) < min_count:
            continue
        amounts = [_as_float(t.amount) for t in group]
        channels = {getattr(t, "channel", None) for t in group}
        avg = sum(amounts) / len(amounts)
        modifier_map = {
            "count > 5": len(group) > 5,
            "same_channel == true": len(channels) == 1 and None not in channels,
            "amounts_tightly_clustered == true": _amounts_similar(amounts, tolerance_pct=2.0),
            "same_day == true": len({_txn_dt(t).date() for t in group}) == 1,
        }
        evidence = {
            "account_name": getattr(account, "account_name", None) or getattr(account, "account_number", ""),
            "count": len(group),
            "avg_amount": f"{avg:,.0f}",
            "hours": int(params["time_window_hours"]),
        }
        candidate = _build_hit(
            account=account,
            rule_config=rule_config,
            modifier_map=modifier_map,
            evidence=evidence,
        )
        if best_hit is None or candidate.score > best_hit.score:
            best_hit = candidate
    return best_hit


def evaluate_layering(
    *,
    account: Any,
    account_txns: list[Any],
    rule_config: dict[str, Any],
) -> RuleHit | None:
    """Fire on clusters of similar-amount transfers within the time window."""
    params = rule_config["conditions"]["params"]
    min_count = int(params["min_transfer_count"])
    variance_pct = float(params["amount_variance_pct"])
    window = timedelta(hours=int(params["time_window_hours"]))
    min_total = float(params["min_total_amount"])

    debits = [t for t in account_txns if t.src_account_id == account.id]
    best_hit: RuleHit | None = None

    for group in _sliding_window_groups(debits, window=window):
        if len(group) < min_count:
            continue
        amounts = [_as_float(t.amount) for t in group]
        total = sum(amounts)
        if total < min_total:
            continue
        if not _amounts_similar(amounts, tolerance_pct=variance_pct):
            continue
        avg = total / len(amounts)
        observed_variance = max(abs(a - avg) / avg * 100 for a in amounts) if avg else 0
        modifier_map = {
            "transfer_count > 10": len(group) > 10,
            "involves_multiple_banks == true": False,
            "amount_variance_pct < 5": observed_variance < 5,
            "circular_flow_detected == true": False,
        }
        evidence = {
            "account_name": getattr(account, "account_name", None) or getattr(account, "account_number", ""),
            "transfer_count": len(group),
            "avg_amount": f"{avg:,.0f}",
            "variance": f"{observed_variance:.1f}",
            "time_window": int(params["time_window_hours"]),
        }
        candidate = _build_hit(
            account=account,
            rule_config=rule_config,
            modifier_map=modifier_map,
            evidence=evidence,
        )
        if best_hit is None or candidate.score > best_hit.score:
            best_hit = candidate
    return best_hit


def evaluate_first_time_high_value(
    *,
    account: Any,
    account_txns: list[Any],
    rule_config: dict[str, Any],
) -> RuleHit | None:
    """Fire on a large first-time transfer from a new account."""
    params = rule_config["conditions"]["params"]
    min_amount = float(params["min_amount"])
    max_age = int(params["max_account_age_days"])

    debits = sorted(
        (t for t in account_txns if t.src_account_id == account.id),
        key=_txn_dt,
    )
    if not debits:
        return None

    best_hit: RuleHit | None = None
    seen_beneficiaries: set[uuid.UUID] = set()
    for txn in debits:
        beneficiary = txn.dst_account_id
        amount = _as_float(txn.amount)
        is_first_time = beneficiary not in seen_beneficiaries
        seen_beneficiaries.add(beneficiary)
        if not is_first_time or amount < min_amount:
            continue
        age = _account_age_days(account, _txn_dt(txn))
        if age > max_age:
            continue

        modifier_map = {
            "amount > 1000000": amount > 1_000_000,
            "beneficiary_at_different_bank == true": False,
            "account_age_days < 30": age < 30,
            "beneficiary_is_flagged == true": False,
        }
        evidence = {
            "account_name": getattr(account, "account_name", None) or getattr(account, "account_number", ""),
            "amount": f"{amount:,.0f}",
            "beneficiary_name": str(beneficiary),
            "account_age": age,
        }
        candidate = _build_hit(
            account=account,
            rule_config=rule_config,
            modifier_map=modifier_map,
            evidence=evidence,
        )
        if best_hit is None or candidate.score > best_hit.score:
            best_hit = candidate
    return best_hit


def evaluate_dormant_spike(
    *,
    account: Any,
    account_txns: list[Any],
    rule_config: dict[str, Any],
) -> RuleHit | None:
    """Fire when a large credit arrives after a dormant period."""
    params = rule_config["conditions"]["params"]
    dormant_days = int(params["dormant_days"])
    min_spike = float(params["min_spike_amount"])

    credits = sorted(
        (t for t in account_txns if t.dst_account_id == account.id),
        key=_txn_dt,
    )
    if len(credits) < 2:
        return None

    best_hit: RuleHit | None = None
    for i in range(1, len(credits)):
        prior_activity = credits[:i]
        spike = credits[i]
        spike_amount = _as_float(spike.amount)
        if spike_amount < min_spike:
            continue
        last_prior = max(prior_activity, key=_txn_dt)
        gap_days = (_txn_dt(spike) - _txn_dt(last_prior)).days
        if gap_days < dormant_days:
            continue

        modifier_map = {
            "spike_amount > 10000000": spike_amount > 10_000_000,
            "multiple_npsb_sources == true": False,
            "dormant_days > 90": gap_days > 90,
            "immediate_outflow == true": False,
        }
        evidence = {
            "account_name": getattr(account, "account_name", None) or getattr(account, "account_number", ""),
            "spike_amount": f"{spike_amount:,.0f}",
            "dormant_days": gap_days,
            "source_count": 1,
        }
        candidate = _build_hit(
            account=account,
            rule_config=rule_config,
            modifier_map=modifier_map,
            evidence=evidence,
        )
        if best_hit is None or candidate.score > best_hit.score:
            best_hit = candidate
    return best_hit


def evaluate_proximity_to_bad(
    *,
    account: Any,
    account_txns: list[Any],
    rule_config: dict[str, Any],
    graph: nx.DiGraph | None = None,
    flagged_entity_ids: set[str] | None = None,
) -> RuleHit | None:
    """Fire when the account's entity is within ``max_hops`` of a flagged entity.

    Requires a prebuilt graph and a set of flagged entity IDs. The pipeline
    passes ``account.metadata_json['entity_id']`` to link accounts to nodes.
    """
    if graph is None or not flagged_entity_ids:
        return None
    params = rule_config["conditions"]["params"]
    max_hops = int(params["max_hops"])

    entity_id = (getattr(account, "metadata_json", {}) or {}).get("entity_id")
    if not entity_id or entity_id not in graph.nodes:
        return None

    undirected = graph.to_undirected()
    best_distance: int | None = None
    flagged_reached: list[str] = []
    for target in flagged_entity_ids:
        if target == entity_id or target not in undirected.nodes:
            continue
        try:
            distance = nx.shortest_path_length(undirected, source=entity_id, target=target)
        except nx.NetworkXNoPath:
            continue
        if distance <= max_hops:
            flagged_reached.append(target)
            if best_distance is None or distance < best_distance:
                best_distance = distance

    if best_distance is None:
        return None

    flagged_name = graph.nodes[flagged_reached[0]].get("label", "flagged entity")
    modifier_map = {
        "hop_distance == 1": best_distance == 1,
        "target_confidence > 0.8": False,
        "multiple_flagged_neighbors == true": len(flagged_reached) > 1,
    }
    evidence = {
        "account_name": getattr(account, "account_name", None) or getattr(account, "account_number", ""),
        "hop_distance": best_distance,
        "flagged_entity_name": flagged_name,
        "confidence": "n/a",
    }
    return _build_hit(
        account=account,
        rule_config=rule_config,
        modifier_map=modifier_map,
        evidence=evidence,
    )


_EVALUATOR_BY_TRIGGER: dict[str, Callable[..., RuleHit | None]] = {
    "credit_then_debit_percentage": evaluate_rapid_cashout,
    "unique_senders_to_recipient": evaluate_fan_in_burst,
    "unique_recipients_from_sender": evaluate_fan_out_burst,
    "sub_threshold_clustering": evaluate_structuring,
    "structured_similar_transfers": evaluate_layering,
    "new_beneficiary_high_value": evaluate_first_time_high_value,
    "balance_spike_after_dormancy": evaluate_dormant_spike,
    "graph_proximity": evaluate_proximity_to_bad,
}


def evaluate_accounts(
    *,
    accounts: list[Any],
    transactions: list[Any],
    rules: list[dict[str, Any]],
    graph: nx.DiGraph | None = None,
    flagged_entity_ids: set[str] | None = None,
) -> list[RuleHit]:
    """Top-level entry point: run every rule against every account.

    Returns a flat list of ``RuleHit`` across all accounts and rules. Callers
    (typically ``pipeline.run_scan_pipeline``) group by account for scoring.
    """
    grouped = _group_transactions_by_account(transactions)
    hits: list[RuleHit] = []
    for account in accounts:
        account_txns = grouped.get(account.id, [])
        for rule in rules:
            trigger = rule["conditions"]["trigger"]
            evaluator = _EVALUATOR_BY_TRIGGER.get(trigger)
            if evaluator is None:
                continue
            if trigger == "graph_proximity":
                hit = evaluator(
                    account=account,
                    account_txns=account_txns,
                    rule_config=rule,
                    graph=graph,
                    flagged_entity_ids=flagged_entity_ids,
                )
            else:
                hit = evaluator(
                    account=account,
                    account_txns=account_txns,
                    rule_config=rule,
                )
            if hit is not None:
                hits.append(hit)
    return hits
