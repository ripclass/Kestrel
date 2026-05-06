"""Scheduled watchlist-ingestion task (V2 phase 4.1).

Runs daily at 02:30 BDT (after the 02:00 nightly scan finishes).
For each configured source, fetches + parses + upserts into
``watchlist_entries`` keyed by the unique index defined in migration 015.

Each source is independent — a failure in OFAC ingestion doesn't block UN
ingestion. Errors are logged + reported in the task return value; a
follow-up alert / ticket is the operator's job (Phase 6 hooks this into
the public status page).

Live ingestion is opt-in via ``KESTREL_WATCHLIST_INGESTION_ENABLED=true``.
By default the task is a no-op so the synthetic seed in
``seed/load_watchlist_synthetic.py`` remains the source of truth and we
don't accidentally pull external bytes onto the engine container until
the operator turns it on.
"""
from __future__ import annotations

import asyncio
import logging
import os
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.database import SessionLocal
from app.models.watchlist import WatchlistEntry
from app.screening.sources import ofac, un, uk_ofsi
from app.screening.sources.base import ParsedWatchlistEntry
from app.tasks.celery_app import celery_app

# Shared with seed.load_watchlist_synthetic so a synthetic OFAC row and a
# live-ingested OFAC row with the same (source, name, dob) collide on the PK.
_NAMESPACE = uuid.UUID("8d393384-a67a-4b64-bf0b-7b66b8d5da76")

logger = logging.getLogger("kestrel.tasks.screening")

# Module-level registry — easy to extend in Phase 6.
_SOURCES: list[Any] = [ofac, un, uk_ofsi]


def _ingestion_enabled() -> bool:
    return os.environ.get("KESTREL_WATCHLIST_INGESTION_ENABLED", "false").lower() == "true"


def _max_body_bytes() -> int:
    """Per-source body-size cap. Defaults to 35 MB so the OFAC SDN.XML
    (~28 MB) still parses on a 512 MB worker but the unified UK list
    (~48 MB CSV) gets skipped with a warning. Operators bumping the
    worker plan to 1 GB+ can raise the cap via env."""
    raw = os.environ.get("KESTREL_WATCHLIST_MAX_BODY_MB", "35")
    try:
        return max(1, int(raw)) * 1024 * 1024
    except ValueError:
        return 35 * 1024 * 1024


@celery_app.task(name="app.tasks.screening_tasks.refresh_all")
def refresh_all() -> dict[str, Any]:
    """Beat-driven entrypoint. Runs every configured source in turn."""
    if not _ingestion_enabled():
        logger.info("watchlist.ingestion.disabled")
        summary = {"status": "disabled", "sources": []}
        asyncio.run(_persist_run_summary(summary))
        return summary

    try:
        results = asyncio.run(_run_all())
        summary = {
            "status": "completed",
            "ran_at": datetime.now(UTC).isoformat(),
            "sources": results,
            "ingested_total": sum(r.get("ingested", 0) for r in results),
        }
    except Exception as exc:  # noqa: BLE001 — surface raw failure so we can diagnose
        summary = {
            "status": "crashed",
            "ran_at": datetime.now(UTC).isoformat(),
            "error_type": type(exc).__name__,
            "error": str(exc)[:500],
            "sources": [],
            "ingested_total": 0,
        }
    logger.info("watchlist.ingestion.batch", extra={"summary": summary})
    asyncio.run(_persist_run_summary(summary))
    return summary


async def _persist_run_summary(summary: dict[str, Any]) -> None:
    """Append a row to audit_log so the run outcome is queryable via SQL.

    Lets operators (or this codebase's Supabase MCP probes) see the last
    refresh result without scraping worker logs. Best-effort — a write
    failure here is logged but not raised, so a DB hiccup never wedges
    the task itself."""
    from sqlalchemy import insert

    from app.database import SessionLocal
    from app.models.audit import AuditLog

    try:
        async with SessionLocal() as session:
            async with session.begin():
                await session.execute(
                    insert(AuditLog).values(
                        action="watchlist.refresh",
                        details=summary,
                    )
                )
    except Exception as exc:  # noqa: BLE001 — never let logging crash the task
        logger.warning("watchlist.run_summary.persist_failed", extra={"error": str(exc)[:200]})


async def _run_all() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for source in _SOURCES:
        rows.append(await _run_one(source))
    return rows


async def _run_one(source: Any) -> dict[str, Any]:
    name = getattr(source, "LIST_SOURCE", source.__name__)
    try:
        content = await source.fetch()
        size_bytes = len(content)
        cap = _max_body_bytes()
        if size_bytes > cap:
            logger.warning(
                "watchlist.source.skipped_oversized",
                extra={"source": name, "size_bytes": size_bytes, "cap_bytes": cap},
            )
            return {
                "source": name,
                "ingested": 0,
                "skipped_reason": f"body {size_bytes} bytes exceeds cap {cap}; raise KESTREL_WATCHLIST_MAX_BODY_MB or bump worker plan",
            }
        parsed = source.parse(content)
        ingested = await _upsert_batch(parsed)
    except NotImplementedError as exc:
        logger.info("watchlist.source.not_implemented", extra={"source": name})
        return {"source": name, "ingested": 0, "skipped_reason": str(exc)}
    except Exception as exc:  # noqa: BLE001 — defensive, we don't want one source to kill the batch
        logger.warning(
            "watchlist.source.failed",
            extra={"source": name, "error_type": type(exc).__name__, "error": str(exc)[:200]},
        )
        return {"source": name, "ingested": 0, "error": type(exc).__name__}
    return {"source": name, "ingested": ingested}


def _row_id(row: ParsedWatchlistEntry) -> uuid.UUID:
    """Deterministic PK so re-ingestion of an identical row is a no-op."""
    raw = f"{row.list_source}|{row.primary_name}|{row.date_of_birth.isoformat() if row.date_of_birth else 'na'}"
    return uuid.uuid5(_NAMESPACE, raw)


_UPSERT_COLS_PER_ROW = 12  # id, list_source, list_version, entry_type, primary_name,
                            # aliases, date_of_birth, nationality, identifiers,
                            # addresses, reason, raw_record
_PG_BIND_LIMIT = 32_767  # PostgreSQL hard limit on bind parameters per query
# Stay comfortably under the limit: 32767 / 12 ≈ 2730. Use 2000 to leave
# headroom and to keep individual transaction times bounded.
_UPSERT_CHUNK_SIZE = 2000


async def _upsert_batch(rows: list[ParsedWatchlistEntry]) -> int:
    """Idempotent upsert keyed off the deterministic PK from ``_row_id``.

    Chunks into ``_UPSERT_CHUNK_SIZE``-row sub-batches. The OFAC SDN list
    has ~12-15k entries; a single multi-row INSERT would hit Postgres'
    32767 bind-parameter limit (12 cols × 12k rows = 144k binds). Chunked
    UPSERTs keep us under the limit and bound the per-statement work."""
    if not rows:
        return 0
    payload = [
        {
            "id": _row_id(row),
            "list_source": row.list_source,
            "list_version": row.list_version,
            "entry_type": row.entry_type,
            "primary_name": row.primary_name,
            "aliases": list(row.aliases),
            "date_of_birth": row.date_of_birth,
            "nationality": row.nationality,
            "identifiers": row.identifiers or {},
            "addresses": row.addresses or [],
            "reason": row.reason,
            "raw_record": row.raw_record or {},
        }
        for row in rows
    ]
    total = 0
    async with SessionLocal() as session:
        for offset in range(0, len(payload), _UPSERT_CHUNK_SIZE):
            chunk = payload[offset : offset + _UPSERT_CHUNK_SIZE]
            async with session.begin():
                stmt = (
                    pg_insert(WatchlistEntry.__table__)
                    .values(chunk)
                    .on_conflict_do_nothing(index_elements=["id"])
                )
                await session.execute(stmt)
            total += len(chunk)
    return total
