from datetime import UTC, datetime
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import AuthenticatedUser
from app.models.audit import AuditLog
from app.models.diagram import Diagram
from app.schemas.diagram import (
    DiagramCreate,
    DiagramDetail,
    DiagramMutationResponse,
    DiagramSummary,
    DiagramUpdate,
)


def _as_uuid(value: str | None) -> UUID | None:
    if not value:
        return None
    try:
        return UUID(value)
    except ValueError:
        return None


def _require_uuid(value: str | None, detail: str) -> UUID:
    parsed = _as_uuid(value)
    if parsed is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)
    return parsed


def _serialize_summary(record: Diagram) -> DiagramSummary:
    return DiagramSummary(
        id=str(record.id),
        org_id=str(record.org_id),
        created_by=str(record.created_by) if record.created_by else None,
        title=record.title,
        description=record.description,
        linked_case_id=str(record.linked_case_id) if record.linked_case_id else None,
        linked_str_id=str(record.linked_str_id) if record.linked_str_id else None,
        created_at=record.created_at,
        updated_at=record.updated_at,
    )


def _serialize_detail(record: Diagram) -> DiagramDetail:
    summary = _serialize_summary(record)
    return DiagramDetail(
        **summary.model_dump(),
        graph_definition=dict(record.graph_definition or {}),
    )


async def list_diagrams(
    session: AsyncSession,
    *,
    linked_case_id: str | None = None,
    linked_str_id: str | None = None,
) -> list[DiagramSummary]:
    stmt = select(Diagram).order_by(Diagram.updated_at.desc())
    case_uuid = _as_uuid(linked_case_id)
    str_uuid = _as_uuid(linked_str_id)
    if case_uuid is not None:
        stmt = stmt.where(Diagram.linked_case_id == case_uuid)
    if str_uuid is not None:
        stmt = stmt.where(Diagram.linked_str_id == str_uuid)
    result = await session.execute(stmt)
    return [_serialize_summary(row) for row in result.scalars().all()]


async def get_diagram(session: AsyncSession, diagram_id: str) -> DiagramDetail:
    record = await session.get(Diagram, UUID(diagram_id))
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Diagram not found.")
    return _serialize_detail(record)


async def create_diagram(
    session: AsyncSession,
    *,
    user: AuthenticatedUser,
    payload: DiagramCreate,
    ip: str | None,
) -> DiagramMutationResponse:
    org_uuid = _require_uuid(user.org_id, "Authenticated user is missing a valid organization id.")
    record = Diagram(
        org_id=org_uuid,
        created_by=_as_uuid(user.user_id),
        title=payload.title.strip(),
        description=payload.description,
        graph_definition=payload.graph_definition,
        linked_case_id=_as_uuid(payload.linked_case_id),
        linked_str_id=_as_uuid(payload.linked_str_id),
    )
    session.add(record)
    await session.flush()
    session.add(
        AuditLog(
            org_id=org_uuid,
            user_id=_as_uuid(user.user_id),
            action="diagram.created",
            resource_type="diagram",
            resource_id=record.id,
            details={
                "title": record.title,
                "node_count": len((payload.graph_definition or {}).get("nodes", []) or []),
            },
            ip=ip,
        )
    )
    await session.commit()
    await session.refresh(record)
    return DiagramMutationResponse(diagram=_serialize_detail(record))


async def update_diagram(
    session: AsyncSession,
    *,
    user: AuthenticatedUser,
    diagram_id: str,
    payload: DiagramUpdate,
    ip: str | None,
) -> DiagramMutationResponse:
    record = await session.get(Diagram, UUID(diagram_id))
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Diagram not found.")
    data = payload.model_dump(exclude_unset=True)
    for field in ("title", "description"):
        if field in data:
            setattr(record, field, data[field])
    if "graph_definition" in data and data["graph_definition"] is not None:
        record.graph_definition = data["graph_definition"]
    if "linked_case_id" in data:
        record.linked_case_id = _as_uuid(data["linked_case_id"])
    if "linked_str_id" in data:
        record.linked_str_id = _as_uuid(data["linked_str_id"])
    record.updated_at = datetime.now(UTC)
    session.add(
        AuditLog(
            org_id=record.org_id,
            user_id=_as_uuid(user.user_id),
            action="diagram.updated",
            resource_type="diagram",
            resource_id=record.id,
            details={"fields": list(data.keys())},
            ip=ip,
        )
    )
    await session.commit()
    await session.refresh(record)
    return DiagramMutationResponse(diagram=_serialize_detail(record))


async def delete_diagram(
    session: AsyncSession,
    *,
    user: AuthenticatedUser,
    diagram_id: str,
    ip: str | None,
) -> None:
    record = await session.get(Diagram, UUID(diagram_id))
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Diagram not found.")
    org_id = record.org_id
    record_id = record.id
    await session.delete(record)
    session.add(
        AuditLog(
            org_id=org_id,
            user_id=_as_uuid(user.user_id),
            action="diagram.deleted",
            resource_type="diagram",
            resource_id=record_id,
            details={},
            ip=ip,
        )
    )
    await session.commit()
