"""goAML XML import — create an STR from an uploaded report.

End-to-end:
1. Parse the XML via app.parsers.goaml_xml.
2. Open a DetectionRun row (run_type="str_triggered") as the import batch.
3. Create an STRReport seeded from the parsed header, in draft status.
4. Insert one Transaction per parsed transaction, tagged with run_id.
5. Walk every subject identifier through core.resolver.resolve_identifier
   so shared intelligence sees the new signals.
6. Close the DetectionRun with counts and return a summary.

Not the same as run_str_pipeline — that fires on submit. Import leaves
the STR as a draft so the analyst can review AI enrichment before
submitting.
"""
from datetime import UTC, datetime
from uuid import UUID
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import AuthenticatedUser
from app.core.resolver import resolve_identifier
from app.models.audit import AuditLog
from app.models.detection_run import DetectionRun
from app.models.entity import Entity
from app.models.str_report import STRReport
from app.models.transaction import Transaction
from app.parsers.goaml_xml import (
    GoAMLParseError,
    ParsedReport,
    SubjectIdentifier,
    parse_goaml_report,
)
from app.schemas.xml_import import XMLImportResponse


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


def _subject_kind_to_entity_type(kind: str) -> str | None:
    mapping = {
        "account": "account",
        "phone": "phone",
        "wallet": "wallet",
        "nid": "nid",
        "person": "person",
        "entity": "business",
    }
    return mapping.get(kind)


async def _resolve_subjects(
    session: AsyncSession,
    *,
    report: ParsedReport,
    org_id: UUID,
) -> tuple[int, list[str]]:
    resolved_count = 0
    resolved_ids: list[str] = []
    seen: set[tuple[str, str]] = set()

    # Build a working list that includes the primary subject slots too —
    # resolve_identifier is idempotent so duplicates are safe but we dedup
    # via (entity_type, canonical-ish key).
    working: list[SubjectIdentifier] = list(report.subjects)
    primary: list[tuple[str, str, str | None]] = [
        ("account", report.subject_account, report.subject_name),
        ("phone", report.subject_phone, None),
        ("wallet", report.subject_wallet, None),
        ("nid", report.subject_nid, None),
    ]
    if report.subject_name and not any(subject.kind == "entity" for subject in report.subjects):
        primary.append(("entity", report.subject_name, report.subject_name))

    for kind, value, display in primary:
        if value:
            working.append(SubjectIdentifier(role="about", kind=kind, value=value, display_name=display))

    for subject in working:
        entity_type = _subject_kind_to_entity_type(subject.kind)
        if entity_type is None:
            continue
        if not subject.value:
            continue
        dedup_key = (entity_type, subject.value.strip().upper())
        if dedup_key in seen:
            continue
        seen.add(dedup_key)
        try:
            entity: Entity = await resolve_identifier(
                session,
                entity_type=entity_type,
                raw_value=subject.value,
                org_id=org_id,
                source="str_cross_ref",
                display_name=subject.display_name,
            )
        except ValueError:
            continue
        resolved_count += 1
        resolved_ids.append(str(entity.id))

    return resolved_count, resolved_ids


async def import_goaml_xml(
    session: AsyncSession,
    *,
    user: AuthenticatedUser,
    xml_bytes: bytes,
    file_name: str | None,
    ip: str | None,
) -> XMLImportResponse:
    org_uuid = _require_uuid(user.org_id, "Authenticated user is missing a valid organization id.")

    try:
        parsed = parse_goaml_report(xml_bytes)
    except GoAMLParseError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    # Open a detection run as the import batch — its run_id tags every
    # Transaction inserted below so downstream scans can scope to this import.
    started_at = datetime.now(UTC)
    run = DetectionRun(
        org_id=org_uuid,
        run_type="str_triggered",
        status="processing",
        file_name=file_name,
        tx_count=0,
        accounts_scanned=0,
        alerts_generated=0,
        results={},
        triggered_by=_as_uuid(user.user_id),
        started_at=started_at,
    )
    session.add(run)
    await session.flush()

    # Create the STR in draft state. The submit endpoint will fire the
    # downstream pipeline later — this endpoint only ingests raw signals.
    report = STRReport(
        org_id=org_uuid,
        report_ref="",
        report_type=parsed.report_type,
        status="draft",
        subject_name=parsed.subject_name,
        subject_account=parsed.subject_account,
        subject_bank=parsed.subject_bank,
        subject_phone=parsed.subject_phone,
        subject_wallet=parsed.subject_wallet,
        subject_nid=parsed.subject_nid,
        total_amount=float(parsed.total_amount or 0),
        currency=parsed.currency or "BDT",
        transaction_count=len(parsed.transactions),
        primary_channel=parsed.primary_channel,
        category="other",
        narrative=parsed.narrative,
        channels=[parsed.primary_channel] if parsed.primary_channel else [],
        date_range_start=parsed.date_range_start,
        date_range_end=parsed.date_range_end,
        metadata_json={
            "source": "goaml_xml_import",
            "file_name": file_name,
            "submission_code": parsed.submission_code,
            "report_code": parsed.report_code,
            "reporting_entity_id": parsed.reporting_entity_id,
            "reporting_person_name": parsed.reporting_person_name,
            "detection_run_id": str(run.id),
            "warnings": list(parsed.warnings),
        },
    )
    session.add(report)
    await session.flush()

    # Insert transactions tagged with the run_id.
    tx_inserted = 0
    for parsed_tx in parsed.transactions:
        posted_at = parsed_tx.posted_at or datetime.now(UTC)
        session.add(
            Transaction(
                org_id=org_uuid,
                run_id=run.id,
                posted_at=posted_at,
                amount=float(parsed_tx.amount or 0),
                currency=parsed_tx.currency or "BDT",
                channel=parsed_tx.channel,
                description=parsed_tx.description,
                metadata_json={
                    "transaction_ref": parsed_tx.transaction_ref,
                    "source_account": parsed_tx.source_account,
                    "destination_account": parsed_tx.destination_account,
                    "source": "goaml_xml_import",
                    "str_report_id": str(report.id),
                },
            )
        )
        tx_inserted += 1

    # Resolve subjects into the shared entity pool.
    resolved_count, resolved_ids = await _resolve_subjects(
        session, report=parsed, org_id=org_uuid
    )
    if resolved_ids:
        report.matched_entity_ids = [UUID(value) for value in resolved_ids]

    # Close the run.
    run.tx_count = tx_inserted
    run.alerts_generated = 0
    run.status = "completed"
    run.completed_at = datetime.now(UTC)
    run.results = {
        "summary": {
            "imported_report_id": str(report.id),
            "transactions_ingested": tx_inserted,
            "subjects_resolved": resolved_count,
            "warnings": list(parsed.warnings),
        }
    }

    audit_details: dict[str, Any] = {
        "detection_run_id": str(run.id),
        "report_id": str(report.id),
        "submission_code": parsed.submission_code,
        "report_type": parsed.report_type,
        "transactions_ingested": tx_inserted,
        "subjects_resolved": resolved_count,
        "file_name": file_name,
    }
    session.add(
        AuditLog(
            org_id=org_uuid,
            user_id=_as_uuid(user.user_id),
            action="str_report.xml_imported",
            resource_type="str_report",
            resource_id=report.id,
            details=audit_details,
            ip=ip,
        )
    )
    await session.commit()
    await session.refresh(report)

    return XMLImportResponse(
        report_id=str(report.id),
        report_ref=report.report_ref,
        report_type=report.report_type,
        detection_run_id=str(run.id),
        transactions_ingested=tx_inserted,
        subjects_resolved=resolved_count,
        warnings=list(parsed.warnings),
        status="partial" if parsed.warnings else "ok",
    )
