"""Information Exchange Request (IER) service.

IERs live in str_reports (report_type='ier') — they share the STR
lifecycle, audit trail, and entity-resolution pipeline. This service is
a thin IER-shaped facade over the STR surface so BFIU's Egmont exchange
workflow has its own verb vocabulary (open, respond, close) without
duplicating storage.
"""
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import AuthenticatedUser
from app.models.audit import AuditLog
from app.models.org import Organization
from app.models.str_report import STRReport
from app.schemas.ier import (
    IERCloseRequest,
    IERDetail,
    IERInboundCreate,
    IERListResponse,
    IERMutationResponse,
    IEROutboundCreate,
    IERRespondRequest,
    IERSummary,
)
from app.services.str_reports import create_str_report


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


def _serialize_summary(record: STRReport, org_name: str) -> IERSummary:
    return IERSummary(
        id=str(record.id),
        report_ref=record.report_ref,
        status=record.status,
        direction=record.ier_direction or "outbound",
        counterparty_fiu=record.ier_counterparty_fiu or "",
        counterparty_country=record.ier_counterparty_country,
        egmont_ref=record.ier_egmont_ref,
        deadline=record.ier_deadline,
        has_response=bool(record.ier_response_narrative),
        org_name=org_name,
        created_at=record.created_at,
        updated_at=record.updated_at,
    )


def _serialize_detail(record: STRReport, org_name: str) -> IERDetail:
    summary = _serialize_summary(record, org_name)
    return IERDetail(
        **summary.model_dump(),
        request_narrative=record.ier_request_narrative,
        response_narrative=record.ier_response_narrative,
        narrative=record.narrative,
        linked_entity_ids=[str(value) for value in (record.matched_entity_ids or [])],
        reported_at=record.reported_at,
    )


async def _fetch_with_org(session: AsyncSession, ier_id: str) -> tuple[STRReport, str]:
    stmt = (
        select(STRReport, Organization.name.label("org_name"))
        .join(Organization, Organization.id == STRReport.org_id)
        .where(STRReport.id == UUID(ier_id))
        .limit(1)
    )
    row = (await session.execute(stmt)).first()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="IER not found.")
    record, org_name = row
    if record.report_type != "ier":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Report exists but is not an IER.",
        )
    return record, str(org_name)


async def list_iers(
    session: AsyncSession,
    *,
    direction: str | None = None,
    status_filter: str | None = None,
    counterparty: str | None = None,
) -> IERListResponse:
    stmt = (
        select(STRReport, Organization.name.label("org_name"))
        .join(Organization, Organization.id == STRReport.org_id)
        .where(STRReport.report_type == "ier")
        .order_by(STRReport.reported_at.desc().nullslast(), STRReport.created_at.desc())
    )
    if direction:
        stmt = stmt.where(STRReport.ier_direction == direction)
    if status_filter:
        stmt = stmt.where(STRReport.status == status_filter)
    if counterparty:
        stmt = stmt.where(
            or_(
                STRReport.ier_counterparty_fiu.ilike(f"%{counterparty}%"),
                STRReport.ier_counterparty_country.ilike(f"%{counterparty}%"),
            )
        )
    result = await session.execute(stmt)
    iers = [_serialize_summary(record, str(org_name)) for record, org_name in result.all()]
    return IERListResponse(iers=iers)


async def get_ier(session: AsyncSession, ier_id: str) -> IERDetail:
    record, org_name = await _fetch_with_org(session, ier_id)
    return _serialize_detail(record, org_name)


async def create_outbound_ier(
    session: AsyncSession,
    *,
    user: AuthenticatedUser,
    payload: IEROutboundCreate,
    ip: str | None,
) -> IERMutationResponse:
    str_payload: dict[str, Any] = {
        "report_type": "ier",
        "subject_account": payload.counterparty_fiu,
        "subject_name": payload.counterparty_fiu,
        "total_amount": 0,
        "currency": "BDT",
        "transaction_count": 0,
        "category": "other",
        "narrative": payload.request_narrative,
        "channels": [],
        "metadata": {
            "ier_origin": "outbound",
            "linked_entity_ids": payload.linked_entity_ids,
        },
        "ier_direction": "outbound",
        "ier_counterparty_fiu": payload.counterparty_fiu,
        "ier_counterparty_country": payload.counterparty_country,
        "ier_egmont_ref": payload.egmont_ref,
        "ier_request_narrative": payload.request_narrative,
        "ier_deadline": payload.deadline,
    }
    mutation = await create_str_report(session, user=user, payload=str_payload, ip=ip)
    record, org_name = await _fetch_with_org(session, mutation.report.id)
    if payload.linked_entity_ids:
        record.matched_entity_ids = [
            _require_uuid(value, "Invalid linked_entity_id.") for value in payload.linked_entity_ids
        ]
        await session.commit()
        await session.refresh(record)
    return IERMutationResponse(ier=_serialize_detail(record, org_name))


async def create_inbound_ier(
    session: AsyncSession,
    *,
    user: AuthenticatedUser,
    payload: IERInboundCreate,
    ip: str | None,
) -> IERMutationResponse:
    str_payload: dict[str, Any] = {
        "report_type": "ier",
        "subject_account": payload.counterparty_fiu,
        "subject_name": payload.counterparty_fiu,
        "total_amount": 0,
        "currency": "BDT",
        "transaction_count": 0,
        "category": "other",
        "narrative": payload.request_narrative,
        "channels": [],
        "metadata": {
            "ier_origin": "inbound",
            "linked_entity_ids": payload.linked_entity_ids,
        },
        "ier_direction": "inbound",
        "ier_counterparty_fiu": payload.counterparty_fiu,
        "ier_counterparty_country": payload.counterparty_country,
        "ier_egmont_ref": payload.egmont_ref,
        "ier_request_narrative": payload.request_narrative,
        "ier_deadline": payload.deadline,
    }
    mutation = await create_str_report(session, user=user, payload=str_payload, ip=ip)
    record, org_name = await _fetch_with_org(session, mutation.report.id)
    if payload.linked_entity_ids:
        record.matched_entity_ids = [
            _require_uuid(value, "Invalid linked_entity_id.") for value in payload.linked_entity_ids
        ]
        await session.commit()
        await session.refresh(record)
    return IERMutationResponse(ier=_serialize_detail(record, org_name))


async def respond_to_ier(
    session: AsyncSession,
    *,
    user: AuthenticatedUser,
    ier_id: str,
    payload: IERRespondRequest,
    ip: str | None,
) -> IERMutationResponse:
    record, org_name = await _fetch_with_org(session, ier_id)
    record.ier_response_narrative = payload.response_narrative.strip()
    # Capture response moves the IER into the review state.
    if record.status in {"draft", "submitted"}:
        record.status = "under_review"
    if payload.linked_str_ids:
        existing = list(record.matched_entity_ids or [])
        # linked_str_ids refer to related STR ids; we stash them in metadata
        # rather than matched_entity_ids (those point at Entities, not STRs).
        metadata = dict(record.metadata_json or {})
        metadata["related_str_ids"] = payload.linked_str_ids
        record.metadata_json = metadata
        record.matched_entity_ids = existing
    session.add(
        AuditLog(
            org_id=record.org_id,
            user_id=_as_uuid(user.user_id),
            action="ier.responded",
            resource_type="str_report",
            resource_id=record.id,
            details={"related_str_ids": payload.linked_str_ids},
            ip=ip,
        )
    )
    record.updated_at = datetime.now(UTC)
    await session.commit()
    await session.refresh(record)
    return IERMutationResponse(ier=_serialize_detail(record, org_name))


async def close_ier(
    session: AsyncSession,
    *,
    user: AuthenticatedUser,
    ier_id: str,
    payload: IERCloseRequest,
    ip: str | None,
) -> IERMutationResponse:
    record, org_name = await _fetch_with_org(session, ier_id)
    previous = record.status
    record.status = "confirmed"
    record.reviewed_by = _as_uuid(user.user_id)
    metadata = dict(record.metadata_json or {})
    if payload.note:
        metadata["close_note"] = payload.note
    metadata["closed_at"] = datetime.now(UTC).isoformat()
    record.metadata_json = metadata
    session.add(
        AuditLog(
            org_id=record.org_id,
            user_id=_as_uuid(user.user_id),
            action="ier.closed",
            resource_type="str_report",
            resource_id=record.id,
            details={"from_status": previous, "to_status": record.status, "note": payload.note},
            ip=ip,
        )
    )
    record.updated_at = datetime.now(UTC)
    await session.commit()
    await session.refresh(record)
    return IERMutationResponse(ier=_serialize_detail(record, org_name))
