"""Scheduled scan tasks.

``run_all_orgs`` is the nightly scan entry point. It creates a system
``DetectionRun`` attributed to the regulator org and executes
``run_scan_pipeline`` across every bank's transactions.
"""
from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.pipeline import run_scan_pipeline
from app.models.detection_run import DetectionRun
from app.models.org import Organization
from app.tasks._runtime import run_async
from app.tasks.celery_app import celery_app

logger = logging.getLogger("kestrel.tasks.scan")


async def _run_all_orgs(session: AsyncSession) -> dict[str, Any]:
    regulator_q = await session.execute(
        select(Organization).where(Organization.org_type == "regulator").limit(1)
    )
    regulator = regulator_q.scalar_one_or_none()
    if regulator is None:
        logger.warning("scheduled.scan.skip", extra={"reason": "no_regulator_org"})
        return {"status": "skipped", "reason": "no_regulator_org"}

    now = datetime.now(UTC)
    run = DetectionRun(
        org_id=regulator.id,
        run_type="scheduled",
        status="pending",
        file_name=f"scheduled-scan-{now:%Y%m%d-%H%M%S}",
        file_url=None,
        tx_count=0,
        accounts_scanned=0,
        alerts_generated=0,
        results={"summary": "queued", "selected_rules": [], "flagged_accounts": []},
        triggered_by=None,
        started_at=None,
        completed_at=None,
        error=None,
    )
    session.add(run)
    await session.flush()

    logger.info(
        "scheduled.scan.start",
        extra={"run_id": str(run.id), "regulator_org_id": str(regulator.id)},
    )
    try:
        result = await run_scan_pipeline(
            session,
            run_id=run.id,
            org_id=regulator.id,
            scope_org_ids=None,
        )
        await session.commit()
        return {
            "status": "completed",
            "run_id": str(run.id),
            "alerts": len(result.get("alerts", [])),
            "flagged": len(result.get("flagged_accounts", [])),
            "matches": len(result.get("matches", [])),
        }
    except Exception as exc:
        run.status = "failed"
        run.error = str(exc)
        run.completed_at = datetime.now(UTC)
        await session.commit()
        logger.exception(
            "scheduled.scan.error", extra={"run_id": str(run.id), "error": str(exc)}
        )
        raise


@celery_app.task(name="app.tasks.scan_tasks.run_all_orgs")
def run_all_orgs() -> dict[str, Any]:
    return run_async(_run_all_orgs)
