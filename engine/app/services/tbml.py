"""TBML dashboard service — presentation layer over alerts + trade_transactions.

One service composes four datasets the ``/intelligence/tbml`` page renders:

  1. summary stats (4 tiles)
  2. multi-invoicing groups — same B/L or LC reference at ≥2 distinct orgs
  3. country-pair heatmap — counterparty country aggregation
  4. recent TBML alerts stream

Persona-aware visibility mirrors the cross-bank service: bank persona sees
own-org rows + anonymised peer counts; regulator persona sees the full
picture including bank names.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import AuthenticatedUser
from app.models.alert import Alert
from app.models.org import Organization
from app.models.trade_transaction import TradeTransaction

_DEFAULT_WINDOW_DAYS = 30
_RECENT_ALERTS_LIMIT = 25
_MULTI_INVOICE_LIMIT = 20
_HEATMAP_LIMIT = 12


def _is_regulator(user: AuthenticatedUser) -> bool:
    return (user.org_type or "").lower() == "regulator"


def _now() -> datetime:
    return datetime.now(UTC)


def _window_start(window_days: int) -> datetime:
    return _now() - timedelta(days=max(window_days, 1))


def _as_float(value: object) -> float:
    if value is None:
        return 0.0
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _as_uuid(value: object) -> UUID | None:
    if not value:
        return None
    if isinstance(value, UUID):
        return value
    try:
        return UUID(str(value))
    except (TypeError, ValueError):
        return None


async def _load_org_name_map(session: AsyncSession, org_ids: set[str]) -> dict[str, str]:
    parsed: list[UUID] = []
    for value in org_ids:
        try:
            parsed.append(UUID(value))
        except (TypeError, ValueError):
            continue
    if not parsed:
        return {}
    result = await session.execute(
        select(Organization.id, Organization.name).where(Organization.id.in_(parsed))
    )
    return {str(row_id): str(row_name) for row_id, row_name in result.all()}


def _label_orgs_for_user(
    org_ids: list[str],
    *,
    user: AuthenticatedUser,
    org_name_map: dict[str, str],
) -> list[str]:
    own_org_id = str(user.org_id) if user.org_id else None
    if _is_regulator(user):
        return [org_name_map.get(org_id, org_id) for org_id in org_ids]
    labels: list[str] = []
    peer_index = 1
    for org_id in org_ids:
        if own_org_id and org_id == own_org_id:
            labels.append(org_name_map.get(org_id, "Own institution"))
        else:
            labels.append(f"Peer institution {peer_index}")
            peer_index += 1
    return labels


def _anonymize_match_key(value: str | None, *, user: AuthenticatedUser) -> str:
    if not value:
        return "—"
    if _is_regulator(user):
        return value
    if len(value) <= 4:
        return value
    return f"····{value[-4:]}"


# ---- Stats tiles -------------------------------------------------------


async def _tbml_alert_counts(
    session: AsyncSession,
    *,
    user: AuthenticatedUser,
    window_start: datetime,
) -> dict[str, int]:
    stmt = (
        select(Alert.severity, func.count(Alert.id))
        .where(Alert.source_type == "tbml_scan")
        .where(Alert.created_at >= window_start)
        .group_by(Alert.severity)
    )
    if not _is_regulator(user):
        org_uuid = _as_uuid(user.org_id)
        if org_uuid is not None:
            stmt = stmt.where(Alert.org_id == org_uuid)
    rows = (await session.execute(stmt)).all()
    counts: dict[str, int] = defaultdict(int)
    for severity, count in rows:
        counts[severity] = int(count or 0)
    counts["total"] = sum(counts.values())
    return counts


async def _flagged_trade_count(
    session: AsyncSession,
    *,
    user: AuthenticatedUser,
    window_start: datetime,
) -> int:
    stmt = (
        select(func.count(TradeTransaction.id))
        .where(TradeTransaction.created_at >= window_start)
        .where(TradeTransaction.status == "flagged")
    )
    if not _is_regulator(user):
        org_uuid = _as_uuid(user.org_id)
        if org_uuid is not None:
            stmt = stmt.where(TradeTransaction.org_id == org_uuid)
    return int((await session.execute(stmt)).scalar() or 0)


# ---- Multi-invoicing groups -------------------------------------------


async def _multi_invoicing_groups(
    session: AsyncSession,
    *,
    user: AuthenticatedUser,
    window_start: datetime,
) -> list[dict[str, Any]]:
    """Trades sharing a B/L or LC reference at ≥2 distinct orgs."""
    # Pull recent trades with either a B/L or an LC reference. Regulators
    # see all orgs; bank persona's group surfaces only if their org is in
    # the cluster.
    stmt = (
        select(
            TradeTransaction.id,
            TradeTransaction.org_id,
            TradeTransaction.trade_ref,
            TradeTransaction.bl_number,
            TradeTransaction.lc_reference,
            TradeTransaction.invoice_value,
            TradeTransaction.currency,
            TradeTransaction.counterparty_country,
            TradeTransaction.created_at,
        )
        .where(TradeTransaction.created_at >= window_start)
        .where(
            (TradeTransaction.bl_number.is_not(None))
            | (TradeTransaction.lc_reference.is_not(None))
        )
        .order_by(TradeTransaction.created_at.desc())
        .limit(2000)
    )
    rows = (await session.execute(stmt)).all()

    by_key: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        record = {
            "id": str(row.id),
            "org_id": str(row.org_id),
            "trade_ref": row.trade_ref,
            "bl_number": row.bl_number,
            "lc_reference": row.lc_reference,
            "invoice_value": _as_float(row.invoice_value),
            "currency": row.currency,
            "counterparty_country": row.counterparty_country,
            "created_at": row.created_at.isoformat() if row.created_at else None,
        }
        if row.bl_number:
            by_key[("bl", row.bl_number)].append(record)
        if row.lc_reference:
            by_key[("lc", row.lc_reference)].append(record)

    groups: list[dict[str, Any]] = []
    own_org_id = str(user.org_id) if user.org_id else None
    for (kind, key), trades in by_key.items():
        distinct_orgs = {trade["org_id"] for trade in trades}
        if len(distinct_orgs) < 2:
            continue
        # Bank persona only sees groups their org is part of.
        if not _is_regulator(user) and own_org_id and own_org_id not in distinct_orgs:
            continue
        groups.append(
            {
                "match_kind": kind,
                "match_key": key,
                "distinct_orgs": list(distinct_orgs),
                "trade_count": len(trades),
                "aggregate_invoice_value": sum(t["invoice_value"] for t in trades),
                "currency": trades[0]["currency"],
                "trades": trades,
            }
        )

    groups.sort(key=lambda g: (g["distinct_orgs"].__len__(), g["aggregate_invoice_value"]), reverse=True)
    return groups[:_MULTI_INVOICE_LIMIT]


async def _decorate_multi_invoicing(
    session: AsyncSession,
    *,
    user: AuthenticatedUser,
    groups: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Apply persona-aware org labels + match-key anonymisation."""
    all_org_ids: set[str] = set()
    for group in groups:
        for org_id in group["distinct_orgs"]:
            all_org_ids.add(org_id)
    org_name_map = await _load_org_name_map(session, all_org_ids)
    decorated: list[dict[str, Any]] = []
    for group in groups:
        org_labels = _label_orgs_for_user(
            group["distinct_orgs"], user=user, org_name_map=org_name_map
        )
        decorated.append(
            {
                "match_kind": group["match_kind"],
                "match_key": _anonymize_match_key(group["match_key"], user=user),
                "distinct_orgs_count": len(group["distinct_orgs"]),
                "involved_orgs": org_labels,
                "trade_count": group["trade_count"],
                "aggregate_invoice_value": group["aggregate_invoice_value"],
                "currency": group["currency"],
                "sample_trade_refs": [trade["trade_ref"] for trade in group["trades"][:3]],
            }
        )
    return decorated


# ---- Country-pair heatmap ---------------------------------------------


async def _country_pair_heatmap(
    session: AsyncSession,
    *,
    user: AuthenticatedUser,
    window_start: datetime,
) -> list[dict[str, Any]]:
    """Counterparty country aggregation with flagged-trade overlay."""
    from sqlalchemy import case
    stmt = (
        select(
            TradeTransaction.counterparty_country,
            func.count(TradeTransaction.id).label("trade_count"),
            func.coalesce(func.sum(TradeTransaction.invoice_value), 0).label("total_value"),
            func.coalesce(
                func.sum(case((TradeTransaction.status == "flagged", 1), else_=0)),
                0,
            ).label("flagged_count"),
        )
        .where(TradeTransaction.created_at >= window_start)
        .group_by(TradeTransaction.counterparty_country)
    )
    if not _is_regulator(user):
        org_uuid = _as_uuid(user.org_id)
        if org_uuid is not None:
            stmt = stmt.where(TradeTransaction.org_id == org_uuid)
    stmt = stmt.order_by(func.count(TradeTransaction.id).desc()).limit(_HEATMAP_LIMIT)
    rows = (await session.execute(stmt)).all()
    return [
        {
            "country": str(row.counterparty_country),
            "trade_count": int(row.trade_count or 0),
            "flagged_count": int(row.flagged_count or 0),
            "total_value": _as_float(row.total_value),
        }
        for row in rows
        if row.counterparty_country
    ]


# ---- Recent TBML alerts stream -----------------------------------------


async def _recent_tbml_alerts(
    session: AsyncSession,
    *,
    user: AuthenticatedUser,
    limit: int = _RECENT_ALERTS_LIMIT,
) -> list[dict[str, Any]]:
    stmt = (
        select(
            Alert.id,
            Alert.org_id,
            Alert.alert_type,
            Alert.title,
            Alert.severity,
            Alert.risk_score,
            Alert.status,
            Alert.bfiu_avenue_ref,
            Alert.predicate_offences,
            Alert.linked_trade_id,
            Alert.created_at,
        )
        .where(Alert.source_type == "tbml_scan")
        .order_by(Alert.created_at.desc())
        .limit(limit)
    )
    if not _is_regulator(user):
        org_uuid = _as_uuid(user.org_id)
        if org_uuid is not None:
            stmt = stmt.where(Alert.org_id == org_uuid)
    rows = (await session.execute(stmt)).all()
    return [
        {
            "id": str(row.id),
            "alert_type": row.alert_type,
            "title": row.title,
            "severity": row.severity,
            "risk_score": int(row.risk_score or 0),
            "status": row.status,
            "bfiu_avenue_ref": row.bfiu_avenue_ref,
            "predicate_offences": list(row.predicate_offences or []),
            "linked_trade_id": str(row.linked_trade_id) if row.linked_trade_id else None,
            "created_at": row.created_at.isoformat() if row.created_at else None,
        }
        for row in rows
    ]


# ---- Public entry point ------------------------------------------------


async def build_tbml_summary(
    session: AsyncSession,
    *,
    user: AuthenticatedUser,
    window_days: int = _DEFAULT_WINDOW_DAYS,
) -> dict[str, Any]:
    """Compose every dataset the dashboard needs in one DB round-trip set."""
    window_start = _window_start(window_days)
    alert_counts = await _tbml_alert_counts(session, user=user, window_start=window_start)
    flagged_trade_count = await _flagged_trade_count(session, user=user, window_start=window_start)
    raw_groups = await _multi_invoicing_groups(session, user=user, window_start=window_start)
    multi_invoice = await _decorate_multi_invoicing(session, user=user, groups=raw_groups)
    heatmap = await _country_pair_heatmap(session, user=user, window_start=window_start)
    recent_alerts = await _recent_tbml_alerts(session, user=user)

    return {
        "window_days": window_days,
        "persona_view": "regulator" if _is_regulator(user) else "bank",
        "stats": {
            "total_alerts": alert_counts.get("total", 0),
            "critical_alerts": alert_counts.get("critical", 0),
            "high_alerts": alert_counts.get("high", 0),
            "flagged_trades": flagged_trade_count,
            "multi_invoicing_clusters": len(multi_invoice),
        },
        "multi_invoicing": multi_invoice,
        "country_pair_heatmap": heatmap,
        "recent_alerts": recent_alerts,
    }
