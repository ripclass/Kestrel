"""Scheduled STR / digest tasks.

``daily_digest`` emits a structured-log heartbeat with yesterday's
volume of alerts, STRs, and cases. This is the morning digest input
that operators can grep for, and the seam where an email/Slack
delivery layer plugs in once a notification provider is wired.
"""
from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.alert import Alert
from app.models.case import Case
from app.models.str_report import STRReport
from app.tasks._runtime import run_async
from app.tasks.celery_app import celery_app

logger = logging.getLogger("kestrel.tasks.digest")


async def _daily_digest(session: AsyncSession) -> dict[str, Any]:
    end = datetime.now(UTC)
    start = end - timedelta(hours=24)

    alerts_total = (
        await session.execute(
            select(func.count(Alert.id)).where(Alert.created_at >= start)
        )
    ).scalar_one()
    cross_bank_alerts = (
        await session.execute(
            select(func.count(Alert.id)).where(
                Alert.created_at >= start,
                Alert.source_type == "cross_bank",
            )
        )
    ).scalar_one()
    str_total = (
        await session.execute(
            select(func.count(STRReport.id)).where(STRReport.created_at >= start)
        )
    ).scalar_one()
    cases_opened = (
        await session.execute(
            select(func.count(Case.id)).where(Case.created_at >= start)
        )
    ).scalar_one()

    digest = {
        "window_start": start.isoformat(),
        "window_end": end.isoformat(),
        "alerts_total": int(alerts_total or 0),
        "alerts_cross_bank": int(cross_bank_alerts or 0),
        "str_reports_filed": int(str_total or 0),
        "cases_opened": int(cases_opened or 0),
    }
    logger.info("scheduled.digest.daily", extra=digest)
    return digest


@celery_app.task(name="app.tasks.str_tasks.daily_digest")
def daily_digest() -> dict[str, Any]:
    return run_async(_daily_digest)
