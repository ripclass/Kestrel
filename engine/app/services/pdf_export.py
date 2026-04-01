def build_report_export(report_type: str) -> dict[str, str]:
    return {
        "report_type": report_type,
        "status": "queued",
        "message": "PDF export generation has been queued.",
    }
