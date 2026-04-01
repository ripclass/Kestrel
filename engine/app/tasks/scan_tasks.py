from app.tasks.celery_app import celery_app


@celery_app.task(name="scan.run")
def run_scan(run_id: str) -> dict[str, str]:
    return {"run_id": run_id, "status": "completed"}
