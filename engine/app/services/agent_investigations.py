"""Agent investigation service (V3 phase 3.2)."""
from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.investigation_agent import (
    InvestigationResult,
    run_investigation,
)
from app.auth import AuthenticatedUser
from app.models.agent_investigation import AgentInvestigation
from app.models.audit import AuditLog

logger = logging.getLogger("kestrel.agents.service")


def _is_regulator(user: AuthenticatedUser) -> bool:
    return (user.org_type or "").lower() == "regulator"


def _row_to_view(row: AgentInvestigation) -> dict[str, Any]:
    return {
        "id": str(row.id),
        "org_id": str(row.org_id),
        "entity_id": str(row.entity_id) if row.entity_id else None,
        "prompt": row.prompt,
        "status": row.status,
        "hypothesis": row.hypothesis,
        "evidence": list(row.evidence or []),
        "suggested_actions": list(row.suggested_actions or []),
        "confidence": float(row.confidence) if row.confidence is not None else None,
        "hops_used": int(row.hops_used or 0),
        "latency_ms": int(row.latency_ms or 0),
        "error": row.error,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "completed_at": row.completed_at.isoformat() if row.completed_at else None,
    }


async def start_investigation(
    session: AsyncSession,
    *,
    user: AuthenticatedUser,
    entity_id: uuid.UUID | None,
    prompt: str,
) -> dict[str, Any]:
    """Run the investigation agent + persist the result."""
    if not prompt or not prompt.strip():
        raise ValueError("prompt is required")
    result: InvestigationResult = await run_investigation(
        session=session,
        user=user,
        entity_id=entity_id,
        prompt=prompt.strip(),
    )

    # Coerce caller user_id to a UUID if possible — the demo viewer's
    # user_id isn't a UUID so we tolerate that path.
    initiated_by: uuid.UUID | None
    try:
        initiated_by = uuid.UUID(str(user.user_id))
    except (TypeError, ValueError):
        initiated_by = None

    row = AgentInvestigation(
        id=uuid.uuid4(),
        org_id=uuid.UUID(str(user.org_id)),
        entity_id=entity_id,
        initiated_by=initiated_by,
        prompt=prompt.strip(),
        status=result.status,
        hypothesis=result.hypothesis,
        evidence=result.evidence_payload(),
        suggested_actions=list(result.suggested_actions),
        confidence=result.confidence,
        hops_used=result.hops_used,
        latency_ms=result.latency_ms,
        error=result.error,
        completed_at=datetime.now(UTC),
    )
    session.add(row)
    session.add(
        AuditLog(
            org_id=uuid.UUID(str(user.org_id)),
            user_id=None,
            action="agent.investigate",
            resource_type="agent_investigation",
            resource_id=row.id,
            details={
                "entity_id": str(entity_id) if entity_id else None,
                "status": result.status,
                "hops_used": result.hops_used,
                "latency_ms": result.latency_ms,
                "confidence": result.confidence,
                "evidence_count": len(result.evidence),
            },
        )
    )
    await session.commit()
    return _row_to_view(row)


async def list_investigations(
    session: AsyncSession,
    *,
    user: AuthenticatedUser,
    entity_id: uuid.UUID | None = None,
    limit: int = 50,
) -> list[dict[str, Any]]:
    capped = max(1, min(int(limit or 50), 200))
    stmt = select(AgentInvestigation).order_by(desc(AgentInvestigation.created_at)).limit(capped)
    if not _is_regulator(user):
        try:
            org_uuid = uuid.UUID(str(user.org_id))
        except (TypeError, ValueError):
            return []
        stmt = stmt.where(AgentInvestigation.org_id == org_uuid)
    if entity_id is not None:
        stmt = stmt.where(AgentInvestigation.entity_id == entity_id)
    rows = (await session.execute(stmt)).scalars().all()
    return [_row_to_view(r) for r in rows]


async def get_investigation(
    session: AsyncSession,
    *,
    user: AuthenticatedUser,
    investigation_id: uuid.UUID,
) -> dict[str, Any]:
    row = await session.get(AgentInvestigation, investigation_id)
    if row is None:
        raise LookupError(f"Investigation {investigation_id} not found")
    if str(row.org_id) != str(user.org_id) and not _is_regulator(user):
        raise PermissionError("Cannot read another org's investigation")
    return _row_to_view(row)
