from celery import Celery
from celery.schedules import crontab

from app.config import get_settings

settings = get_settings()
celery_app = Celery(
    "kestrel",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=[
        "app.tasks.scan_tasks",
        "app.tasks.str_tasks",
        "app.tasks.export_tasks",
        "app.tasks.demo_seed_tasks",
        "app.tasks.screening_tasks",
        "app.tasks.kyc_tasks",
        "app.tasks.status_tasks",
        "app.tasks.demo_refresh_tasks",
        "app.tasks.sovereign_health_tasks",
        "app.tasks.telemetry_tasks",
    ],
)
celery_app.conf.task_default_queue = "kestrel"
celery_app.conf.timezone = "Asia/Dhaka"
celery_app.conf.enable_utc = False

celery_app.conf.beat_schedule = {
    "nightly_scan_all_orgs": {
        "task": "app.tasks.scan_tasks.run_all_orgs",
        "schedule": crontab(minute=0, hour=2),
        "options": {"expires": 60 * 60 * 6},
    },
    "daily_digest_bfiu": {
        "task": "app.tasks.str_tasks.daily_digest",
        "schedule": crontab(minute=30, hour=6),
        "options": {"expires": 60 * 60 * 6},
    },
    "weekly_compliance_report": {
        "task": "app.tasks.export_tasks.weekly_compliance_report",
        "schedule": crontab(minute=0, hour=5, day_of_week=1),
        "options": {"expires": 60 * 60 * 24},
    },
    "demo_bank_seed_pending": {
        "task": "app.tasks.demo_seed_tasks.apply_pending",
        "schedule": crontab(minute="*/10"),
        "options": {"expires": 60 * 30},
    },
    "watchlist_refresh_daily": {
        "task": "app.tasks.screening_tasks.refresh_all",
        "schedule": crontab(minute=30, hour=2),
        "options": {"expires": 60 * 60 * 6},
    },
    "kyc_rescreen_active": {
        "task": "app.tasks.kyc_tasks.rescreen_active_customers",
        "schedule": crontab(minute=0, hour=3),
        "options": {"expires": 60 * 60 * 6},
    },
    "uptime_ping_5min": {
        "task": "app.tasks.status_tasks.record_uptime_ping",
        "schedule": crontab(minute="*/5"),
        "options": {"expires": 60 * 5},
    },
    "weekly_demo_refresh": {
        "task": "app.tasks.demo_refresh_tasks.weekly_demo_refresh",
        "schedule": crontab(minute=0, hour=4, day_of_week=1),
        "options": {"expires": 60 * 60 * 12},
    },
    "sovereign_health_check_30min": {
        "task": "app.tasks.sovereign_health_tasks.check",
        "schedule": crontab(minute="*/30"),
        "options": {"expires": 60 * 25},
    },
    "telemetry_pingback_daily": {
        "task": "app.tasks.telemetry_tasks.pingback",
        "schedule": crontab(minute=0, hour=1),
        "options": {"expires": 60 * 60 * 6},
    },
}


@celery_app.task(name="worker.ping")
def ping() -> dict[str, str]:
    return {"status": "ok", "queue": "kestrel"}
