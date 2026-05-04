"""Cross-bank intelligence service — presentation layer over the existing
matches/entities pipeline. The matcher already populates `matches` and emits
cross_bank alerts; this service shapes that data for the dashboard surface.

Persona-aware visibility: bank persona sees own-bank rows in full + anonymised
peer counts; regulator persona sees the full picture including bank names.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import AuthenticatedUser
from app.models.alert import Alert
from app.models.entity import Entity
from app.models.match import Match
from app.models.org import Organization


_DEFAULT_WINDOW_DAYS = 30


def _is_regulator(user: AuthenticatedUser) -> bool:
    return (user.org_type or "").lower() == "regulator"


def _now() -> datetime:
    return datetime.now(UTC)


def _window_start(window_days: int) -> datetime:
    return _now() - timedelta(days=max(window_days, 1))


def _as_float(value: object) -> float:
    if value is None:
        return 0.0
    return float(value)


def _safe_int(value: int | None) -> int:
    return int(value or 0)


def _candidate_org_ids(values: list[Any] | None) -> list[str]:
    return [str(value) for value in (values or []) if value]


async def _load_org_name_map(session: AsyncSession, org_ids: set[str]) -> dict[str, str]:
    parsed: list[UUID] = []
    for value in org_ids:
        try:
            parsed.append(UUID(value))
        except ValueError:
            continue
    if not parsed:
        return {}
    result = await session.execute(select(Organization.id, Organization.name).where(Organization.id.in_(parsed)))
    return {str(row_id): str(row_name) for row_id, row_name in result.all()}


def _label_orgs_for_user(
    org_ids: list[str],
    user: AuthenticatedUser,
    org_name_map: dict[str, str],
) -> list[str]:
    """Regulator sees real bank names. Bank user sees their own bank's name and
    anonymised tokens for peers ('Peer institution 1', 'Peer institution 2', ...)."""
    own_org_id = str(user.org_id) if user.org_id else None
    if _is_regulator(user):
        return [org_name_map.get(org_id, org_id) for org_id in org_ids]

    labels: list[str] = []
    peer_index = 1
    for org_id in org_ids:
        if org_id == own_org_id:
            labels.append(org_name_map.get(org_id, "Your institution"))
        else:
            labels.append(f"Peer institution {peer_index}")
            peer_index += 1
    return labels


def _anonymize_match_key(match_key: str, user: AuthenticatedUser) -> str:
    """Bank persona sees a redacted shape ('account ····1234') for cross-bank
    matches that involve other banks. Regulator sees the full key."""
    if _is_regulator(user) or not match_key:
        return match_key
    if len(match_key) <= 4:
        return "····"
    return f"····{match_key[-4:]}"


async def summarize_cross_bank(
    session: AsyncSession,
    *,
    user: AuthenticatedUser,
    window_days: int = _DEFAULT_WINDOW_DAYS,
) -> dict[str, object]:
    """Top stats row for the cross-bank dashboard."""
    window_start = _window_start(window_days)
    seven_days_ago = _now() - timedelta(days=7)

    # All cross-bank matches in the window
    result = await session.execute(
        select(Match).where(Match.detected_at >= window_start).order_by(Match.detected_at.desc())
    )
    matches = list(result.scalars().all())

    # Cross-bank alerts in the window
    alert_result = await session.execute(
        select(Alert)
        .where(Alert.source_type == "cross_bank", Alert.created_at >= window_start)
        .order_by(Alert.created_at.desc())
    )
    cross_bank_alerts = list(alert_result.scalars().all())

    # Bank-set per match
    own_org_id = str(user.org_id) if user.org_id else None
    matches_involving_user_org: list[Match] = []
    for match in matches:
        org_ids = _candidate_org_ids(match.involved_org_ids)
        if own_org_id and own_org_id in org_ids:
            matches_involving_user_org.append(match)

    visible_matches = matches if _is_regulator(user) else matches_involving_user_org

    entities_in_multiple_banks = sum(
        1 for match in visible_matches if len(_candidate_org_ids(match.involved_org_ids)) >= 2
    )
    new_this_week = sum(
        1
        for match in visible_matches
        if match.detected_at and match.detected_at >= seven_days_ago
    )
    high_risk_cross_institution = sum(
        1
        for match in visible_matches
        if (match.risk_score or 0) >= 70 and len(_candidate_org_ids(match.involved_org_ids)) >= 2
    )
    total_exposure = sum(_as_float(match.total_exposure) for match in visible_matches)

    return {
        "window_days": window_days,
        "entities_flagged_across_banks": entities_in_multiple_banks,
        "new_this_week": new_this_week,
        "high_risk_cross_institution": high_risk_cross_institution,
        "total_exposure": total_exposure,
        "cross_bank_alerts_count": len(cross_bank_alerts) if _is_regulator(user)
            else sum(1 for a in cross_bank_alerts if str(a.org_id) == own_org_id),
        "visible_matches_count": len(visible_matches),
        "persona_view": "regulator" if _is_regulator(user) else "bank",
    }


async def list_cross_bank_matches(
    session: AsyncSession,
    *,
    user: AuthenticatedUser,
    window_days: int = _DEFAULT_WINDOW_DAYS,
    severity: str | None = None,
    min_banks: int = 2,
    limit: int = 50,
) -> list[dict[str, object]]:
    """Recent cross-bank matches with persona-aware anonymisation."""
    window_start = _window_start(window_days)

    stmt = (
        select(Match)
        .where(Match.detected_at >= window_start)
        .order_by(
            Match.risk_score.desc().nullslast(),
            Match.detected_at.desc().nullslast(),
            Match.match_count.desc(),
        )
        .limit(limit)
    )
    if severity:
        stmt = stmt.where(Match.severity == severity)

    result = await session.execute(stmt)
    matches = list(result.scalars().all())

    org_name_map = await _load_org_name_map(
        session,
        {org_id for match in matches for org_id in _candidate_org_ids(match.involved_org_ids)},
    )

    own_org_id = str(user.org_id) if user.org_id else None
    payload: list[dict[str, object]] = []

    for match in matches:
        org_ids = _candidate_org_ids(match.involved_org_ids)
        if len(org_ids) < min_banks:
            continue
        if not _is_regulator(user) and own_org_id and own_org_id not in org_ids:
            # Bank persona only sees matches their own org is part of
            continue

        first_seen_iso = match.detected_at.astimezone(UTC).isoformat() if match.detected_at else None
        payload.append({
            "id": str(match.id),
            "entity_id": str(match.entity_id) if match.entity_id else "",
            "match_key": _anonymize_match_key(match.match_key, user),
            "match_type": match.match_type,
            "involved_orgs": _label_orgs_for_user(org_ids, user, org_name_map),
            "bank_count": len(org_ids),
            "match_count": _safe_int(match.match_count),
            "total_exposure": _as_float(match.total_exposure),
            "risk_score": _safe_int(match.risk_score),
            "severity": match.severity or "low",
            "status": match.status or "new",
            "first_seen": first_seen_iso,
        })

    return payload


async def cross_bank_heatmap(
    session: AsyncSession,
    *,
    user: AuthenticatedUser,
    window_days: int = _DEFAULT_WINDOW_DAYS,
) -> dict[str, object]:
    """Per-bank cross-bank-match counts in the window. For regulator persona,
    returns counts per named bank. For bank persona, returns own-bank count + a
    single 'Peer institutions' aggregate."""
    window_start = _window_start(window_days)

    result = await session.execute(
        select(Match).where(Match.detected_at >= window_start)
    )
    matches = list(result.scalars().all())

    org_name_map = await _load_org_name_map(
        session,
        {org_id for match in matches for org_id in _candidate_org_ids(match.involved_org_ids)},
    )

    own_org_id = str(user.org_id) if user.org_id else None
    per_bank_counts: Counter[str] = Counter()
    valid_severities = {"critical", "high", "medium", "low"}
    severity_buckets: dict[str, dict[str, int]] = defaultdict(
        lambda: {"critical": 0, "high": 0, "medium": 0, "low": 0}
    )

    for match in matches:
        org_ids = _candidate_org_ids(match.involved_org_ids)
        if len(org_ids) < 2:
            continue
        if not _is_regulator(user) and own_org_id and own_org_id not in org_ids:
            continue
        sev = (match.severity or "low").lower()
        if sev not in valid_severities:
            sev = "low"
        for org_id in org_ids:
            if _is_regulator(user):
                label = org_name_map.get(org_id, org_id)
            elif org_id == own_org_id:
                label = org_name_map.get(org_id, "Your institution")
            else:
                label = "Peer institutions"
            per_bank_counts[label] += 1
            severity_buckets[label][sev] += 1

    buckets = []
    for label, count in per_bank_counts.most_common():
        sev_dist = severity_buckets[label]
        buckets.append({
            "label": label,
            "match_count": count,
            "severity_breakdown": sev_dist,
        })

    return {
        "window_days": window_days,
        "buckets": buckets,
        "persona_view": "regulator" if _is_regulator(user) else "bank",
    }


async def list_recent_cross_bank_entities(
    session: AsyncSession,
    *,
    user: AuthenticatedUser,
    window_days: int = _DEFAULT_WINDOW_DAYS,
    limit: int = 12,
) -> list[dict[str, object]]:
    """Top entities flagged across institutions, ranked by risk x bank-count."""
    window_start = _window_start(window_days)

    result = await session.execute(
        select(Match)
        .where(Match.detected_at >= window_start, Match.entity_id.is_not(None))
        .order_by(Match.risk_score.desc().nullslast(), Match.match_count.desc())
        .limit(limit * 3)
    )
    matches = list(result.scalars().all())
    if not matches:
        return []

    entity_ids = [m.entity_id for m in matches if m.entity_id]
    entity_result = await session.execute(select(Entity).where(Entity.id.in_(entity_ids)))
    entities_by_id = {entity.id: entity for entity in entity_result.scalars().all()}

    org_name_map = await _load_org_name_map(
        session,
        {org_id for match in matches for org_id in _candidate_org_ids(match.involved_org_ids)},
    )

    own_org_id = str(user.org_id) if user.org_id else None
    rows: list[dict[str, object]] = []
    seen: set[UUID] = set()
    for match in matches:
        if not match.entity_id or match.entity_id in seen:
            continue
        org_ids = _candidate_org_ids(match.involved_org_ids)
        if len(org_ids) < 2:
            continue
        if not _is_regulator(user) and own_org_id and own_org_id not in org_ids:
            continue
        entity = entities_by_id.get(match.entity_id)
        if entity is None:
            continue
        seen.add(match.entity_id)
        display = entity.display_value if _is_regulator(user) else _anonymize_match_key(entity.display_value, user)
        rows.append({
            "entity_id": str(entity.id),
            "display": display,
            "entity_type": entity.entity_type,
            "risk_score": _safe_int(entity.risk_score),
            "severity": entity.severity or "low",
            "bank_count": len(org_ids),
            "involved_orgs": _label_orgs_for_user(org_ids, user, org_name_map),
            "total_exposure": _as_float(match.total_exposure),
        })
        if len(rows) >= limit:
            break

    return rows
