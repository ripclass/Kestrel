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

from sqlalchemy import func, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool

from app.config import get_settings
from app.models.watchlist import WatchlistEntry
from app.screening.sources import bis, ofac, un, uk_ofsi
from app.screening.sources.base import ParsedWatchlistEntry
from app.tasks.celery_app import celery_app

# Shared with seed.load_watchlist_synthetic so a synthetic OFAC row and a
# live-ingested OFAC row with the same (source, name, dob) collide on the PK.
_NAMESPACE = uuid.UUID("8d393384-a67a-4b64-bf0b-7b66b8d5da76")

logger = logging.getLogger("kestrel.tasks.screening")

# Module-level registry — easy to extend in Phase 6.
_SOURCES: list[Any] = [ofac, un, uk_ofsi, bis]


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
    return asyncio.run(_orchestrate())


async def _orchestrate() -> dict[str, Any]:
    """Run the full watchlist refresh in a single event loop using a
    per-task NullPool engine.

    The Celery worker is a long-lived process; the global ``SessionLocal``
    engine in ``app.database`` retains asyncpg connections in its pool
    across task invocations. Each ``asyncio.run`` call closes its event
    loop, leaving those pooled connections bound to a dead transport.
    The next task invocation pulls a stale connection and asyncpg
    surfaces it as InterfaceError. Creating a fresh NullPool engine per
    task and disposing it on exit keeps every invocation self-contained.
    See ``app/tasks/_runtime.py`` for the same pattern."""
    settings = get_settings()
    engine = create_async_engine(
        settings.database_url,
        poolclass=NullPool,
        future=True,
        echo=False,
    )
    factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    try:
        if not _ingestion_enabled():
            logger.info("watchlist.ingestion.disabled")
            summary: dict[str, Any] = {"status": "disabled", "sources": []}
            await _persist_run_summary(factory, summary)
            return summary

        try:
            results = await _run_all(factory)
            summary = {
                "status": "completed",
                "ran_at": datetime.now(UTC).isoformat(),
                "sources": results,
                "ingested_total": sum(r.get("ingested", 0) for r in results),
                "removed_total": sum(r.get("removed", 0) for r in results),
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
        await _persist_run_summary(factory, summary)
        return summary
    finally:
        await engine.dispose()


async def _persist_run_summary(
    factory: async_sessionmaker[AsyncSession], summary: dict[str, Any]
) -> None:
    """Append a row to audit_log so the run outcome is queryable via SQL.

    Lets operators (or this codebase's Supabase MCP probes) see the last
    refresh result without scraping worker logs. Best-effort — a write
    failure here is logged but not raised, so a DB hiccup never wedges
    the task itself."""
    from sqlalchemy import insert

    from app.models.audit import AuditLog

    try:
        async with factory() as session:
            async with session.begin():
                await session.execute(
                    insert(AuditLog).values(
                        action="watchlist.refresh",
                        details=summary,
                    )
                )
    except Exception as exc:  # noqa: BLE001 — never let logging crash the task
        logger.warning("watchlist.run_summary.persist_failed", extra={"error": str(exc)[:200]})


async def _run_all(factory: async_sessionmaker[AsyncSession]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for source in _SOURCES:
        rows.append(await _run_one(factory, source))
    return rows


async def _run_one(
    factory: async_sessionmaker[AsyncSession], source: Any
) -> dict[str, Any]:
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
        ingested = await _upsert_batch(factory, parsed)
        reconcile = {"reconciled": False, "removed": 0}
        if parsed:
            # All rows in a feed share one list_version; entries NOT carrying
            # this run's version are delistings (or stale and were not re-sent).
            reconcile = await _reconcile_delistings(
                factory, list_source=name, run_version=parsed[0].list_version, parsed_count=len(parsed)
            )
    except NotImplementedError as exc:
        logger.info("watchlist.source.not_implemented", extra={"source": name})
        return {"source": name, "ingested": 0, "skipped_reason": str(exc)}
    except Exception as exc:  # noqa: BLE001 — defensive, we don't want one source to kill the batch
        import traceback

        tb_tail = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))[-1200:]
        logger.warning(
            "watchlist.source.failed",
            extra={"source": name, "error_type": type(exc).__name__, "error": str(exc)[:200]},
        )
        return {
            "source": name,
            "ingested": 0,
            "error": type(exc).__name__,
            "error_message": str(exc)[:500],
            "traceback_tail": tb_tail,
        }
    result = {"source": name, "ingested": ingested, "removed": reconcile.get("removed", 0)}
    if not reconcile.get("reconciled", False) and reconcile.get("reason"):
        result["reconcile_skipped_reason"] = reconcile["reason"]
    return result


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


# Don't reconcile delistings unless the new feed is at least this fraction of
# the existing active live set. A feed that suddenly came back at < half size
# is far more likely a fetch/parse failure than a real mass delisting — and we
# must never mass-remove real sanctions entries off a truncated download.
_RECONCILE_MIN_RATIO = 0.5


def _should_reconcile(parsed_count: int, existing_active_live: int) -> bool:
    """Safety gate for delisting reconciliation. Pure so it's unit-testable."""
    if parsed_count <= 0:
        return False
    if existing_active_live <= 0:
        return True  # nothing to remove — reconciliation is a no-op
    return parsed_count >= _RECONCILE_MIN_RATIO * existing_active_live


async def _upsert_batch(
    factory: async_sessionmaker[AsyncSession], rows: list[ParsedWatchlistEntry]
) -> int:
    """Upsert keyed off the deterministic PK from ``_row_id``, refreshing
    mutable fields on conflict so a changed entry (new alias / identifier /
    program / reason) doesn't stay stale — the old ``DO NOTHING`` silently
    dropped every change. Also clears ``removed_at`` so a re-listed entry is
    reactivated. Identity columns (id / list_source / primary_name /
    date_of_birth) are left untouched; the conflict row shares them by
    construction.

    Chunks into ``_UPSERT_CHUNK_SIZE``-row sub-batches to stay under Postgres'
    32767 bind-parameter limit. Returns the number of rows processed."""
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
    async with factory() as session:
        for offset in range(0, len(payload), _UPSERT_CHUNK_SIZE):
            chunk = payload[offset : offset + _UPSERT_CHUNK_SIZE]
            async with session.begin():
                insert_stmt = pg_insert(WatchlistEntry.__table__).values(chunk)
                upsert = insert_stmt.on_conflict_do_update(
                    index_elements=["id"],
                    set_={
                        "list_version": insert_stmt.excluded.list_version,
                        "entry_type": insert_stmt.excluded.entry_type,
                        "aliases": insert_stmt.excluded.aliases,
                        "nationality": insert_stmt.excluded.nationality,
                        "identifiers": insert_stmt.excluded.identifiers,
                        "addresses": insert_stmt.excluded.addresses,
                        "reason": insert_stmt.excluded.reason,
                        "raw_record": insert_stmt.excluded.raw_record,
                        "ingested_at": func.now(),
                        "removed_at": None,
                    },
                )
                await session.execute(upsert)
            total += len(chunk)
    return total


# Synthetic seed rows carry raw_record->>'source' = 'synthetic'. Live
# reconciliation must NEVER soft-remove them (they're demo data sharing the
# same table + id space as live entries).
_SYNTHETIC_MARKER = "synthetic"


async def _reconcile_delistings(
    factory: async_sessionmaker[AsyncSession],
    *,
    list_source: str,
    run_version: str,
    parsed_count: int,
) -> dict[str, Any]:
    """Soft-delete entries that fell off the upstream list.

    The upsert stamped every current entry with this run's ``list_version``;
    any still-active LIVE entry of this source NOT carrying that version is a
    delisting (no longer published) and is marked ``removed_at = now()`` so it
    stops producing false-positive matches. Guarded by ``_should_reconcile``
    against a truncated feed, and scoped away from synthetic seed rows."""
    async with factory() as session:
        existing_active_live = await session.scalar(
            select(func.count())
            .select_from(WatchlistEntry.__table__)
            .where(
                WatchlistEntry.list_source == list_source,
                WatchlistEntry.removed_at.is_(None),
                func.coalesce(WatchlistEntry.raw_record.op("->>")("source"), "") != _SYNTHETIC_MARKER,
            )
        )
        existing = int(existing_active_live or 0)
        if not _should_reconcile(parsed_count, existing):
            logger.warning(
                "watchlist.reconcile.skipped",
                extra={"source": list_source, "parsed": parsed_count, "existing_active_live": existing},
            )
            return {
                "reconciled": False,
                "removed": 0,
                "reason": f"feed size {parsed_count} below {_RECONCILE_MIN_RATIO:.0%} of {existing} active — skipped to avoid mass false removal",
            }

        async with session.begin():
            result = await session.execute(
                update(WatchlistEntry.__table__)
                .where(
                    WatchlistEntry.list_source == list_source,
                    WatchlistEntry.removed_at.is_(None),
                    WatchlistEntry.list_version != run_version,
                    func.coalesce(WatchlistEntry.raw_record.op("->>")("source"), "") != _SYNTHETIC_MARKER,
                )
                .values(removed_at=func.now())
            )
            removed = result.rowcount or 0
        if removed:
            logger.info(
                "watchlist.reconcile.removed",
                extra={"source": list_source, "removed": removed, "run_version": run_version},
            )
        return {"reconciled": True, "removed": removed}
