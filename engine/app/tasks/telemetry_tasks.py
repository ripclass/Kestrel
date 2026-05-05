"""Telemetry pingback (V3 phase 6.5).

Optional outbound pingback from on-prem deployments back to Kestrel HQ
for billing reconciliation. Defaults OFF in air-gapped mode — operators
opt in by setting ``KESTREL_TELEMETRY_ENABLED=true`` and a destination
URL via ``KESTREL_TELEMETRY_URL``.

Posted payload is minimal and aggregate — counts only, no PII, no
case/STR content. Designed to satisfy a procurement reviewer:

    {
      "deployment_mode": "onprem",
      "engine_version": "0.1.0",
      "timestamp": "2026-05-05T10:30:00Z",
      "metrics": {
        "organizations": 1,
        "transactions": 1284731,
        "alerts_open": 47,
        "strs_submitted_30d": 12,
        "ai_invocations_30d": 318
      }
    }

Failure is silent — a transient HQ outage shouldn't crash the customer's
container. The task logs at warning level so the operator can spot it.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime, timedelta
from typing import Any

import httpx
from sqlalchemy import func, select

from app.config import get_settings
from app.database import SessionLocal
from app.models.ai_outcome import AIOutcomeLog
from app.models.alert import Alert
from app.models.org import Organization
from app.models.str_report import STRReport
from app.models.transaction import Transaction
from app.tasks.celery_app import celery_app

logger = logging.getLogger("kestrel.tasks.telemetry")

REQUEST_TIMEOUT_SECONDS = 10.0


def _telemetry_enabled(settings) -> bool:
    return bool(settings.kestrel_telemetry_enabled and settings.kestrel_telemetry_url)


@celery_app.task(name="app.tasks.telemetry_tasks.pingback")
def pingback() -> dict[str, Any]:
    """Beat-driven entrypoint."""
    settings = get_settings()
    if not _telemetry_enabled(settings):
        logger.info("telemetry.disabled")
        return {"status": "disabled"}

    summary = asyncio.run(_run(settings))
    return summary


async def _run(settings) -> dict[str, Any]:
    metrics = await _gather_metrics()
    payload = {
        "deployment_mode": settings.kestrel_deployment_mode,
        "engine_version": settings.app_version,
        "timestamp": datetime.now(UTC).isoformat(),
        "metrics": metrics,
    }
    try:
        async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT_SECONDS) as client:
            response = await client.post(settings.kestrel_telemetry_url, json=payload)
            response.raise_for_status()
    except (httpx.RequestError, httpx.HTTPStatusError) as exc:
        logger.warning(
            "telemetry.pingback_failed",
            extra={"error_type": type(exc).__name__, "error": str(exc)[:200]},
        )
        return {"status": "failed", "error": type(exc).__name__, "metrics": metrics}
    logger.info("telemetry.pingback_ok", extra={"metrics": metrics})
    return {"status": "ok", "metrics": metrics}


async def _gather_metrics() -> dict[str, int]:
    """Pure aggregate counts — no PII, no business detail."""
    cutoff_30d = datetime.now(UTC) - timedelta(days=30)
    async with SessionLocal() as session:
        org_count = (await session.execute(select(func.count(Organization.id)))).scalar_one()
        txn_count = (await session.execute(select(func.count(Transaction.id)))).scalar_one()
        alerts_open = (
            await session.execute(
                select(func.count(Alert.id)).where(Alert.status.in_(("open", "reviewing", "escalated")))
            )
        ).scalar_one()
        strs_30d = (
            await session.execute(
                select(func.count(STRReport.id)).where(
                    STRReport.created_at >= cutoff_30d, STRReport.status == "submitted"
                )
            )
        ).scalar_one()
        ai_30d = (
            await session.execute(
                select(func.count(AIOutcomeLog.id)).where(AIOutcomeLog.created_at >= cutoff_30d)
            )
        ).scalar_one()
    return {
        "organizations": int(org_count or 0),
        "transactions": int(txn_count or 0),
        "alerts_open": int(alerts_open or 0),
        "strs_submitted_30d": int(strs_30d or 0),
        "ai_invocations_30d": int(ai_30d or 0),
    }


def build_payload_for_test(settings, metrics: dict[str, int]) -> dict[str, Any]:
    """Pure helper exposed for unit tests — no DB IO, no HTTP."""
    return {
        "deployment_mode": settings.kestrel_deployment_mode,
        "engine_version": settings.app_version,
        "timestamp": datetime.now(UTC).isoformat(),
        "metrics": dict(metrics),
    }
