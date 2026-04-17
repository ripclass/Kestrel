from copy import deepcopy
from typing import Any
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import AuthenticatedUser
from app.models.audit import AuditLog
from app.models.dissemination import Dissemination
from app.models.org import Organization
from app.schemas.dissemination import (
    DisseminationCreate,
    DisseminationDetail,
    DisseminationMutationResponse,
    DisseminationSummary,
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


def _parse_uuid_list(values: list[str] | None, field: str) -> list[UUID]:
    if not values:
        return []
    parsed: list[UUID] = []
    for raw in values:
        parsed.append(_require_uuid(raw, f"Invalid UUID in {field}."))
    return parsed


def _uuid_list_as_str(values: list[UUID] | None) -> list[str]:
    if not values:
        return []
    return [str(value) for value in values]


def _serialize_summary(record: Dissemination, org_name: str) -> DisseminationSummary:
    return DisseminationSummary(
        id=str(record.id),
        org_id=str(record.org_id),
        org_name=org_name,
        dissemination_ref=record.dissemination_ref,
        recipient_agency=record.recipient_agency,
        recipient_type=record.recipient_type,
        subject_summary=record.subject_summary,
        classification=record.classification,
        disseminated_by=str(record.disseminated_by) if record.disseminated_by else None,
        disseminated_at=record.disseminated_at,
        linked_report_count=len(record.linked_report_ids or []),
        linked_entity_count=len(record.linked_entity_ids or []),
        linked_case_count=len(record.linked_case_ids or []),
        created_at=record.created_at,
    )


def _serialize_detail(record: Dissemination, org_name: str) -> DisseminationDetail:
    summary = _serialize_summary(record, org_name)
    return DisseminationDetail(
        **summary.model_dump(),
        linked_report_ids=_uuid_list_as_str(record.linked_report_ids),
        linked_entity_ids=_uuid_list_as_str(record.linked_entity_ids),
        linked_case_ids=_uuid_list_as_str(record.linked_case_ids),
        metadata=deepcopy(record.metadata_json or {}),
    )


async def _fetch_with_org(session: AsyncSession, dissem_id: str) -> tuple[Dissemination, str]:
    stmt = (
        select(Dissemination, Organization.name.label("org_name"))
        .join(Organization, Organization.id == Dissemination.org_id)
        .where(Dissemination.id == UUID(dissem_id))
        .limit(1)
    )
    row = (await session.execute(stmt)).first()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dissemination not found.")
    record, org_name = row
    return record, str(org_name)


async def list_disseminations(
    session: AsyncSession,
    *,
    recipient_agency: str | None = None,
    recipient_type: str | None = None,
) -> list[DisseminationSummary]:
    stmt = (
        select(Dissemination, Organization.name.label("org_name"))
        .join(Organization, Organization.id == Dissemination.org_id)
        .order_by(Dissemination.disseminated_at.desc())
    )
    if recipient_agency:
        stmt = stmt.where(Dissemination.recipient_agency == recipient_agency)
    if recipient_type:
        stmt = stmt.where(Dissemination.recipient_type == recipient_type)
    result = await session.execute(stmt)
    return [_serialize_summary(record, str(org_name)) for record, org_name in result.all()]


async def get_dissemination(session: AsyncSession, dissem_id: str) -> DisseminationDetail:
    record, org_name = await _fetch_with_org(session, dissem_id)
    return _serialize_detail(record, org_name)


async def create_dissemination(
    session: AsyncSession,
    *,
    user: AuthenticatedUser,
    payload: DisseminationCreate,
    ip: str | None,
) -> DisseminationMutationResponse:
    org_id = _require_uuid(user.org_id, "Authenticated user is missing a valid organization id.")

    record = Dissemination(
        org_id=org_id,
        dissemination_ref="",
        recipient_agency=payload.recipient_agency.strip(),
        recipient_type=payload.recipient_type,
        subject_summary=payload.subject_summary.strip(),
        linked_report_ids=_parse_uuid_list(payload.linked_report_ids, "linked_report_ids"),
        linked_entity_ids=_parse_uuid_list(payload.linked_entity_ids, "linked_entity_ids"),
        linked_case_ids=_parse_uuid_list(payload.linked_case_ids, "linked_case_ids"),
        disseminated_by=_as_uuid(user.user_id),
        classification=payload.classification,
        metadata_json=payload.metadata,
    )
    session.add(record)
    await session.flush()

    audit_details: dict[str, Any] = {
        "dissemination_ref": record.dissemination_ref,
        "recipient_agency": record.recipient_agency,
        "recipient_type": record.recipient_type,
        "classification": record.classification,
        "linked_report_count": len(record.linked_report_ids or []),
        "linked_entity_count": len(record.linked_entity_ids or []),
        "linked_case_count": len(record.linked_case_ids or []),
    }
    session.add(
        AuditLog(
            org_id=org_id,
            user_id=_as_uuid(user.user_id),
            action="dissemination.created",
            resource_type="dissemination",
            resource_id=record.id,
            details=audit_details,
            ip=ip,
        )
    )
    await session.commit()
    await session.refresh(record)
    detail = await get_dissemination(session, str(record.id))
    return DisseminationMutationResponse(dissemination=detail)
