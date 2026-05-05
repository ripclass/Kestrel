"""Tool whitelist for the investigation agent (V3 phase 3.1).

Each tool is a small async function bound to existing Kestrel services.
The agent loop dispatches by name; anything off the whitelist is
refused. Returns are bounded — the loop's context-summariser further
trims them before re-feeding to the AI.

Pattern: every tool returns a ``ToolResult`` with ``payload`` (dict that
serialises to JSON) and optional ``error``. Failure modes (missing
entity, RLS denied, validation error) become bounded payloads, not
exceptions — the agent loop has its own catch-all defence-in-depth.
"""
from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import AuthenticatedUser
from app.models.alert import Alert
from app.models.connection import Connection
from app.models.entity import Entity
from app.models.str_report import STRReport
from app.services.screening import ScreeningRequest, screen_entity

logger = logging.getLogger("kestrel.agents.tools")


@dataclass(slots=True)
class ToolCall:
    name: str
    args: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class ToolResult:
    payload: dict[str, Any]
    error: str | None = None


ToolFn = Callable[..., Awaitable[ToolResult]]


def _parse_uuid(value: Any) -> uuid.UUID | None:
    if not value:
        return None
    try:
        return uuid.UUID(str(value))
    except (TypeError, ValueError):
        return None


def _entity_summary(entity: Entity) -> dict[str, Any]:
    return {
        "id": str(entity.id),
        "entity_type": entity.entity_type,
        "display_value": entity.display_value,
        "display_name": entity.display_name,
        "risk_score": int(entity.risk_score or 0),
        "severity": entity.severity,
        "status": entity.status,
        "reporting_org_count": len(entity.reporting_orgs or []),
        "report_count": int(entity.report_count or 0),
    }


# --- Tool implementations --------------------------------------------------


async def resolve_entity_tool(
    *,
    session: AsyncSession,
    user: AuthenticatedUser,
    args: dict[str, Any],
) -> ToolResult:
    """Resolve an entity by id. Returns the dossier-flavour summary
    used as hop-0 evidence and as the seed for downstream tools."""
    entity_id = _parse_uuid(args.get("entity_id"))
    if entity_id is None:
        return ToolResult(payload={"refused": True}, error="entity_id is required and must be a UUID")
    entity = await session.get(Entity, entity_id)
    if entity is None:
        return ToolResult(payload={"missing": True}, error="Entity not found")
    return ToolResult(payload=_entity_summary(entity))


async def neighbours_tool(
    *,
    session: AsyncSession,
    user: AuthenticatedUser,
    args: dict[str, Any],
) -> ToolResult:
    """One-hop neighbours via the connections graph. Bounded at 12 to
    keep the AI context manageable."""
    entity_id = _parse_uuid(args.get("entity_id"))
    if entity_id is None:
        return ToolResult(payload={"neighbours": [], "refused": True}, error="entity_id required")
    limit = max(1, min(int(args.get("limit", 12) or 12), 25))

    out_stmt = (
        select(Connection)
        .where(Connection.from_entity_id == entity_id)
        .limit(limit)
    )
    in_stmt = (
        select(Connection)
        .where(Connection.to_entity_id == entity_id)
        .limit(limit)
    )
    out_rows = list((await session.execute(out_stmt)).scalars().all())
    in_rows = list((await session.execute(in_stmt)).scalars().all())

    neighbour_ids: dict[uuid.UUID, str] = {}
    for c in out_rows:
        if c.to_entity_id is not None:
            neighbour_ids[c.to_entity_id] = c.relation
    for c in in_rows:
        if c.from_entity_id is not None and c.from_entity_id not in neighbour_ids:
            neighbour_ids[c.from_entity_id] = c.relation

    if not neighbour_ids:
        return ToolResult(payload={"neighbours": []})

    ent_rows = (
        await session.execute(select(Entity).where(Entity.id.in_(neighbour_ids.keys())))
    ).scalars().all()

    return ToolResult(
        payload={
            "neighbours": [
                {
                    **_entity_summary(e),
                    "relation": neighbour_ids.get(e.id),
                }
                for e in ent_rows
            ],
        }
    )


async def recent_alerts_tool(
    *,
    session: AsyncSession,
    user: AuthenticatedUser,
    args: dict[str, Any],
) -> ToolResult:
    entity_id = _parse_uuid(args.get("entity_id"))
    if entity_id is None:
        return ToolResult(payload={"alerts": [], "refused": True}, error="entity_id required")
    limit = max(1, min(int(args.get("limit", 5) or 5), 25))
    rows = (
        await session.execute(
            select(Alert)
            .where(Alert.entity_id == entity_id)
            .order_by(desc(Alert.created_at))
            .limit(limit)
        )
    ).scalars().all()
    return ToolResult(
        payload={
            "alerts": [
                {
                    "id": str(a.id),
                    "title": a.title,
                    "alert_type": a.alert_type,
                    "severity": a.severity,
                    "status": a.status,
                    "risk_score": int(a.risk_score or 0),
                    "created_at": a.created_at.isoformat() if a.created_at else None,
                }
                for a in rows
            ],
        }
    )


async def recent_strs_tool(
    *,
    session: AsyncSession,
    user: AuthenticatedUser,
    args: dict[str, Any],
) -> ToolResult:
    entity_id = _parse_uuid(args.get("entity_id"))
    if entity_id is None:
        return ToolResult(payload={"strs": [], "refused": True}, error="entity_id required")
    limit = max(1, min(int(args.get("limit", 5) or 5), 25))
    rows = (
        await session.execute(
            select(STRReport)
            .where(STRReport.matched_entity_ids.any(entity_id))
            .order_by(desc(STRReport.created_at))
            .limit(limit)
        )
    ).scalars().all()
    return ToolResult(
        payload={
            "strs": [
                {
                    "id": str(r.id),
                    "report_ref": r.report_ref,
                    "report_type": r.report_type,
                    "status": r.status,
                    "subject_name": r.subject_name,
                    "created_at": r.created_at.isoformat() if r.created_at else None,
                }
                for r in rows
            ],
        }
    )


async def screen_entity_tool(
    *,
    session: AsyncSession,
    user: AuthenticatedUser,
    args: dict[str, Any],
) -> ToolResult:
    name = (args.get("name") or "").strip()
    if not name:
        return ToolResult(payload={"matches": [], "refused": True}, error="name required")
    request = ScreeningRequest(
        name=name,
        nationality=args.get("nationality"),
        nid=args.get("nid"),
        passport=args.get("passport"),
        minimum_match_score=float(args.get("minimum_match_score", 0.7) or 0.7),
    )
    matches = await screen_entity(session, request=request)
    return ToolResult(
        payload={
            "matches": [
                {
                    "list_source": m.list_source,
                    "matched_name": m.matched_name,
                    "match_score": float(m.match_score),
                    "match_reasons": list(m.match_reasons),
                }
                for m in matches
            ],
        }
    )


async def build_narrative_tool(
    *,
    session: AsyncSession,
    user: AuthenticatedUser,
    args: dict[str, Any],
) -> ToolResult:
    """Compose a draft STR narrative seed from the entity's exposure +
    cross-bank flags. The agent's evidence-so-far is the better seed,
    but this gives the AI a deterministic starter when called as a
    final step before `done`."""
    entity_id = _parse_uuid(args.get("entity_id"))
    if entity_id is None:
        return ToolResult(payload={"narrative_seed": "", "refused": True}, error="entity_id required")
    entity = await session.get(Entity, entity_id)
    if entity is None:
        return ToolResult(payload={"narrative_seed": "", "missing": True}, error="entity not found")
    seed = (
        f"{entity.display_name or entity.display_value} (entity_type={entity.entity_type}) "
        f"is reported by {len(entity.reporting_orgs or [])} institution(s) "
        f"with risk_score={int(entity.risk_score or 0)} severity={entity.severity or 'unset'}."
    )
    return ToolResult(payload={"narrative_seed": seed})


# --- Registry --------------------------------------------------------------


TOOL_REGISTRY: dict[str, ToolFn] = {
    "resolve_entity": resolve_entity_tool,
    "neighbours": neighbours_tool,
    "recent_alerts": recent_alerts_tool,
    "recent_strs": recent_strs_tool,
    "screen_entity": screen_entity_tool,
    "build_narrative": build_narrative_tool,
}
