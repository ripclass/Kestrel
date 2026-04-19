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
}


@celery_app.task(name="worker.ping")
def ping() -> dict[str, str]:
    return {"status": "ok", "queue": "kestrel"}
