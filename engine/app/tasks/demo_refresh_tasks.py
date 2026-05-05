"""Weekly demo data refresher (V2 phase 6.3).

Shifts ``transactions.posted_at`` and a handful of other timestamp
fields forward by ~7 days so every demo always shows ``activity in the
last 30 days``. Without this, the synthetic dataset's data appears
older the longer the prod environment runs without new ingestion.

Idempotent: tracks the last-refresh timestamp under
``settings.last_demo_refresh_at`` on the regulator org and skips the
shift if the last refresh was within 6 days.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import select, text, update

from app.database import SessionLocal
from app.models.org import Organization
from app.tasks.celery_app import celery_app

logger = logging.getLogger("kestrel.tasks.demo_refresh")

_REFRESH_WINDOW_DAYS = 6
_SHIFT_DAYS = 7


@celery_app.task(name="app.tasks.demo_refresh_tasks.weekly_demo_refresh")
def weekly_demo_refresh() -> dict[str, Any]:
    summary = asyncio.run(_run())
    if summary.get("shifted_rows", 0) > 0:
        logger.info("demo_refresh.shifted", extra={"summary": summary})
    elif summary.get("skipped"):
        logger.info("demo_refresh.skipped", extra={"summary": summary})
    return summary


async def _run() -> dict[str, Any]:
    async with SessionLocal() as session:
        regulator = await _find_regulator(session)
        if regulator is None:
            return {"status": "no_regulator", "shifted_rows": 0}

        last = (regulator.settings or {}).get("last_demo_refresh_at")
        last_at = _parse_iso(last)
        now = datetime.now(UTC)
        if last_at and (now - last_at) < timedelta(days=_REFRESH_WINDOW_DAYS):
            return {
                "status": "skipped",
                "skipped": True,
                "last_refresh_at": last_at.isoformat(),
                "shifted_rows": 0,
            }

        async with session.begin():
            shifted_txns = await session.execute(
                text(
                    """
                    UPDATE transactions
                       SET posted_at = posted_at + interval ':days days'
                     WHERE org_id IN (
                       SELECT id FROM organizations WHERE org_type = 'bank'
                     )
                       AND posted_at < now() - interval '7 days'
                       AND posted_at > now() - interval '400 days'
                    """.replace(":days days", f"{_SHIFT_DAYS} days")
                )
            )
            shifted_alerts = await session.execute(
                text(
                    f"""
                    UPDATE alerts
                       SET created_at = created_at + interval '{_SHIFT_DAYS} days'
                     WHERE created_at < now() - interval '7 days'
                       AND created_at > now() - interval '400 days'
                    """
                )
            )
            new_settings = dict(regulator.settings or {})
            new_settings["last_demo_refresh_at"] = now.isoformat()
            await session.execute(
                update(Organization)
                .where(Organization.id == regulator.id)
                .values(settings=new_settings)
            )

    return {
        "status": "completed",
        "ran_at": datetime.now(UTC).isoformat(),
        "shifted_rows": int(shifted_txns.rowcount or 0) + int(shifted_alerts.rowcount or 0),
        "shifted_transactions": int(shifted_txns.rowcount or 0),
        "shifted_alerts": int(shifted_alerts.rowcount or 0),
    }


async def _find_regulator(session) -> Organization | None:
    result = await session.execute(
        select(Organization).where(Organization.org_type == "regulator").limit(1)
    )
    return result.scalar_one_or_none()


def _parse_iso(value: Any) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed
