from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import desc, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import AuthenticatedUser
from app.core.pipeline import run_scan_pipeline
from app.models.alert import Alert
from app.models.case import Case
from app.models.detection_run import DetectionRun
from app.models.entity import Entity
from app.models.match import Match
from app.schemas.scan import DetectionRunDetail, FlaggedAccount, ScanQueueRequest, ScanQueueResponse
from app.services.csv_ingest import ingest_csv
from app.services.storage import StorageError, upload_to_uploads_bucket


def _as_uuid(value: str | UUID | None) -> UUID | None:
    if value is None or value == "":
        return None
    if isinstance(value, UUID):
        return value
    try:
        return UUID(str(value))
    except ValueError:
        return None


def _as_float(value: Decimal | float | int | None) -> float:
    if value is None:
        return 0.0
    return float(value)


def _iso(value: datetime | None) -> str:
    if value is None:
        return datetime.now(UTC).isoformat()
    return value.astimezone(UTC).isoformat()


def _safe_int(value: object) -> int:
    if value is None:
        return 0
    return int(value)


def _safe_severity(value: str | None) -> str:
    return value or "low"


def _reason_summary(alert: Alert | None) -> str | None:
    if alert is None or not isinstance(alert.reasons, list):
        return None

    for reason in alert.reasons:
        if isinstance(reason, dict):
            explanation = reason.get("explanation")
            if isinstance(explanation, str) and explanation.strip():
                return explanation.strip()
    return None


def _serialize_flagged_account(
    entity: Entity,
    *,
    match: Match | None,
    alert: Alert | None,
    linked_case: Case | None,
) -> dict[str, object]:
    match_count = max(
        _safe_int(entity.report_count),
        len(entity.reporting_orgs or []),
        _safe_int(match.match_count) if match is not None else 0,
    )
    summary = (
        _reason_summary(alert)
        or (
            f"{entity.display_value} has cross-bank overlap across {match_count} institution"
            f"{'' if match_count == 1 else 's'}."
        )
    )

    return {
        "entity_id": str(entity.id),
        "account_number": entity.display_value,
        "account_name": entity.display_name or entity.display_value,
        "score": _safe_int(entity.risk_score),
        "severity": _safe_severity(entity.severity),
        "summary": summary,
        "matched_banks": match_count,
        "total_exposure": _as_float(entity.total_exposure),
        "tags": list(entity.tags or []),
        "linked_alert_id": str(alert.id) if alert is not None else None,
        "linked_case_id": str(linked_case.id) if linked_case is not None else None,
    }


def _results_summary(flagged_accounts: list[dict[str, object]]) -> str:
    if not flagged_accounts:
        return "No elevated accounts were identified for this organization in the current scan snapshot."
    highest = max(int(item["score"]) for item in flagged_accounts)
    return (
        f"{len(flagged_accounts)} account candidate"
        f"{'' if len(flagged_accounts) == 1 else 's'} flagged with highest score {highest}/100."
    )


def _serialize_run_summary(run: DetectionRun) -> dict[str, object]:
    return {
        "id": str(run.id),
        "file_name": run.file_name or "Untitled scan",
        "status": run.status,
        "alerts_generated": run.alerts_generated,
        "accounts_scanned": run.accounts_scanned,
        "tx_count": run.tx_count,
        "created_at": _iso(run.created_at),
        "started_at": _iso(run.started_at) if run.started_at else None,
        "completed_at": _iso(run.completed_at) if run.completed_at else None,
    }


def _serialize_run_detail(run: DetectionRun) -> dict[str, object]:
    results = run.results if isinstance(run.results, dict) else {}
    flagged_accounts = results.get("flagged_accounts", [])
    if not isinstance(flagged_accounts, list):
        flagged_accounts = []

    return {
        **_serialize_run_summary(run),
        "run_type": run.run_type,
        "summary": str(results.get("summary") or _results_summary(flagged_accounts)),
        "flagged_accounts": [
            FlaggedAccount.model_validate(item).model_dump()
            for item in flagged_accounts
            if isinstance(item, dict)
        ],
        "error": run.error,
    }


async def _fetch_run_or_404(session: AsyncSession, run_id: str) -> DetectionRun:
    parsed_id = _as_uuid(run_id)
    if parsed_id is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Detection run not found.")

    run = await session.get(DetectionRun, parsed_id)
    if run is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Detection run not found.")
    return run


async def _select_candidate_entities(session: AsyncSession, *, user: AuthenticatedUser) -> list[Entity]:
    org_uuid = _as_uuid(user.org_id)
    stmt = select(Entity).where(Entity.entity_type == "account")

    if user.org_type != "regulator":
        if org_uuid is None:
            return []
        stmt = stmt.where(Entity.reporting_orgs.any(org_uuid))

    stmt = stmt.order_by(
        desc(Entity.risk_score).nullslast(),
        desc(Entity.report_count),
        desc(Entity.total_exposure).nullslast(),
        desc(Entity.last_seen).nullslast(),
    ).limit(8)

    result = await session.execute(stmt)
    return list(result.scalars().all())


async def _fetch_match_map(session: AsyncSession, entity_ids: list[UUID]) -> dict[str, Match]:
    if not entity_ids:
        return {}
    result = await session.execute(
        select(Match)
        .where(Match.entity_id.in_(entity_ids))
        .order_by(desc(Match.risk_score).nullslast(), desc(Match.detected_at).nullslast())
    )
    match_map: dict[str, Match] = {}
    for match in result.scalars().all():
        match_map.setdefault(str(match.entity_id), match)
    return match_map


async def _fetch_alert_map(session: AsyncSession, entity_ids: list[UUID]) -> dict[str, Alert]:
    if not entity_ids:
        return {}
    result = await session.execute(
        select(Alert)
        .where(Alert.entity_id.in_(entity_ids))
        .order_by(desc(Alert.risk_score), desc(Alert.created_at).nullslast())
    )
    alert_map: dict[str, Alert] = {}
    for alert in result.scalars().all():
        if alert.entity_id is None:
            continue
        alert_map.setdefault(str(alert.entity_id), alert)
    return alert_map


async def _fetch_case_map(session: AsyncSession, entity_ids: list[UUID]) -> dict[str, Case]:
    if not entity_ids:
        return {}
    result = await session.execute(
        select(Case)
        .where(
            or_(
                *[Case.linked_entity_ids.any(entity_id) for entity_id in entity_ids],
            )
        )
        .order_by(desc(Case.updated_at).nullslast(), desc(Case.created_at).nullslast())
    )
    case_map: dict[str, Case] = {}
    for linked_case in result.scalars().all():
        for entity_id in linked_case.linked_entity_ids or []:
            case_map.setdefault(str(entity_id), linked_case)
    return case_map


async def list_runs(session: AsyncSession) -> list[dict[str, object]]:
    result = await session.execute(
        select(DetectionRun).order_by(desc(DetectionRun.created_at).nullslast(), desc(DetectionRun.started_at).nullslast())
    )
    return [_serialize_run_summary(run) for run in result.scalars().all()]


async def get_run_detail(session: AsyncSession, *, run_id: str) -> dict[str, object]:
    run = await _fetch_run_or_404(session, run_id)
    return _serialize_run_detail(run)


async def get_results(session: AsyncSession, *, run_id: str) -> list[dict[str, object]]:
    run = await _fetch_run_or_404(session, run_id)
    detail = _serialize_run_detail(run)
    return list(detail["flagged_accounts"])


async def queue_run(
    session: AsyncSession,
    *,
    user: AuthenticatedUser,
    request: ScanQueueRequest,
) -> ScanQueueResponse:
    org_uuid = _as_uuid(user.org_id)
    if org_uuid is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid organization id.")

    now = datetime.now(UTC)
    run = DetectionRun(
        org_id=org_uuid,
        run_type="upload",
        status="pending",
        file_name=(request.file_name or f"{user.org_type}-network-scan-{now:%Y%m%d-%H%M%S}.csv").strip(),
        file_url=None,
        tx_count=0,
        accounts_scanned=0,
        alerts_generated=0,
        results={
            "summary": "queued",
            "selected_rules": list(request.selected_rules),
            "flagged_accounts": [],
        },
        triggered_by=_as_uuid(user.user_id),
        started_at=None,
        completed_at=None,
        error=None,
    )
    session.add(run)
    await session.flush()

    scope_org_ids: list[UUID] | None = (
        None if user.org_type == "regulator" else [org_uuid]
    )

    try:
        await run_scan_pipeline(
            session,
            run_id=run.id,
            org_id=org_uuid,
            scope_org_ids=scope_org_ids,
        )
    except Exception as exc:
        run.status = "failed"
        run.error = str(exc)
        run.completed_at = datetime.now(UTC)

    await session.commit()
    await session.refresh(run)

    return ScanQueueResponse(
        run=DetectionRunDetail.model_validate(_serialize_run_detail(run)),
        message=(
            "Detection pipeline executed over current transactions."
            if run.status == "completed"
            else f"Detection run ended with status {run.status}."
        ),
    )


async def queue_run_with_upload(
    session: AsyncSession,
    *,
    user: AuthenticatedUser,
    file_name: str,
    content_bytes: bytes,
    selected_rules: list[str],
) -> ScanQueueResponse:
    """Upload path: ingest a CSV, tag transactions with run_id, scan those only."""
    org_uuid = _as_uuid(user.org_id)
    if org_uuid is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid organization id.")

    safe_name = (file_name or "upload.csv").strip() or "upload.csv"
    now = datetime.now(UTC)

    run = DetectionRun(
        org_id=org_uuid,
        run_type="upload",
        status="processing",
        file_name=safe_name,
        file_url=None,
        tx_count=0,
        accounts_scanned=0,
        alerts_generated=0,
        results={
            "summary": "processing upload",
            "selected_rules": list(selected_rules),
            "flagged_accounts": [],
        },
        triggered_by=_as_uuid(user.user_id),
        started_at=now,
        completed_at=None,
        error=None,
    )
    session.add(run)
    await session.flush()

    # Best-effort upload of the raw file. Storage down ≠ failed scan.
    storage_path = f"{org_uuid}/{run.id}/{safe_name}"
    try:
        run.file_url = await upload_to_uploads_bucket(
            path=storage_path,
            content=content_bytes,
            content_type="text/csv",
        )
    except StorageError:
        # Swallow — ingestion can still proceed
        run.file_url = None

    # Decode and ingest
    try:
        content_str = content_bytes.decode("utf-8-sig")
    except UnicodeDecodeError:
        content_str = content_bytes.decode("latin-1")

    try:
        ingest_summary = await ingest_csv(
            session, run_id=run.id, org_id=org_uuid, content=content_str
        )
    except HTTPException as exc:
        run.status = "failed"
        run.error = str(exc.detail)
        run.completed_at = datetime.now(UTC)
        await session.commit()
        await session.refresh(run)
        raise

    run.tx_count = int(ingest_summary.get("tx_count", 0))

    scope_org_ids = None if user.org_type == "regulator" else [org_uuid]

    try:
        await run_scan_pipeline(
            session,
            run_id=run.id,
            org_id=org_uuid,
            scope_org_ids=scope_org_ids,
            source_run_id=run.id,
        )
    except Exception as exc:
        run.status = "failed"
        run.error = str(exc)
        run.completed_at = datetime.now(UTC)

    await session.commit()
    await session.refresh(run)

    return ScanQueueResponse(
        run=DetectionRunDetail.model_validate(_serialize_run_detail(run)),
        message=(
            f"Ingested {run.tx_count} transactions and ran detection."
            if run.status == "completed"
            else f"Detection run ended with status {run.status}."
        ),
    )
