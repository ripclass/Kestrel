from datetime import UTC, datetime
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import AuthenticatedUser
from app.models.audit import AuditLog
from app.models.reference_table import ReferenceEntry
from app.schemas.reference_table import (
    ReferenceEntryCreate,
    ReferenceEntryMutationResponse,
    ReferenceEntrySummary,
    ReferenceEntryUpdate,
    ReferenceTableCount,
)


def _as_uuid(value: str | None) -> UUID | None:
    if not value:
        return None
    try:
        return UUID(value)
    except ValueError:
        return None


def _require_regulator(user: AuthenticatedUser) -> None:
    if user.org_type != "regulator":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only regulator users can modify reference tables.",
        )


def _serialize(record: ReferenceEntry) -> ReferenceEntrySummary:
    return ReferenceEntrySummary(
        id=str(record.id),
        table_name=record.table_name,
        code=record.code,
        value=record.value,
        description=record.description,
        parent_code=record.parent_code,
        metadata=dict(record.metadata_json or {}),
        is_active=record.is_active,
        created_at=record.created_at,
        updated_at=record.updated_at,
    )


async def list_entries(
    session: AsyncSession,
    *,
    table_name: str,
    include_inactive: bool = False,
) -> list[ReferenceEntrySummary]:
    stmt = select(ReferenceEntry).where(ReferenceEntry.table_name == table_name)
    if not include_inactive:
        stmt = stmt.where(ReferenceEntry.is_active.is_(True))
    stmt = stmt.order_by(ReferenceEntry.code.asc())
    result = await session.execute(stmt)
    return [_serialize(row) for row in result.scalars().all()]


async def table_counts(session: AsyncSession) -> list[ReferenceTableCount]:
    active_expr = case((ReferenceEntry.is_active.is_(True), 1), else_=0)
    stmt = (
        select(
            ReferenceEntry.table_name.label("table_name"),
            func.count().label("total_count"),
            func.sum(active_expr).label("active_count"),
        )
        .group_by(ReferenceEntry.table_name)
        .order_by(ReferenceEntry.table_name.asc())
    )
    result = await session.execute(stmt)
    return [
        ReferenceTableCount(
            table_name=row.table_name,
            active_count=int(row.active_count or 0),
            total_count=int(row.total_count or 0),
        )
        for row in result.all()
    ]


async def _fetch_entry_or_404(session: AsyncSession, entry_id: str) -> ReferenceEntry:
    record = await session.get(ReferenceEntry, UUID(entry_id))
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reference entry not found.")
    return record


async def create_entry(
    session: AsyncSession,
    *,
    user: AuthenticatedUser,
    payload: ReferenceEntryCreate,
    ip: str | None,
) -> ReferenceEntryMutationResponse:
    _require_regulator(user)
    record = ReferenceEntry(
        table_name=payload.table_name,
        code=payload.code.strip(),
        value=payload.value.strip(),
        description=payload.description,
        parent_code=payload.parent_code,
        metadata_json=payload.metadata,
        is_active=payload.is_active,
    )
    session.add(record)
    await session.flush()
    session.add(
        AuditLog(
            org_id=_as_uuid(user.org_id),
            user_id=_as_uuid(user.user_id),
            action="reference_table.entry.created",
            resource_type="reference_entry",
            resource_id=record.id,
            details={"table_name": record.table_name, "code": record.code},
            ip=ip,
        )
    )
    await session.commit()
    await session.refresh(record)
    return ReferenceEntryMutationResponse(entry=_serialize(record))


async def update_entry(
    session: AsyncSession,
    *,
    user: AuthenticatedUser,
    entry_id: str,
    payload: ReferenceEntryUpdate,
    ip: str | None,
) -> ReferenceEntryMutationResponse:
    _require_regulator(user)
    record = await _fetch_entry_or_404(session, entry_id)
    data = payload.model_dump(exclude_unset=True)
    for field in ("value", "description", "parent_code", "is_active"):
        if field in data:
            setattr(record, field, data[field])
    if "metadata" in data and data["metadata"] is not None:
        record.metadata_json = data["metadata"]
    record.updated_at = datetime.now(UTC)
    session.add(
        AuditLog(
            org_id=_as_uuid(user.org_id),
            user_id=_as_uuid(user.user_id),
            action="reference_table.entry.updated",
            resource_type="reference_entry",
            resource_id=record.id,
            details={"fields": list(data.keys())},
            ip=ip,
        )
    )
    await session.commit()
    await session.refresh(record)
    return ReferenceEntryMutationResponse(entry=_serialize(record))


async def delete_entry(
    session: AsyncSession,
    *,
    user: AuthenticatedUser,
    entry_id: str,
    ip: str | None,
) -> None:
    _require_regulator(user)
    record = await _fetch_entry_or_404(session, entry_id)
    record_id = record.id
    table_name = record.table_name
    code = record.code
    await session.delete(record)
    session.add(
        AuditLog(
            org_id=_as_uuid(user.org_id),
            user_id=_as_uuid(user.user_id),
            action="reference_table.entry.deleted",
            resource_type="reference_entry",
            resource_id=record_id,
            details={"table_name": table_name, "code": code},
            ip=ip,
        )
    )
    await session.commit()
