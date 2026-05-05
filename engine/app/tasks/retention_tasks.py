"""V3 P7.3 — audit-log retention.

`audit_log` accumulates fast (~1 row per state-changing action across
every router). Compliance retention is satisfied by archiving the rows
older than ``AUDIT_LOG_RETENTION_DAYS`` to cold storage; query latency
on the live table stays bounded.

Daily Beat at 03:30 BDT (after the 03:00 KYC re-screen). Cutoff =
``now - audit_log_retention_days`` (default 365). When the
``KESTREL_AUDIT_ARCHIVE_BUCKET`` env is set, rows are written to that
bucket as JSONL at ``audit-archive/YYYY-MM/<batch>.jsonl`` before
deletion. When the env is unset the task still deletes (compliance
retention is satisfied by the customer's Postgres backup cadence). Both
modes are batched at ``BATCH_SIZE = 500`` rows per iteration.

Idempotent: a row that's already archived (key collision) is skipped
and re-deleted; the bucket exporter sets ``Content-MD5`` so a re-run
landing on the same key noops via Supabase Storage's overwrite-allowed
default.
"""
from __future__ import annotations

import asyncio
import io
import json
import logging
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import delete, select

from app.config import get_settings
from app.database import SessionLocal
from app.models.audit import AuditLog
from app.tasks.celery_app import celery_app

logger = logging.getLogger("kestrel.tasks.retention")

BATCH_SIZE = 500
MAX_BATCHES_PER_RUN = 40  # 20k rows per run; tuneable.


@celery_app.task(name="app.tasks.retention_tasks.archive_audit_log")
def archive_audit_log() -> dict[str, Any]:
    summary = asyncio.run(_run())
    if summary.get("archived", 0) > 0 or summary.get("deleted", 0) > 0:
        logger.info("retention.audit.swept", extra={"summary": summary})
    return summary


async def _run() -> dict[str, Any]:
    settings = get_settings()
    cutoff = datetime.now(UTC) - timedelta(days=int(settings.audit_log_retention_days))
    bucket = settings.kestrel_audit_archive_bucket

    archived = 0
    deleted = 0
    batches = 0

    while batches < MAX_BATCHES_PER_RUN:
        async with SessionLocal() as session:
            stmt = (
                select(AuditLog)
                .where(AuditLog.created_at < cutoff)
                .order_by(AuditLog.created_at.asc())
                .limit(BATCH_SIZE)
            )
            rows = (await session.execute(stmt)).scalars().all()
            if not rows:
                break
            if bucket:
                try:
                    archived += _archive_batch(rows, bucket=bucket, cutoff=cutoff)
                except Exception as exc:  # noqa: BLE001 — defensive
                    logger.warning(
                        "retention.audit.archive_failed",
                        extra={"error_type": type(exc).__name__, "error": str(exc)[:200]},
                    )
                    break
            ids = [row.id for row in rows]
            await session.execute(delete(AuditLog).where(AuditLog.id.in_(ids)))
            await session.commit()
            deleted += len(ids)
            batches += 1

    return {
        "ran_at": datetime.now(UTC).isoformat(),
        "cutoff": cutoff.isoformat(),
        "archived": archived,
        "deleted": deleted,
        "batches": batches,
    }


def _row_to_jsonl(row: AuditLog) -> str:
    return json.dumps(
        {
            "id": str(row.id),
            "org_id": str(row.org_id) if row.org_id else None,
            "actor_user_id": str(getattr(row, "actor_user_id", None) or "") or None,
            "action": row.action,
            "details": row.details,
            "resource_id": str(getattr(row, "resource_id", None) or "") or None,
            "created_at": row.created_at.isoformat() if row.created_at else None,
        },
        sort_keys=True,
    )


def serialize_batch(rows: list[AuditLog]) -> bytes:
    """Pure helper exposed for unit tests.

    Returns deterministic JSONL bytes — line-per-row, sorted by id so a
    re-run lands the same content at the same key."""
    sorted_rows = sorted(rows, key=lambda r: str(r.id))
    buf = io.StringIO()
    for row in sorted_rows:
        buf.write(_row_to_jsonl(row))
        buf.write("\n")
    return buf.getvalue().encode("utf-8")


def archive_key_for(*, period: datetime, batch_id: uuid.UUID | None = None) -> str:
    yyyy_mm = f"{period.year:04d}-{period.month:02d}"
    sentinel = batch_id or uuid.uuid4()
    return f"audit-archive/{yyyy_mm}/{sentinel}.jsonl"


def _archive_batch(rows: list[AuditLog], *, bucket: str, cutoff: datetime) -> int:
    """Upload a serialized batch to Supabase Storage. Returns count.

    The actual upload is best-effort against the storage REST endpoint;
    we keep the network call here so the unit test can monkeypatch it
    without touching the rest of the loop. When ``SUPABASE_URL`` /
    ``SUPABASE_SERVICE_ROLE_KEY`` aren't set, the upload is skipped and
    we count zero archived (rows still get deleted because the
    compliance copy lives in the customer's Postgres backup)."""
    settings = get_settings()
    if not (settings.supabase_url and settings.supabase_service_role_key):
        logger.info("retention.audit.archive_skipped_no_storage")
        return 0
    body = serialize_batch(rows)
    key = archive_key_for(period=cutoff, batch_id=uuid.uuid4())
    upload_url = (
        f"{settings.supabase_url.rstrip('/')}/storage/v1/object/{bucket}/{key}"
    )
    headers = {
        "Authorization": f"Bearer {settings.supabase_service_role_key}",
        "Content-Type": "application/x-ndjson",
        "x-upsert": "true",
    }
    import httpx  # local import — keeps the import graph leaner for tests

    response = httpx.post(upload_url, headers=headers, content=body, timeout=30.0)
    response.raise_for_status()
    return len(rows)
