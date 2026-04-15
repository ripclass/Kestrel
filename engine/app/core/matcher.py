"""Cross-bank matcher.

Detects when a resolved Entity appears in STRs from 2+ different banks and
creates or updates a ``matches`` row plus a ``cross_bank`` alert when the
severity escalates.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.alert import Alert
from app.models.entity import Entity
from app.models.match import Match


def _severity_for(score: int) -> str:
    if score >= 90:
        return "critical"
    if score >= 70:
        return "high"
    if score >= 50:
        return "medium"
    return "low"


def _severity_rank(severity: str | None) -> int:
    return {"low": 0, "medium": 1, "high": 2, "critical": 3}.get(severity or "", 0)


def _compute_match_score(*, match_count: int, total_exposure: float) -> int:
    score = 50 + (10 * match_count)
    if total_exposure > 10_000_000:
        score += 20
    return min(100, score)


async def _find_existing_match(
    session: AsyncSession,
    *,
    match_type: str,
    match_key: str,
) -> Match | None:
    stmt = (
        select(Match)
        .where(Match.match_type == match_type)
        .where(Match.match_key == match_key)
        .limit(1)
    )
    try:
        result = await session.execute(stmt)
        return result.scalars().first()
    except Exception:
        return None


def _build_alert(
    *,
    entity: Entity,
    match: Match,
    org_id: uuid.UUID,
) -> Alert:
    bank_count = match.match_count
    return Alert(
        id=uuid.uuid4(),
        org_id=org_id,
        source_type="cross_bank",
        source_id=match.id,
        entity_id=entity.id,
        title=f"Cross-bank match: {entity.display_value}",
        description=(
            f"{entity.display_name or entity.display_value} has been reported by "
            f"{bank_count} distinct institutions."
        ),
        alert_type="cross_bank_match",
        risk_score=int(match.risk_score or 0),
        severity=match.severity or "low",
        status="open",
        reasons=[
            {
                "rule": "cross_bank",
                "score": int(match.risk_score or 0),
                "explanation": (
                    f"{entity.display_name or entity.display_value} appears in STRs from "
                    f"{bank_count} banks with total exposure BDT "
                    f"{float(entity.total_exposure or 0):,.0f}."
                ),
            }
        ],
    )


async def run_cross_bank_matching(
    session: AsyncSession,
    *,
    entities: list[Entity],
    str_report: Any | None,
    org_id: uuid.UUID,
) -> tuple[list[Match], list[Alert]]:
    """Scan ``entities`` for cross-bank appearances and upsert matches.

    Returns ``(new_or_updated_matches, new_alerts)``. Alerts are only emitted
    when the match is newly created or the severity rank increases. The caller
    owns the surrounding transaction and must commit.
    """
    matches_out: list[Match] = []
    alerts_out: list[Alert] = []
    now = datetime.now(UTC)

    for entity in entities:
        reporting = list(entity.reporting_orgs or [])
        unique_orgs = list(set(reporting))
        if len(unique_orgs) < 2:
            continue

        existing = await _find_existing_match(
            session,
            match_type=entity.entity_type,
            match_key=entity.canonical_value,
        )
        involved_strs: list[uuid.UUID] = []
        if str_report is not None and getattr(str_report, "id", None) is not None:
            involved_strs.append(str_report.id)

        total_exposure = float(entity.total_exposure or 0)
        match_count = len(unique_orgs)
        score = _compute_match_score(match_count=match_count, total_exposure=total_exposure)
        severity = _severity_for(score)
        previous_severity = existing.severity if existing is not None else None

        if existing is None:
            match = Match(
                id=uuid.uuid4(),
                entity_id=entity.id,
                match_key=entity.canonical_value,
                match_type=entity.entity_type,
                involved_org_ids=unique_orgs,
                involved_str_ids=involved_strs,
                match_count=match_count,
                total_exposure=total_exposure,
                risk_score=score,
                severity=severity,
                status="new",
                notes=[],
                detected_at=now,
            )
            session.add(match)
            escalated = True
        else:
            merged_orgs = list({*existing.involved_org_ids, *unique_orgs})
            merged_strs = list({*existing.involved_str_ids, *involved_strs})
            existing.involved_org_ids = merged_orgs
            existing.involved_str_ids = merged_strs
            existing.match_count = len(merged_orgs)
            existing.total_exposure = max(float(existing.total_exposure or 0), total_exposure)
            existing.risk_score = _compute_match_score(
                match_count=existing.match_count,
                total_exposure=float(existing.total_exposure),
            )
            existing.severity = _severity_for(existing.risk_score)
            existing.detected_at = now
            match = existing
            escalated = _severity_rank(match.severity) > _severity_rank(previous_severity)

        matches_out.append(match)

        if escalated:
            alerts_out.append(_build_alert(entity=entity, match=match, org_id=org_id))

    for alert in alerts_out:
        session.add(alert)
    if matches_out or alerts_out:
        await session.flush()

    return matches_out, alerts_out
