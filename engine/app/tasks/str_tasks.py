from app.tasks.celery_app import celery_app


@celery_app.task(name="str.enrich")
def enrich_str(report_id: str) -> dict[str, str]:
    return {"report_id": report_id, "status": "queued"}
