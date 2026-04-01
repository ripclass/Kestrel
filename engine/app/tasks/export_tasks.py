from app.tasks.celery_app import celery_app


@celery_app.task(name="report.export")
def export_report(report_type: str) -> dict[str, str]:
    return {"report_type": report_type, "status": "queued"}
