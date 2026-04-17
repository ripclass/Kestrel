"""Scheduled-processes surface.

v1 returns the declared schedule operators *plan* to run, cross-referenced
with any live Celery workers. No beat schedule is wired into the engine
yet — this module is the visible seam for operators to see what's
configured vs. actually running, and for ops teams to know what to
automate next.
"""
from datetime import datetime

from pydantic import BaseModel, Field

from app.tasks.celery_app import celery_app


class ScheduleEntry(BaseModel):
    name: str
    description: str
    cron: str
    task: str
    status: str
    last_run_at: str | None = None
    next_run_at: str | None = None


class ScheduleWorker(BaseModel):
    hostname: str
    alive: bool


class ScheduleListResponse(BaseModel):
    schedules: list[ScheduleEntry] = Field(default_factory=list)
    workers: list[ScheduleWorker] = Field(default_factory=list)
    generated_at: str


_DECLARED_SCHEDULES: list[ScheduleEntry] = [
    ScheduleEntry(
        name="nightly_scan_all_orgs",
        description="Run the full scan pipeline across every bank's transactions and write alerts for anything above the scoring threshold.",
        cron="0 2 * * *",
        task="app.tasks.scan_tasks.run_all_orgs",
        status="not_configured",
    ),
    ScheduleEntry(
        name="daily_digest_bfiu",
        description="Compose a morning digest for BFIU leadership summarising the previous day's alerts, new cross-bank matches, and STR throughput.",
        cron="30 6 * * *",
        task="app.tasks.str_tasks.daily_digest",
        status="not_configured",
    ),
    ScheduleEntry(
        name="weekly_compliance_report",
        description="Generate the weekly compliance scorecard and queue it for export + dissemination.",
        cron="0 5 * * 1",
        task="app.tasks.export_tasks.weekly_compliance_report",
        status="not_configured",
    ),
]


def _probe_workers() -> list[ScheduleWorker]:
    try:
        inspector = celery_app.control.inspect(timeout=1.5)
        ping = inspector.ping() or {}
    except Exception:
        return []
    return [
        ScheduleWorker(
            hostname=hostname,
            alive=bool(payload and payload.get("ok") == "pong"),
        )
        for hostname, payload in ping.items()
    ]


def build_schedule_list() -> ScheduleListResponse:
    return ScheduleListResponse(
        schedules=list(_DECLARED_SCHEDULES),
        workers=_probe_workers(),
        generated_at=datetime.utcnow().isoformat() + "Z",
    )
