from datetime import UTC, datetime
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import AuthenticatedUser
from app.models.audit import AuditLog
from app.models.match_definition import MatchDefinition, MatchExecution
from app.schemas.match_definition import (
    MatchDefinitionCreate,
    MatchDefinitionDetail,
    MatchDefinitionMutationResponse,
    MatchDefinitionSummary,
    MatchDefinitionUpdate,
    MatchExecutionResponse,
    MatchExecutionSummary,
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


def _serialize_summary(record: MatchDefinition) -> MatchDefinitionSummary:
    return MatchDefinitionSummary(
        id=str(record.id),
        org_id=str(record.org_id),
        name=record.name,
        description=record.description,
        is_active=record.is_active,
        created_by=str(record.created_by) if record.created_by else None,
        created_at=record.created_at,
        updated_at=record.updated_at,
        last_execution_at=record.last_execution_at,
        total_hits=record.total_hits,
    )


def _serialize_execution(record: MatchExecution) -> MatchExecutionSummary:
    return MatchExecutionSummary(
        id=str(record.id),
        definition_id=str(record.definition_id),
        executed_at=record.executed_at,
        executed_by=str(record.executed_by) if record.executed_by else None,
        hit_count=record.hit_count,
        execution_status=record.execution_status,
        results_summary=dict(record.results_summary or {}),
    )


async def _recent_executions(
    session: AsyncSession, definition_id: UUID, limit: int = 10
) -> list[MatchExecutionSummary]:
    result = await session.execute(
        select(MatchExecution)
        .where(MatchExecution.definition_id == definition_id)
        .order_by(MatchExecution.executed_at.desc())
        .limit(limit)
    )
    return [_serialize_execution(row) for row in result.scalars().all()]


async def _serialize_detail(
    session: AsyncSession, record: MatchDefinition
) -> MatchDefinitionDetail:
    summary = _serialize_summary(record)
    executions = await _recent_executions(session, record.id)
    return MatchDefinitionDetail(
        **summary.model_dump(),
        definition=dict(record.definition or {}),
        recent_executions=executions,
    )


async def list_match_definitions(
    session: AsyncSession,
    *,
    is_active: bool | None = None,
) -> list[MatchDefinitionSummary]:
    stmt = select(MatchDefinition).order_by(MatchDefinition.updated_at.desc())
    if is_active is not None:
        stmt = stmt.where(MatchDefinition.is_active.is_(is_active))
    result = await session.execute(stmt)
    return [_serialize_summary(row) for row in result.scalars().all()]


async def get_match_definition(
    session: AsyncSession, definition_id: str
) -> MatchDefinitionDetail:
    record = await session.get(MatchDefinition, UUID(definition_id))
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Match definition not found.")
    return await _serialize_detail(session, record)


async def create_match_definition(
    session: AsyncSession,
    *,
    user: AuthenticatedUser,
    payload: MatchDefinitionCreate,
    ip: str | None,
) -> MatchDefinitionMutationResponse:
    org_uuid = _require_uuid(user.org_id, "Authenticated user is missing a valid organization id.")
    record = MatchDefinition(
        org_id=org_uuid,
        name=payload.name.strip(),
        description=payload.description,
        definition=payload.definition,
        is_active=payload.is_active,
        created_by=_as_uuid(user.user_id),
    )
    session.add(record)
    await session.flush()
    session.add(
        AuditLog(
            org_id=org_uuid,
            user_id=_as_uuid(user.user_id),
            action="match_definition.created",
            resource_type="match_definition",
            resource_id=record.id,
            details={"name": record.name, "is_active": record.is_active},
            ip=ip,
        )
    )
    await session.commit()
    await session.refresh(record)
    detail = await _serialize_detail(session, record)
    return MatchDefinitionMutationResponse(match_definition=detail)


async def update_match_definition(
    session: AsyncSession,
    *,
    user: AuthenticatedUser,
    definition_id: str,
    payload: MatchDefinitionUpdate,
    ip: str | None,
) -> MatchDefinitionMutationResponse:
    record = await session.get(MatchDefinition, UUID(definition_id))
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Match definition not found.")
    data = payload.model_dump(exclude_unset=True)
    for field in ("name", "description", "is_active"):
        if field in data:
            setattr(record, field, data[field])
    if "definition" in data and data["definition"] is not None:
        record.definition = data["definition"]
    record.updated_at = datetime.now(UTC)
    session.add(
        AuditLog(
            org_id=record.org_id,
            user_id=_as_uuid(user.user_id),
            action="match_definition.updated",
            resource_type="match_definition",
            resource_id=record.id,
            details={"fields": list(data.keys())},
            ip=ip,
        )
    )
    await session.commit()
    await session.refresh(record)
    detail = await _serialize_detail(session, record)
    return MatchDefinitionMutationResponse(match_definition=detail)


async def delete_match_definition(
    session: AsyncSession,
    *,
    user: AuthenticatedUser,
    definition_id: str,
    ip: str | None,
) -> None:
    record = await session.get(MatchDefinition, UUID(definition_id))
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Match definition not found.")
    org_id = record.org_id
    record_id = record.id
    await session.delete(record)
    session.add(
        AuditLog(
            org_id=org_id,
            user_id=_as_uuid(user.user_id),
            action="match_definition.deleted",
            resource_type="match_definition",
            resource_id=record_id,
            details={},
            ip=ip,
        )
    )
    await session.commit()


async def execute_match_definition(
    session: AsyncSession,
    *,
    user: AuthenticatedUser,
    definition_id: str,
    ip: str | None,
) -> MatchExecutionResponse:
    record = await session.get(MatchDefinition, UUID(definition_id))
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Match definition not found.")
    if not record.is_active:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Inactive match definitions cannot be executed.",
        )

    # v1 execution: the definition DSL is a JSON blob with no evaluator
    # yet. We record the execution attempt and stamp the definition so
    # downstream dashboards see activity, and leave real scoring for a
    # follow-up that wires the JSON into the existing rule evaluator.
    execution = MatchExecution(
        definition_id=record.id,
        executed_by=_as_uuid(user.user_id),
        hit_count=0,
        execution_status="completed",
        results_summary={
            "message": "Definition recorded; evaluator wiring pending.",
        },
    )
    session.add(execution)
    await session.flush()

    record.last_execution_at = execution.executed_at
    session.add(
        AuditLog(
            org_id=record.org_id,
            user_id=_as_uuid(user.user_id),
            action="match_definition.executed",
            resource_type="match_definition",
            resource_id=record.id,
            details={
                "execution_id": str(execution.id),
                "hit_count": execution.hit_count,
                "status": execution.execution_status,
            },
            ip=ip,
        )
    )
    await session.commit()
    await session.refresh(record)
    await session.refresh(execution)

    detail = await _serialize_detail(session, record)
    return MatchExecutionResponse(
        execution=_serialize_execution(execution),
        match_definition=detail,
    )
