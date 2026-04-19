"""Scheduled-processes surface.

Derives the visible schedule list from ``celery_app.conf.beat_schedule``
so the admin surface stays in sync with what beat will actually run.
Each entry is enriched with a human-readable description and the cron
expression equivalent of the celery ``crontab`` schedule object.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any

from celery.schedules import crontab
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


_SCHEDULE_METADATA: dict[str, dict[str, str]] = {
    "nightly_scan_all_orgs": {
        "description": (
            "Run the full scan pipeline across every bank's transactions and "
            "write alerts for anything above the scoring threshold."
        ),
    },
    "daily_digest_bfiu": {
        "description": (
            "Compose a morning digest for BFIU leadership summarising the "
            "previous day's alerts, new cross-bank matches, and STR throughput."
        ),
    },
    "weekly_compliance_report": {
        "description": (
            "Generate the weekly compliance scorecard and queue it for export "
            "+ dissemination."
        ),
    },
}


def _crontab_to_string(schedule: Any) -> str:
    """Best-effort cron string for a celery schedule object."""
    if isinstance(schedule, crontab):
        return " ".join(
            [
                str(schedule._orig_minute),
                str(schedule._orig_hour),
                str(schedule._orig_day_of_month),
                str(schedule._orig_month_of_year),
                str(schedule._orig_day_of_week),
            ]
        )
    return str(schedule)


def _build_entries() -> list[ScheduleEntry]:
    beat = celery_app.conf.beat_schedule or {}
    entries: list[ScheduleEntry] = []
    for name, payload in beat.items():
        meta = _SCHEDULE_METADATA.get(name, {})
        entries.append(
            ScheduleEntry(
                name=name,
                description=meta.get("description", ""),
                cron=_crontab_to_string(payload.get("schedule")),
                task=str(payload.get("task", "")),
                status="scheduled",
            )
        )
    # Surface any metadata-only entries that haven't been wired into beat yet
    # so operators can still see what's planned.
    for name, meta in _SCHEDULE_METADATA.items():
        if any(e.name == name for e in entries):
            continue
        entries.append(
            ScheduleEntry(
                name=name,
                description=meta.get("description", ""),
                cron="",
                task="",
                status="not_configured",
            )
        )
    return entries


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
        schedules=_build_entries(),
        workers=_probe_workers(),
        generated_at=datetime.utcnow().isoformat() + "Z",
    )
