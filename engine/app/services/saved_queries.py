from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import AuthenticatedUser
from app.models.audit import AuditLog
from app.models.saved_query import SavedQuery
from app.schemas.saved_query import (
    SavedQueryCreate,
    SavedQueryDetail,
    SavedQueryMutationResponse,
    SavedQuerySummary,
    SavedQueryUpdate,
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


def _serialize_summary(record: SavedQuery) -> SavedQuerySummary:
    return SavedQuerySummary(
        id=str(record.id),
        org_id=str(record.org_id),
        user_id=str(record.user_id),
        name=record.name,
        description=record.description,
        query_type=record.query_type,
        is_shared=record.is_shared,
        last_run_at=record.last_run_at,
        run_count=record.run_count,
        created_at=record.created_at,
        updated_at=record.updated_at,
    )


def _serialize_detail(record: SavedQuery) -> SavedQueryDetail:
    summary = _serialize_summary(record)
    return SavedQueryDetail(
        **summary.model_dump(),
        query_definition=dict(record.query_definition or {}),
    )


async def list_saved_queries(
    session: AsyncSession,
    *,
    user: AuthenticatedUser,
    query_type: str | None = None,
) -> list[SavedQuerySummary]:
    user_uuid = _require_uuid(user.user_id, "Authenticated user is missing a valid user id.")
    org_uuid = _require_uuid(user.org_id, "Authenticated user is missing a valid organization id.")
    stmt = select(SavedQuery).where(
        or_(
            SavedQuery.user_id == user_uuid,
            (SavedQuery.is_shared.is_(True)) & (SavedQuery.org_id == org_uuid),
        )
    ).order_by(SavedQuery.updated_at.desc())
    if query_type:
        stmt = stmt.where(SavedQuery.query_type == query_type)
    result = await session.execute(stmt)
    return [_serialize_summary(row) for row in result.scalars().all()]


async def _fetch_owned_query(
    session: AsyncSession, *, user: AuthenticatedUser, query_id: str
) -> SavedQuery:
    record = await session.get(SavedQuery, UUID(query_id))
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Saved query not found.")
    # Owner-only for writes; read is broader but this helper guards writes.
    if str(record.user_id) != user.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the owner can modify this saved query.",
        )
    return record


async def get_saved_query(
    session: AsyncSession, *, user: AuthenticatedUser, query_id: str
) -> SavedQueryDetail:
    record = await session.get(SavedQuery, UUID(query_id))
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Saved query not found.")
    if str(record.user_id) != user.user_id and not (
        record.is_shared and str(record.org_id) == user.org_id
    ) and user.org_type != "regulator":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This saved query is not visible to you.",
        )
    return _serialize_detail(record)


async def create_saved_query(
    session: AsyncSession,
    *,
    user: AuthenticatedUser,
    payload: SavedQueryCreate,
    ip: str | None,
) -> SavedQueryMutationResponse:
    org_uuid = _require_uuid(user.org_id, "Authenticated user is missing a valid organization id.")
    user_uuid = _require_uuid(user.user_id, "Authenticated user is missing a valid user id.")
    record = SavedQuery(
        org_id=org_uuid,
        user_id=user_uuid,
        name=payload.name.strip(),
        description=payload.description,
        query_type=payload.query_type,
        query_definition=payload.query_definition,
        is_shared=payload.is_shared,
    )
    session.add(record)
    await session.flush()
    session.add(
        AuditLog(
            org_id=org_uuid,
            user_id=user_uuid,
            action="saved_query.created",
            resource_type="saved_query",
            resource_id=record.id,
            details={"name": record.name, "query_type": record.query_type, "is_shared": record.is_shared},
            ip=ip,
        )
    )
    await session.commit()
    await session.refresh(record)
    return SavedQueryMutationResponse(saved_query=_serialize_detail(record))


async def update_saved_query(
    session: AsyncSession,
    *,
    user: AuthenticatedUser,
    query_id: str,
    payload: SavedQueryUpdate,
    ip: str | None,
) -> SavedQueryMutationResponse:
    record = await _fetch_owned_query(session, user=user, query_id=query_id)
    data = payload.model_dump(exclude_unset=True)
    for field in ("name", "description", "is_shared"):
        if field in data:
            setattr(record, field, data[field])
    if "query_definition" in data and data["query_definition"] is not None:
        record.query_definition = data["query_definition"]
    record.updated_at = datetime.now(UTC)
    session.add(
        AuditLog(
            org_id=record.org_id,
            user_id=_as_uuid(user.user_id),
            action="saved_query.updated",
            resource_type="saved_query",
            resource_id=record.id,
            details={"fields": list(data.keys())},
            ip=ip,
        )
    )
    await session.commit()
    await session.refresh(record)
    return SavedQueryMutationResponse(saved_query=_serialize_detail(record))


async def delete_saved_query(
    session: AsyncSession,
    *,
    user: AuthenticatedUser,
    query_id: str,
    ip: str | None,
) -> None:
    record = await _fetch_owned_query(session, user=user, query_id=query_id)
    org_id = record.org_id
    record_id = record.id
    await session.delete(record)
    session.add(
        AuditLog(
            org_id=org_id,
            user_id=_as_uuid(user.user_id),
            action="saved_query.deleted",
            resource_type="saved_query",
            resource_id=record_id,
            details={},
            ip=ip,
        )
    )
    await session.commit()


async def record_run(
    session: AsyncSession,
    *,
    user: AuthenticatedUser,
    query_id: str,
) -> SavedQueryMutationResponse:
    record = await session.get(SavedQuery, UUID(query_id))
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Saved query not found.")
    record.run_count = (record.run_count or 0) + 1
    record.last_run_at = datetime.now(UTC)
    await session.commit()
    await session.refresh(record)
    return SavedQueryMutationResponse(saved_query=_serialize_detail(record))


async def ping_user(_: AuthenticatedUser) -> dict[str, Any]:
    return {"ok": True}
