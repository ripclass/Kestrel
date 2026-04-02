from celery import Celery

from app.config import get_settings

settings = get_settings()
celery_app = Celery("kestrel", broker=settings.redis_url, backend=settings.redis_url)
celery_app.conf.task_default_queue = "kestrel"


@celery_app.task(name="worker.ping")
def ping() -> dict[str, str]:
    return {"status": "ok", "queue": "kestrel"}
