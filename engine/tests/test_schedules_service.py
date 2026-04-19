"""Tests for the scheduled-processes admin surface."""
from __future__ import annotations

from app.services import schedules
from app.tasks.celery_app import celery_app


def test_beat_schedule_declares_three_jobs() -> None:
    beat = celery_app.conf.beat_schedule or {}
    assert set(beat) == {
        "nightly_scan_all_orgs",
        "daily_digest_bfiu",
        "weekly_compliance_report",
    }


def test_beat_schedule_targets_real_task_names() -> None:
    expected = {
        "nightly_scan_all_orgs": "app.tasks.scan_tasks.run_all_orgs",
        "daily_digest_bfiu": "app.tasks.str_tasks.daily_digest",
        "weekly_compliance_report": "app.tasks.export_tasks.weekly_compliance_report",
    }
    beat = celery_app.conf.beat_schedule
    for entry_name, task_path in expected.items():
        assert beat[entry_name]["task"] == task_path


def test_build_entries_marks_wired_jobs_scheduled() -> None:
    entries = {entry.name: entry for entry in schedules._build_entries()}
    for name in (
        "nightly_scan_all_orgs",
        "daily_digest_bfiu",
        "weekly_compliance_report",
    ):
        assert entries[name].status == "scheduled"
        assert entries[name].cron, f"cron string missing for {name}"
        assert entries[name].task, f"task path missing for {name}"


def test_build_entries_includes_metadata_for_each_job() -> None:
    entries = {entry.name: entry for entry in schedules._build_entries()}
    for entry in entries.values():
        if entry.status == "scheduled":
            assert entry.description, (
                f"description missing for scheduled job {entry.name}"
            )


def test_unwired_metadata_only_jobs_are_not_configured() -> None:
    """If a metadata key has no beat entry, surface it as not_configured."""
    original = celery_app.conf.beat_schedule
    try:
        celery_app.conf.beat_schedule = {
            k: v for k, v in original.items() if k != "weekly_compliance_report"
        }
        entries = {entry.name: entry for entry in schedules._build_entries()}
        assert entries["weekly_compliance_report"].status == "not_configured"
        assert entries["nightly_scan_all_orgs"].status == "scheduled"
    finally:
        celery_app.conf.beat_schedule = original


def test_celery_timezone_is_dhaka() -> None:
    assert celery_app.conf.timezone == "Asia/Dhaka"
    assert celery_app.conf.enable_utc is False


def test_tasks_modules_are_included() -> None:
    """Beat needs the task modules in `include` so they import on startup."""
    include = list(celery_app.conf.include or [])
    for module in (
        "app.tasks.scan_tasks",
        "app.tasks.str_tasks",
        "app.tasks.export_tasks",
    ):
        assert module in include


def test_registered_tasks_match_beat_targets() -> None:
    """Every beat target must resolve to a registered Celery task.

    Celery's `include` only fires inside the worker. Importing the
    task modules here mirrors what `celery -A app.tasks.celery_app worker`
    does on startup, so a typo in the beat task path fails this test
    rather than at 02:00 Dhaka time.
    """
    import importlib

    for module in (
        "app.tasks.scan_tasks",
        "app.tasks.str_tasks",
        "app.tasks.export_tasks",
    ):
        importlib.import_module(module)

    beat = celery_app.conf.beat_schedule or {}
    task_names = set(celery_app.tasks.keys())
    for entry in beat.values():
        assert entry["task"] in task_names, (
            f"{entry['task']} not registered. Known: {sorted(task_names)}"
        )
