from datetime import UTC, datetime


def build_report_export(report_type: str) -> dict[str, str]:
    return {
        "report_type": report_type,
        "status": "queued",
        "message": f"{report_type.replace('_', ' ').title()} export generation has been queued.",
        "generated_at": datetime.now(UTC).isoformat(),
    }
