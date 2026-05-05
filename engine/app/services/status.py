"""Public status service (V2 phase 6.1).

Three responsibilities:

  1. Aggregate the latest ``uptime_pings`` per component into the public
     status snapshot (``up`` / ``degraded`` / ``down`` / ``unknown``).
  2. Compute 30-day and 90-day uptime % per component from the same
     ledger.
  3. Surface active + recent ``status_incidents`` for the public page.

All paths are read-only. The Beat task in
``app.tasks.status_tasks.record_uptime_ping`` writes; the admin router
posts incidents.
"""
from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import AuthenticatedUser
from app.models.audit import AuditLog
from app.models.status import StatusIncident, UptimePing

logger = logging.getLogger("kestrel.status")


_COMPONENTS = ("auth", "database", "redis", "storage", "worker", "ai")
_VALID_INCIDENT_SEVERITIES = {"minor", "major", "outage"}
_VALID_INCIDENT_COMPONENTS = {
    "overall",
    "auth",
    "database",
    "redis",
    "storage",
    "worker",
    "ai",
    "web",
    "engine",
}


def _now() -> datetime:
    return datetime.now(UTC)


async def _latest_ping_per_component(session: AsyncSession) -> dict[str, UptimePing]:
    """One query per component is fine — bounded set of ~6."""
    out: dict[str, UptimePing] = {}
    for component in _COMPONENTS:
        result = await session.execute(
            select(UptimePing)
            .where(UptimePing.component == component)
            .order_by(desc(UptimePing.observed_at))
            .limit(1)
        )
        row = result.scalar_one_or_none()
        if row is not None:
            out[component] = row
    return out


async def _uptime_pct(
    session: AsyncSession,
    *,
    component: str,
    window_days: int,
) -> float:
    """Compute ``up_count / (up_count + degraded_count + down_count)`` over
    ``window_days``. Returns 1.0 if there are no pings (degrade gracefully —
    if we have no data, don't claim downtime)."""
    window_start = _now() - timedelta(days=window_days)
    result = await session.execute(
        select(UptimePing.status, func.count())
        .where(UptimePing.component == component)
        .where(UptimePing.observed_at >= window_start)
        .group_by(UptimePing.status)
    )
    counts: dict[str, int] = {row[0]: int(row[1]) for row in result.all()}
    total = counts.get("up", 0) + counts.get("degraded", 0) + counts.get("down", 0)
    if total == 0:
        return 1.0
    return round(counts.get("up", 0) / total, 4)


def _component_status_label(ping: UptimePing | None) -> str:
    if ping is None:
        return "unknown"
    return ping.status


def _overall_status(component_states: dict[str, str]) -> str:
    """Worst-of: down > degraded > up."""
    states = set(component_states.values())
    if "down" in states:
        return "down"
    if "degraded" in states:
        return "degraded"
    if states == {"up"}:
        return "up"
    return "degraded"


async def build_status_summary(session: AsyncSession) -> dict[str, Any]:
    pings = await _latest_ping_per_component(session)
    component_states = {c: _component_status_label(pings.get(c)) for c in _COMPONENTS}

    components: list[dict[str, Any]] = []
    for component in _COMPONENTS:
        ping = pings.get(component)
        components.append(
            {
                "component": component,
                "status": _component_status_label(ping),
                "latency_ms": ping.latency_ms if ping else None,
                "detail": ping.detail if ping else "No ping recorded yet.",
                "observed_at": ping.observed_at.isoformat() if ping and ping.observed_at else None,
                "uptime_30d": await _uptime_pct(session, component=component, window_days=30),
                "uptime_90d": await _uptime_pct(session, component=component, window_days=90),
            }
        )

    incidents_result = await session.execute(
        select(StatusIncident)
        .order_by(desc(StatusIncident.started_at))
        .limit(10)
    )
    incidents = [_incident_to_view(row) for row in incidents_result.scalars().all()]

    overall_30d = round(
        sum(c["uptime_30d"] for c in components) / max(1, len(components)),
        4,
    )

    return {
        "status": _overall_status(component_states),
        "components": components,
        "incidents": incidents,
        "overall_uptime_30d": overall_30d,
        "generated_at": _now().isoformat(),
    }


async def list_incidents(
    session: AsyncSession,
    *,
    active_only: bool = False,
    limit: int = 25,
) -> list[dict[str, Any]]:
    capped = max(1, min(int(limit or 25), 100))
    stmt = select(StatusIncident).order_by(desc(StatusIncident.started_at)).limit(capped)
    if active_only:
        stmt = stmt.where(StatusIncident.ended_at.is_(None))
    result = await session.execute(stmt)
    return [_incident_to_view(row) for row in result.scalars().all()]


async def post_incident(
    session: AsyncSession,
    *,
    user: AuthenticatedUser,
    component: str,
    severity: str,
    summary: str,
    message: str | None = None,
) -> dict[str, Any]:
    if (user.org_type or "").lower() != "regulator":
        raise PermissionError("Only regulator-org admins can post status incidents.")
    if severity not in _VALID_INCIDENT_SEVERITIES:
        raise ValueError(f"Unsupported severity '{severity}'")
    if component not in _VALID_INCIDENT_COMPONENTS:
        raise ValueError(f"Unsupported component '{component}'")
    if not summary or not summary.strip():
        raise ValueError("summary is required")

    posted_by: uuid.UUID | None
    try:
        posted_by = uuid.UUID(str(user.user_id))
    except (TypeError, ValueError):
        posted_by = None

    incident = StatusIncident(
        id=uuid.uuid4(),
        severity=severity,
        component=component,
        summary=summary.strip(),
        message=message.strip() if message else None,
        posted_by=posted_by,
    )
    session.add(incident)
    session.add(
        AuditLog(
            org_id=uuid.UUID(str(user.org_id)),
            user_id=None,
            action="status.incident.post",
            resource_type="status_incident",
            resource_id=incident.id,
            details={"severity": severity, "component": component},
        )
    )
    await session.commit()
    return _incident_to_view(incident)


async def resolve_incident(
    session: AsyncSession,
    *,
    user: AuthenticatedUser,
    incident_id: uuid.UUID,
    message: str | None = None,
) -> dict[str, Any]:
    if (user.org_type or "").lower() != "regulator":
        raise PermissionError("Only regulator-org admins can resolve status incidents.")
    incident = await session.get(StatusIncident, incident_id)
    if incident is None:
        raise LookupError(f"Incident {incident_id} not found")
    incident.ended_at = _now()
    if message:
        # Append to existing message (incidents accrete updates over their lifetime).
        existing = (incident.message or "").rstrip()
        suffix = f"\n\n[Resolved {_now().isoformat()}]\n{message.strip()}"
        incident.message = f"{existing}{suffix}" if existing else suffix.lstrip()
    session.add(
        AuditLog(
            org_id=uuid.UUID(str(user.org_id)),
            user_id=None,
            action="status.incident.resolve",
            resource_type="status_incident",
            resource_id=incident.id,
            details={"resolved_at": incident.ended_at.isoformat()},
        )
    )
    await session.commit()
    return _incident_to_view(incident)


def _incident_to_view(incident: StatusIncident) -> dict[str, Any]:
    return {
        "id": str(incident.id),
        "started_at": incident.started_at.isoformat() if incident.started_at else None,
        "ended_at": incident.ended_at.isoformat() if incident.ended_at else None,
        "severity": incident.severity,
        "component": incident.component,
        "summary": incident.summary,
        "message": incident.message,
        "is_active": incident.ended_at is None,
    }
