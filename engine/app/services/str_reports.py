from copy import deepcopy
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.service import AIInvocationResult, AIOrchestrator
from app.ai.types import AITaskName
from app.auth import AuthenticatedUser
from app.core.pipeline import run_str_pipeline
from app.models.audit import AuditLog
from app.models.org import Organization
from app.models.str_report import STRReport
from app.schemas.ai import AIInvocationMeta, EntityExtractionResult, STRNarrativeResult
from app.schemas.str_report import (
    STREnrichmentSnapshot,
    STRLifecycleEvent,
    STRMutationResponse,
    STRReportDetail,
    STRReportSummary,
    STRReviewRequest,
    STRReviewState,
)

_EDITABLE_STATUSES = {"draft"}
_REVIEW_OUTCOMES = {
    "start_review": "under_review",
    "flag": "flagged",
    "confirm": "confirmed",
    "dismiss": "dismissed",
}


def _as_float(value: Decimal | float | int | None) -> float:
    if value is None:
        return 0.0
    return float(value)


def _as_str_list(values: list[Any] | None) -> list[str]:
    if not values:
        return []
    return [str(value) for value in values]


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


def _normalize_review(metadata: dict[str, Any]) -> STRReviewState:
    review = metadata.get("review")
    if not isinstance(review, dict):
        return STRReviewState()
    return STRReviewState.model_validate(review)


def _normalize_enrichment(metadata: dict[str, Any]) -> STREnrichmentSnapshot | None:
    enrichment = metadata.get("enrichment")
    if not isinstance(enrichment, dict):
        return None
    return STREnrichmentSnapshot.model_validate(enrichment)


def _serialize_report(report: STRReport, org_name: str) -> STRReportSummary:
    return STRReportSummary(
        id=str(report.id),
        org_id=str(report.org_id),
        org_name=org_name,
        report_ref=report.report_ref,
        report_type=report.report_type or "str",
        status=report.status,
        subject_name=report.subject_name,
        subject_account=report.subject_account,
        subject_bank=report.subject_bank,
        total_amount=_as_float(report.total_amount),
        currency=report.currency,
        transaction_count=report.transaction_count,
        primary_channel=report.primary_channel,
        category=report.category,
        auto_risk_score=report.auto_risk_score,
        cross_bank_hit=report.cross_bank_hit,
        reported_at=report.reported_at,
        created_at=report.created_at,
        updated_at=report.updated_at,
        supplements_report_id=str(report.supplements_report_id) if report.supplements_report_id else None,
        ier_direction=report.ier_direction,
        ier_counterparty_fiu=report.ier_counterparty_fiu,
        media_source=report.media_source,
    )


def serialize_report_detail(report: STRReport, org_name: str) -> STRReportDetail:
    metadata = deepcopy(report.metadata_json or {})
    summary = _serialize_report(report, org_name)
    return STRReportDetail(
        **summary.model_dump(),
        subject_phone=report.subject_phone,
        subject_wallet=report.subject_wallet,
        subject_nid=report.subject_nid,
        channels=list(report.channels or []),
        date_range_start=report.date_range_start,
        date_range_end=report.date_range_end,
        narrative=report.narrative,
        matched_entity_ids=_as_str_list(report.matched_entity_ids),
        submitted_by=str(report.submitted_by) if report.submitted_by else None,
        reviewed_by=str(report.reviewed_by) if report.reviewed_by else None,
        metadata=metadata,
        enrichment=_normalize_enrichment(metadata),
        review=_normalize_review(metadata),
        media_url=report.media_url,
        media_published_at=report.media_published_at,
        ier_counterparty_country=report.ier_counterparty_country,
        ier_egmont_ref=report.ier_egmont_ref,
        ier_request_narrative=report.ier_request_narrative,
        ier_response_narrative=report.ier_response_narrative,
        ier_deadline=report.ier_deadline,
        tbml_invoice_value=_as_float(report.tbml_invoice_value) if report.tbml_invoice_value is not None else None,
        tbml_declared_value=_as_float(report.tbml_declared_value) if report.tbml_declared_value is not None else None,
        tbml_lc_reference=report.tbml_lc_reference,
        tbml_hs_code=report.tbml_hs_code,
        tbml_commodity=report.tbml_commodity,
        tbml_counterparty_country=report.tbml_counterparty_country,
    )


def _append_lifecycle_event(
    metadata: dict[str, Any],
    *,
    action: str,
    user: AuthenticatedUser,
    from_status: str | None,
    to_status: str | None,
    note: str | None = None,
    assigned_to: str | None = None,
) -> dict[str, Any]:
    next_metadata = deepcopy(metadata or {})
    review = deepcopy(next_metadata.get("review") or {})
    history = list(review.get("status_history") or [])
    history.append(
        STRLifecycleEvent(
            action=action,
            actor_user_id=user.user_id,
            actor_role=user.role,
            actor_org_type=user.org_type,
            from_status=from_status,
            to_status=to_status,
            note=note,
            occurred_at=datetime.now(UTC),
        ).model_dump(mode="json")
    )
    review["status_history"] = history
    if assigned_to is not None:
        review["assigned_to"] = assigned_to
    if note:
        notes = list(review.get("notes") or [])
        notes.append(
            {
                "actor_user_id": user.user_id,
                "actor_role": user.role,
                "note": note,
                "occurred_at": datetime.now(UTC).isoformat(),
            }
        )
        review["notes"] = notes
    next_metadata["review"] = review
    return next_metadata


def build_str_enrichment_payload(report: STRReport) -> dict[str, Any]:
    trigger_facts: list[str] = []
    if report.total_amount:
        trigger_facts.append(f"Approximate exposure of BDT {_as_float(report.total_amount):,.2f} was reported.")
    if report.transaction_count:
        trigger_facts.append(f"{report.transaction_count} transactions were cited in the draft.")
    if report.primary_channel:
        trigger_facts.append(f"Primary channel observed: {report.primary_channel}.")
    if report.channels:
        trigger_facts.append(f"Channels involved: {', '.join(report.channels)}.")
    if report.cross_bank_hit:
        trigger_facts.append("Cross-bank matches were already associated with this subject.")
    if report.metadata_json.get("review", {}).get("notes"):
        trigger_facts.append("Existing review notes are available and should be reflected in the narrative.")

    return {
        "subject_name": report.subject_name,
        "subject_account": report.subject_account,
        "subject_phone": report.subject_phone,
        "subject_wallet": report.subject_wallet,
        "subject_nid": report.subject_nid,
        "total_amount": _as_float(report.total_amount),
        "category": report.category,
        "trigger_facts": trigger_facts,
    }


async def _record_audit(
    session: AsyncSession,
    *,
    report: STRReport,
    user: AuthenticatedUser,
    action: str,
    details: dict[str, Any],
    ip: str | None,
) -> None:
    session.add(
        AuditLog(
            org_id=report.org_id,
            user_id=_as_uuid(user.user_id),
            action=action,
            resource_type="str_report",
            resource_id=report.id,
            details=details,
            ip=ip,
        )
    )


async def _fetch_report_with_org(session: AsyncSession, report_id: str) -> tuple[STRReport, str]:
    stmt = (
        select(STRReport, Organization.name.label("org_name"))
        .join(Organization, Organization.id == STRReport.org_id)
        .where(STRReport.id == UUID(report_id))
        .execution_options(populate_existing=True)
        .limit(1)
    )
    result = await session.execute(stmt)
    row = result.first()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="STR report not found.")
    report, org_name = row
    return report, str(org_name)


def _ensure_editable(report: STRReport, user: AuthenticatedUser) -> None:
    if str(report.org_id) != user.org_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only the owning organization can edit this STR.")
    if report.status not in _EDITABLE_STATUSES:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Only draft STRs can be edited.")


def _ensure_review_access(user: AuthenticatedUser) -> None:
    if user.org_type != "regulator":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only regulator users can review STRs.")


_NEW_REPORT_FIELDS: tuple[str, ...] = (
    "supplements_report_id",
    "media_source",
    "media_url",
    "media_published_at",
    "ier_direction",
    "ier_counterparty_fiu",
    "ier_counterparty_country",
    "ier_egmont_ref",
    "ier_request_narrative",
    "ier_response_narrative",
    "ier_deadline",
    "tbml_invoice_value",
    "tbml_declared_value",
    "tbml_lc_reference",
    "tbml_hs_code",
    "tbml_commodity",
    "tbml_counterparty_country",
)


def _ensure_submission_ready(report: STRReport) -> None:
    missing: list[str] = []
    if not report.category:
        missing.append("category")

    rt = report.report_type or "str"
    if rt == "ier":
        if not report.ier_direction:
            missing.append("ier_direction")
        if not report.ier_counterparty_fiu:
            missing.append("ier_counterparty_fiu")
        if not (
            report.narrative
            or report.ier_request_narrative
            or report.ier_response_narrative
        ):
            missing.append("narrative")
    elif rt == "additional_info":
        if not report.supplements_report_id:
            missing.append("supplements_report_id")
        if not report.narrative:
            missing.append("narrative")
    else:
        if not report.subject_account:
            missing.append("subject_account")
        if not report.narrative:
            missing.append("narrative")

    if missing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Draft is incomplete. Missing required submission fields: {', '.join(missing)}.",
        )


async def _fetch_parent_for_supplement(
    session: AsyncSession, parent_id: UUID
) -> STRReport | None:
    result = await session.execute(
        select(STRReport).where(STRReport.id == parent_id).limit(1)
    )
    return result.scalar_one_or_none()


async def list_supplements_of(
    session: AsyncSession,
    *,
    parent_id: str,
) -> list[STRReportSummary]:
    """Return every additional_info STR that supplements ``parent_id``."""
    parent_uuid = _as_uuid(parent_id)
    if parent_uuid is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid parent report id.")
    stmt = (
        select(STRReport, Organization.name.label("org_name"))
        .join(Organization, Organization.id == STRReport.org_id)
        .where(STRReport.supplements_report_id == parent_uuid)
        .order_by(STRReport.reported_at.desc().nullslast(), STRReport.created_at.desc())
    )
    result = await session.execute(stmt)
    return [_serialize_report(report, str(org_name)) for report, org_name in result.all()]


async def list_str_reports(
    session: AsyncSession,
    *,
    status_filter: str | None = None,
    report_type: str | None = None,
) -> list[STRReportSummary]:
    stmt = (
        select(STRReport, Organization.name.label("org_name"))
        .join(Organization, Organization.id == STRReport.org_id)
        .order_by(STRReport.reported_at.desc().nullslast(), STRReport.created_at.desc())
    )
    if status_filter:
        stmt = stmt.where(STRReport.status == status_filter)
    if report_type:
        stmt = stmt.where(STRReport.report_type == report_type)
    result = await session.execute(stmt)
    return [_serialize_report(report, str(org_name)) for report, org_name in result.all()]


async def get_str_report(session: AsyncSession, report_id: str) -> STRReportDetail:
    report, org_name = await _fetch_report_with_org(session, report_id)
    return serialize_report_detail(report, org_name)


async def create_str_report(
    session: AsyncSession,
    *,
    user: AuthenticatedUser,
    payload: dict[str, Any],
    ip: str | None,
) -> STRMutationResponse:
    report_type = payload.get("report_type", "str")

    subject_fields: dict[str, Any] = {
        "subject_name": payload.get("subject_name"),
        "subject_account": payload.get("subject_account"),
        "subject_bank": payload.get("subject_bank"),
        "subject_phone": payload.get("subject_phone"),
        "subject_wallet": payload.get("subject_wallet"),
        "subject_nid": payload.get("subject_nid"),
    }
    matched_entity_ids: list[UUID] = []

    # Additional Information Files inherit subject identity + matched entities
    # from the parent report when the caller hasn't overridden them.
    supplements_raw = payload.get("supplements_report_id")
    supplements_uuid: UUID | None = None
    if report_type == "additional_info" and supplements_raw:
        supplements_uuid = _require_uuid(
            supplements_raw, "Invalid supplements_report_id."
        )
        parent = await _fetch_parent_for_supplement(session, supplements_uuid)
        if parent is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Parent report for supplement not found.",
            )
        if str(parent.org_id) != user.org_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot supplement a report owned by another organization.",
            )
        for key in subject_fields:
            if subject_fields[key] is None:
                subject_fields[key] = getattr(parent, key)
        matched_entity_ids = list(parent.matched_entity_ids or [])

    # IER doesn't require a subject_account — the "subject" is the
    # counterparty FIU exchange, not an account number.
    if report_type == "ier" and not subject_fields["subject_account"]:
        subject_fields["subject_account"] = payload.get(
            "ier_counterparty_fiu"
        ) or "(IER)"

    type_specific_fields: dict[str, Any] = {
        field: payload.get(field) for field in _NEW_REPORT_FIELDS
    }
    type_specific_fields["supplements_report_id"] = supplements_uuid

    report = STRReport(
        org_id=_require_uuid(user.org_id, "Authenticated user is missing a valid organization id."),
        report_ref="",
        report_type=report_type,
        status="draft",
        **subject_fields,
        total_amount=payload.get("total_amount", 0),
        currency=payload.get("currency", "BDT"),
        transaction_count=payload.get("transaction_count", 0),
        primary_channel=payload.get("primary_channel"),
        category=payload.get("category", "fraud"),
        narrative=payload.get("narrative"),
        channels=payload.get("channels", []),
        date_range_start=payload.get("date_range_start"),
        date_range_end=payload.get("date_range_end"),
        matched_entity_ids=matched_entity_ids,
        metadata_json=_append_lifecycle_event(
            payload.get("metadata", {}),
            action="created",
            user=user,
            from_status=None,
            to_status="draft",
        ),
        **type_specific_fields,
    )
    session.add(report)
    await session.flush()
    await _record_audit(
        session,
        report=report,
        user=user,
        action="str_report.created",
        details={"status": report.status, "report_ref": report.report_ref},
        ip=ip,
    )
    await session.commit()
    await session.refresh(report)
    refreshed, org_name = await _fetch_report_with_org(session, str(report.id))
    return STRMutationResponse(report=serialize_report_detail(refreshed, org_name))


async def update_str_report(
    session: AsyncSession,
    *,
    report_id: str,
    user: AuthenticatedUser,
    payload: dict[str, Any],
    ip: str | None,
) -> STRMutationResponse:
    report, org_name = await _fetch_report_with_org(session, report_id)
    _ensure_editable(report, user)
    for field in [
        "subject_name",
        "subject_account",
        "subject_bank",
        "subject_phone",
        "subject_wallet",
        "subject_nid",
        "total_amount",
        "currency",
        "transaction_count",
        "primary_channel",
        "category",
        "narrative",
        "channels",
        "date_range_start",
        "date_range_end",
    ]:
        setattr(report, field, payload.get(field))
    for field in _NEW_REPORT_FIELDS:
        if field == "supplements_report_id":
            raw = payload.get(field)
            setattr(
                report,
                field,
                _require_uuid(raw, f"Invalid {field}.") if raw else None,
            )
        else:
            setattr(report, field, payload.get(field))
    report.metadata_json = _append_lifecycle_event(
        {**(report.metadata_json or {}), **payload.get("metadata", {})},
        action="updated",
        user=user,
        from_status=report.status,
        to_status=report.status,
    )
    await _record_audit(
        session,
        report=report,
        user=user,
        action="str_report.updated",
        details={"status": report.status},
        ip=ip,
    )
    await session.commit()
    await session.refresh(report)
    return STRMutationResponse(report=serialize_report_detail(report, org_name))


async def submit_str_report(
    session: AsyncSession,
    *,
    report_id: str,
    user: AuthenticatedUser,
    ip: str | None,
) -> STRMutationResponse:
    report, org_name = await _fetch_report_with_org(session, report_id)
    _ensure_editable(report, user)
    _ensure_submission_ready(report)
    previous_status = report.status
    report.status = "submitted"
    report.submitted_by = _as_uuid(user.user_id)
    report.reported_at = report.reported_at or datetime.now(UTC)
    report.metadata_json = _append_lifecycle_event(
        report.metadata_json or {},
        action="submitted",
        user=user,
        from_status=previous_status,
        to_status=report.status,
    )

    org_uuid = _require_uuid(user.org_id, "Authenticated user is missing a valid organization id.")
    try:
        pipeline_result = await run_str_pipeline(
            session, str_report=report, org_id=org_uuid
        )
    except Exception as exc:
        pipeline_result = {"entities": [], "matches": [], "alerts": [], "error": str(exc)}

    await _record_audit(
        session,
        report=report,
        user=user,
        action="str_report.submitted",
        details={
            "from_status": previous_status,
            "to_status": report.status,
            "entities_resolved": len(pipeline_result.get("entities", [])),
            "cross_bank_matches": len(pipeline_result.get("matches", [])),
        },
        ip=ip,
    )
    await session.commit()
    await session.refresh(report)
    return STRMutationResponse(report=serialize_report_detail(report, org_name))


async def review_str_report(
    session: AsyncSession,
    *,
    report_id: str,
    user: AuthenticatedUser,
    request: STRReviewRequest,
    ip: str | None,
) -> STRMutationResponse:
    _ensure_review_access(user)
    report, org_name = await _fetch_report_with_org(session, report_id)

    if request.action == "assign":
        report.metadata_json = _append_lifecycle_event(
            report.metadata_json or {},
            action="assigned",
            user=user,
            from_status=report.status,
            to_status=report.status,
            note=request.note,
            assigned_to=request.assigned_to,
        )
    else:
        if report.status not in {"submitted", "under_review", "flagged"}:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="STR is not in a reviewable state.")
        next_status = _REVIEW_OUTCOMES[request.action]
        previous_status = report.status
        report.status = next_status
        report.reviewed_by = _as_uuid(user.user_id)
        report.metadata_json = _append_lifecycle_event(
            report.metadata_json or {},
            action=request.action,
            user=user,
            from_status=previous_status,
            to_status=next_status,
            note=request.note,
            assigned_to=request.assigned_to,
        )

    await _record_audit(
        session,
        report=report,
        user=user,
        action=f"str_report.review.{request.action}",
        details=request.model_dump(),
        ip=ip,
    )
    await session.commit()
    await session.refresh(report)
    return STRMutationResponse(report=serialize_report_detail(report, org_name))


async def enrich_str_report(
    session: AsyncSession,
    *,
    report_id: str,
    user: AuthenticatedUser,
    ip: str | None,
    orchestrator: AIOrchestrator | None = None,
) -> STREnrichmentSnapshot:
    report, _ = await _fetch_report_with_org(session, report_id)
    if user.role == "viewer":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Viewer accounts cannot generate enrichment.")

    ai = orchestrator or AIOrchestrator()
    narrative_payload = build_str_enrichment_payload(report)
    narrative_result: AIInvocationResult = await ai.invoke(
        task=AITaskName.STR_NARRATIVE,
        payload=narrative_payload,
        output_model=STRNarrativeResult,
        user=user,
        ip=ip,
    )
    extraction_seed = " ".join(
        value for value in [
            report.subject_name,
            report.subject_account,
            report.subject_phone,
            report.subject_wallet,
            report.subject_nid,
            report.narrative,
        ]
        if value
    )
    extraction_result: AIInvocationResult = await ai.invoke(
        task=AITaskName.ENTITY_EXTRACTION,
        payload={"raw_text": extraction_seed},
        output_model=EntityExtractionResult,
        user=user,
        ip=ip,
    )

    enrichment = STREnrichmentSnapshot(
        draft_narrative=narrative_result.output.narrative,
        missing_fields=narrative_result.output.missing_fields,
        category_suggestion=narrative_result.output.category_suggestion,
        severity_suggestion=narrative_result.output.severity_suggestion,
        trigger_facts=narrative_payload["trigger_facts"],
        extracted_entities=extraction_result.output.entities,
        generated_at=datetime.now(UTC),
        narrative_meta=AIInvocationMeta.model_validate(
            {
                "task": narrative_result.task,
                "provider": narrative_result.provider,
                "model": narrative_result.model,
                "prompt_version": narrative_result.prompt_version,
                "redaction_mode": narrative_result.redaction_mode,
                "fallback_used": narrative_result.fallback_used,
                "audit_logged": narrative_result.audit_logged,
                "attempts": [attempt.model_dump() for attempt in narrative_result.attempts],
            }
        ),
        extraction_meta=AIInvocationMeta.model_validate(
            {
                "task": extraction_result.task,
                "provider": extraction_result.provider,
                "model": extraction_result.model,
                "prompt_version": extraction_result.prompt_version,
                "redaction_mode": extraction_result.redaction_mode,
                "fallback_used": extraction_result.fallback_used,
                "audit_logged": extraction_result.audit_logged,
                "attempts": [attempt.model_dump() for attempt in extraction_result.attempts],
            }
        ),
    )
    metadata = deepcopy(report.metadata_json or {})
    metadata["enrichment"] = enrichment.model_dump(mode="json")
    report.metadata_json = _append_lifecycle_event(
        metadata,
        action="enriched",
        user=user,
        from_status=report.status,
        to_status=report.status,
    )
    await _record_audit(
        session,
        report=report,
        user=user,
        action="str_report.enriched",
        details={
            "category_suggestion": enrichment.category_suggestion,
            "severity_suggestion": enrichment.severity_suggestion,
            "missing_fields": enrichment.missing_fields,
        },
        ip=ip,
    )
    await session.commit()
    return enrichment
