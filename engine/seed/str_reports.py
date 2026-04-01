def build_str_reports(count: int = 540) -> list[dict[str, object]]:
    reports: list[dict[str, object]] = []
    for index in range(count):
        reports.append(
            {
                "id": f"str-{index:05d}",
                "report_ref": f"STR-2604-{index:06d}",
                "subject_account": f"178143{index:07d}",
                "category": "fraud" if index % 2 == 0 else "money_laundering",
                "cross_bank_hit": index % 5 == 0,
            }
        )
    return reports
