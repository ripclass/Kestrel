from datetime import UTC, datetime

from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.case import Case
from app.models.ctr import CashTransactionReport
from app.models.dissemination import Dissemination
from app.models.org import Organization
from app.models.str_report import STRReport
from app.schemas.statistics import (
    CaseOutcomeBreakdown,
    CtrVolumeByMonth,
    DisseminationsByAgency,
    OperationalStatisticsResponse,
    ReportsByOrg,
    ReportsByTypeByMonth,
    TimeToReviewAverage,
)


def _iso(value: datetime | None) -> str:
    if value is None:
        return datetime.now(UTC).isoformat()
    return value.astimezone(UTC).isoformat()


async def build_operational_statistics(
    session: AsyncSession,
) -> OperationalStatisticsResponse:
    # --- reports_by_type_by_month (all STR/SAR/CTR variants stored in str_reports)
    month_expr = func.to_char(
        func.coalesce(STRReport.reported_at, STRReport.created_at),
        "YYYY-MM",
    ).label("month")
    stmt = (
        select(
            month_expr,
            STRReport.report_type.label("report_type"),
            func.count().label("count"),
        )
        .group_by(month_expr, STRReport.report_type)
        .order_by(month_expr.desc(), STRReport.report_type.asc())
        .limit(200)
    )
    result = await session.execute(stmt)
    reports_by_type_by_month = [
        ReportsByTypeByMonth(
            month=row.month or "",
            report_type=row.report_type or "str",
            count=int(row.count or 0),
        )
        for row in result.all()
    ]

    # --- reports_by_org (top reporting organizations)
    stmt = (
        select(
            Organization.name.label("org_name"),
            func.count(STRReport.id).label("count"),
        )
        .join(Organization, Organization.id == STRReport.org_id)
        .group_by(Organization.name)
        .order_by(desc("count"))
        .limit(20)
    )
    result = await session.execute(stmt)
    reports_by_org = [
        ReportsByOrg(org_name=row.org_name, count=int(row.count or 0))
        for row in result.all()
    ]

    # --- CTR volume by month
    ctr_month_expr = func.to_char(CashTransactionReport.transaction_date, "YYYY-MM").label("month")
    stmt = (
        select(
            ctr_month_expr,
            func.count().label("count"),
            func.coalesce(func.sum(CashTransactionReport.amount), 0).label("total_amount"),
        )
        .group_by(ctr_month_expr)
        .order_by(ctr_month_expr.desc())
        .limit(24)
    )
    result = await session.execute(stmt)
    ctr_volume_by_month = [
        CtrVolumeByMonth(
            month=row.month or "",
            count=int(row.count or 0),
            total_amount=float(row.total_amount or 0.0),
        )
        for row in result.all()
    ]

    # --- Disseminations by agency
    stmt = (
        select(
            Dissemination.recipient_agency.label("recipient_agency"),
            Dissemination.recipient_type.label("recipient_type"),
            func.count().label("count"),
        )
        .group_by(Dissemination.recipient_agency, Dissemination.recipient_type)
        .order_by(desc("count"))
        .limit(50)
    )
    result = await session.execute(stmt)
    disseminations_by_agency = [
        DisseminationsByAgency(
            recipient_agency=row.recipient_agency,
            recipient_type=row.recipient_type,
            count=int(row.count or 0),
        )
        for row in result.all()
    ]

    # --- Case outcomes (by status)
    stmt = (
        select(Case.status.label("status"), func.count().label("count"))
        .group_by(Case.status)
        .order_by(desc("count"))
    )
    result = await session.execute(stmt)
    case_outcomes = [
        CaseOutcomeBreakdown(status=row.status or "unknown", count=int(row.count or 0))
        for row in result.all()
    ]

    # --- Average time-to-review (submitted → non-submitted transition)
    # We don't have a dedicated reviewed_at column, so we approximate using
    # updated_at - reported_at for status != 'submitted' and != 'draft'.
    hours_expr = func.avg(
        func.extract("epoch", STRReport.updated_at - STRReport.reported_at) / 3600.0
    ).label("avg_hours")
    count_expr = func.count().label("sample_size")
    stmt = (
        select(STRReport.report_type.label("report_type"), hours_expr, count_expr)
        .where(
            STRReport.status.notin_(["draft", "submitted"]),
            STRReport.reported_at.is_not(None),
            STRReport.updated_at.is_not(None),
        )
        .group_by(STRReport.report_type)
        .order_by(STRReport.report_type.asc())
    )
    result = await session.execute(stmt)
    time_to_review = [
        TimeToReviewAverage(
            report_type=row.report_type or "str",
            average_hours=float(row.avg_hours or 0.0),
            sample_size=int(row.sample_size or 0),
        )
        for row in result.all()
    ]

    return OperationalStatisticsResponse(
        reports_by_type_by_month=reports_by_type_by_month,
        reports_by_org=reports_by_org,
        ctr_volume_by_month=ctr_volume_by_month,
        disseminations_by_agency=disseminations_by_agency,
        case_outcomes=case_outcomes,
        time_to_review=time_to_review,
        generated_at=_iso(None),
    )
