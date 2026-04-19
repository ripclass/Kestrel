"""Scheduled export / compliance tasks.

``weekly_compliance_report`` emits a structured-log scorecard summarising
the past seven days of alert disposition, STR throughput, and case
closure. The structured payload is the seam where a real exporter
(PDF/XLSX → dissemination ledger) plugs in once recipient routing is
configured.
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

logger = logging.getLogger("kestrel.tasks.compliance")


async def _weekly_compliance_report(session: AsyncSession) -> dict[str, Any]:
    end = datetime.now(UTC)
    start = end - timedelta(days=7)

    alerts_by_status = (
        await session.execute(
            select(Alert.status, func.count(Alert.id))
            .where(Alert.created_at >= start)
            .group_by(Alert.status)
        )
    ).all()
    str_by_type = (
        await session.execute(
            select(STRReport.report_type, func.count(STRReport.id))
            .where(STRReport.created_at >= start)
            .group_by(STRReport.report_type)
        )
    ).all()
    cases_closed = (
        await session.execute(
            select(func.count(Case.id)).where(Case.closed_at >= start)
        )
    ).scalar_one()

    scorecard = {
        "window_start": start.isoformat(),
        "window_end": end.isoformat(),
        "alerts_by_status": {row[0]: int(row[1] or 0) for row in alerts_by_status},
        "str_by_type": {row[0]: int(row[1] or 0) for row in str_by_type},
        "cases_closed": int(cases_closed or 0),
    }
    logger.info("scheduled.compliance.weekly", extra=scorecard)
    return scorecard


@celery_app.task(name="app.tasks.export_tasks.weekly_compliance_report")
def weekly_compliance_report() -> dict[str, Any]:
    return run_async(_weekly_compliance_report)
