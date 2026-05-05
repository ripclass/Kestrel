"""Uptime ledger Beat task (V2 phase 6.1).

Runs ``app.services.readiness.build_readiness_report`` every 5 minutes
and writes one row per check into ``uptime_pings``. The public status
page reads this ledger to compute 30/90-day uptime percentages.

Failure paths are silenced (a database outage shouldn't make this task
itself crash and lose subsequent checks) — the absence of a recent ping
is itself the signal the public page surfaces as ``unknown``.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.config import get_settings
from app.database import SessionLocal
from app.models.status import UptimePing
from app.services.readiness import build_readiness_report
from app.tasks.celery_app import celery_app

logger = logging.getLogger("kestrel.tasks.status")


def _map_status(check_status: str) -> str:
    """Translate /ready check states to uptime ping states."""
    if check_status == "ok":
        return "up"
    if check_status in {"degraded", "warning"}:
        return "degraded"
    if check_status == "skipped":
        return "up"  # configured but probe disabled — treat as up.
    if check_status == "missing_config":
        return "unknown"
    return "down"


def _component_for_check(check_name: str) -> str:
    """Collapse `ai:openai` / `ai:anthropic` into one logical `ai` component
    on the public status page."""
    if check_name.startswith("ai:"):
        return "ai"
    return check_name


@celery_app.task(name="app.tasks.status_tasks.record_uptime_ping")
def record_uptime_ping() -> dict[str, Any]:
    """Beat-driven entrypoint."""
    summary = asyncio.run(_run())
    if summary.get("written", 0) > 0:
        logger.info("status.uptime.ping", extra={"summary": summary})
    return summary


async def _run() -> dict[str, Any]:
    settings = get_settings()
    try:
        report = await build_readiness_report(settings)
    except Exception as exc:  # noqa: BLE001
        logger.warning("status.uptime.report_failed", extra={"error_type": type(exc).__name__})
        return {"status": "report_failed", "written": 0}

    rows: dict[str, dict[str, Any]] = {}
    for check in report.checks:
        component = _component_for_check(check.name)
        # Take the worst state when multiple checks roll into one component
        # (e.g. ai:openai + ai:anthropic both roll into 'ai').
        status = _map_status(check.status)
        existing = rows.get(component)
        if existing is None or _is_worse(status, existing["status"]):
            rows[component] = {
                "component": component,
                "status": status,
                "latency_ms": None,
                "detail": check.detail[:500] if check.detail else None,
            }

    payload = list(rows.values())
    if not payload:
        return {"status": "empty", "written": 0}

    try:
        async with SessionLocal() as session:
            async with session.begin():
                stmt = pg_insert(UptimePing.__table__).values(payload)
                await session.execute(stmt)
    except Exception as exc:  # noqa: BLE001
        logger.warning("status.uptime.write_failed", extra={"error_type": type(exc).__name__})
        return {"status": "write_failed", "written": 0}

    return {
        "status": "completed",
        "ran_at": datetime.now(UTC).isoformat(),
        "written": len(payload),
        "components": [r["component"] for r in payload],
    }


_RANK = {"up": 0, "unknown": 1, "degraded": 2, "down": 3}


def _is_worse(new: str, existing: str) -> bool:
    return _RANK.get(new, 1) > _RANK.get(existing, 1)
