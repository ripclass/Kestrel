from __future__ import annotations

from collections import Counter, defaultdict
from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import AuthenticatedUser
from app.models.alert import Alert
from app.models.case import Case
from app.models.detection_run import DetectionRun
from app.models.entity import Entity
from app.models.match import Match
from app.models.org import Organization
from app.models.str_report import STRReport
from app.schemas.overview import KpiStat, OverviewResponse
from app.schemas.report import (
    ComplianceScore,
    ComplianceScorecard,
    NationalReportResponse,
    ThreatMapRow,
    TrendPoint,
    TrendSeriesResponse,
)

_OPEN_ALERT_STATUSES = {"open", "reviewing", "escalated"}
_ACTIVE_CASE_STATUSES = {"open", "investigating", "escalated", "pending_action"}
_BANKLIKE_ORG_TYPES = {"bank", "mfs", "nbfi"}


def _as_float(value: Decimal | float | int | None) -> float:
    if value is None:
        return 0.0
    return float(value)


def _as_int(value: object) -> int:
    if value is None:
        return 0
    return int(value)


def _as_uuid(value: str | UUID | None) -> UUID | None:
    if value is None or value == "":
        return None
    if isinstance(value, UUID):
        return value
    try:
        return UUID(str(value))
    except ValueError:
        return None


def _month_bucket(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.astimezone(UTC).strftime("%b")


def _recent_delta(count: int, previous: int, *, neutral_label: str) -> str:
    delta = count - previous
    if delta > 0:
        return f"+{delta} recent"
    if delta < 0:
        return f"{delta} recent"
    return neutral_label


def _threat_level(signal_count: int, total_exposure: float) -> str:
    if signal_count >= 5 or total_exposure >= 10_000_000:
        return "Very high"
    if signal_count >= 3 or total_exposure >= 5_000_000:
        return "High"
    if signal_count >= 1 or total_exposure > 0:
        return "Elevated"
    return "Monitoring"


def _score_org_compliance(
    *,
    report_count: int,
    open_alert_count: int,
    active_case_count: int,
    cross_bank_hit_count: int,
    detection_run_count: int,
) -> ComplianceScore:
    submission_timeliness = min(100, 55 + report_count * 8 + detection_run_count * 4)
    alert_conversion = min(
        100,
        35 + min(report_count, open_alert_count) * 10 + active_case_count * 12,
    )
    peer_coverage = min(100, 30 + cross_bank_hit_count * 15 + detection_run_count * 5)
    score = round(
        submission_timeliness * 0.4
        + alert_conversion * 0.35
        + peer_coverage * 0.25,
    )
    return ComplianceScore(
        org_name="",
        submission_timeliness=submission_timeliness,
        alert_conversion=alert_conversion,
        peer_coverage=peer_coverage,
        score=score,
    )


async def _load_reporting_context(session: AsyncSession) -> dict[str, list[object]]:
    organizations = list((await session.execute(select(Organization))).scalars().all())
    reports = list((await session.execute(select(STRReport))).scalars().all())
    alerts = list((await session.execute(select(Alert))).scalars().all())
    cases = list((await session.execute(select(Case))).scalars().all())
    matches = list((await session.execute(select(Match))).scalars().all())
    entities = list((await session.execute(select(Entity))).scalars().all())
    runs = list((await session.execute(select(DetectionRun))).scalars().all())
    return {
        "organizations": organizations,
        "reports": reports,
        "alerts": alerts,
        "cases": cases,
        "matches": matches,
        "entities": entities,
        "runs": runs,
    }


def _build_compliance_rows(
    *,
    organizations: list[Organization],
    reports: list[STRReport],
    alerts: list[Alert],
    cases: list[Case],
    runs: list[DetectionRun],
) -> list[ComplianceScore]:
    report_counter = Counter(str(report.org_id) for report in reports if report.org_id)
    cross_bank_counter = Counter(str(report.org_id) for report in reports if report.org_id and report.cross_bank_hit)
    alert_counter = Counter(
        str(alert.org_id)
        for alert in alerts
        if alert.org_id and alert.status in _OPEN_ALERT_STATUSES
    )
    case_counter = Counter(
        str(linked_case.org_id)
        for linked_case in cases
        if linked_case.org_id and linked_case.status in _ACTIVE_CASE_STATUSES
    )
    run_counter = Counter(str(run.org_id) for run in runs if run.org_id)

    rows: list[ComplianceScore] = []
    for organization in organizations:
        if organization.org_type not in _BANKLIKE_ORG_TYPES:
            continue
        org_key = str(organization.id)
        score = _score_org_compliance(
            report_count=report_counter[org_key],
            open_alert_count=alert_counter[org_key],
            active_case_count=case_counter[org_key],
            cross_bank_hit_count=cross_bank_counter[org_key],
            detection_run_count=run_counter[org_key],
        )
        score.org_name = organization.name
        rows.append(score)

    return sorted(rows, key=lambda item: item.score, reverse=True)


def _build_threat_map_rows(reports: list[STRReport], alerts: list[Alert]) -> list[ThreatMapRow]:
    channel_signals: dict[str, dict[str, object]] = defaultdict(
        lambda: {
            "report_count": 0,
            "alert_count": 0,
            "exposure": 0.0,
            "categories": Counter(),
        }
    )

    for report in reports:
        channels = {channel for channel in [report.primary_channel, *(report.channels or [])] if channel}
        if not channels:
            channels = {"Unknown"}
        for channel in channels:
            signal = channel_signals[channel]
            signal["report_count"] = _as_int(signal["report_count"]) + 1
            signal["exposure"] = _as_float(signal["exposure"]) + _as_float(report.total_amount)
            categories = signal["categories"]
            if isinstance(categories, Counter):
                categories[report.category] += 1

    for alert in alerts:
        description = (alert.description or "").lower()
        inferred_channel = None
        for channel in ("MFS", "RTGS", "NPSB", "BEFTN", "Cash", "Card"):
            if channel.lower() in description:
                inferred_channel = channel
                break
        if not inferred_channel:
            continue
        signal = channel_signals[inferred_channel]
        signal["alert_count"] = _as_int(signal["alert_count"]) + 1

    rows: list[ThreatMapRow] = []
    for channel, signal in channel_signals.items():
        report_count = _as_int(signal["report_count"])
        alert_count = _as_int(signal["alert_count"])
        exposure = _as_float(signal["exposure"])
        categories = signal["categories"]
        primary_category = "mixed activity"
        if isinstance(categories, Counter) and categories:
            primary_category = categories.most_common(1)[0][0].replace("_", " ")
        total_signals = report_count + alert_count
        rows.append(
            ThreatMapRow(
                channel=channel,
                level=_threat_level(total_signals, exposure),
                detail=(
                    f"{total_signals} live signals, {report_count} STR references, "
                    f"dominant typology {primary_category}."
                ),
                signal_count=total_signals,
                total_exposure=round(exposure, 2),
            )
        )

    return sorted(
        rows,
        key=lambda item: (item.signal_count, item.total_exposure),
        reverse=True,
    )[:4]


def _build_trend_points(
    *,
    alerts: list[Alert],
    reports: list[STRReport],
    cases: list[Case],
    runs: list[DetectionRun],
) -> list[TrendPoint]:
    month_order: list[str] = []
    series: dict[str, dict[str, int]] = {}

    def ensure_month(month: str | None) -> None:
        if not month:
            return
        if month not in series:
            series[month] = {"alerts": 0, "str_reports": 0, "cases": 0, "scans": 0}
            month_order.append(month)

    for alert in alerts:
        month = _month_bucket(alert.created_at)
        ensure_month(month)
        if month:
            series[month]["alerts"] += 1

    for report in reports:
        month = _month_bucket(report.reported_at or report.created_at)
        ensure_month(month)
        if month:
            series[month]["str_reports"] += 1

    for linked_case in cases:
        month = _month_bucket(linked_case.created_at)
        ensure_month(month)
        if month:
            series[month]["cases"] += 1

    for run in runs:
        month = _month_bucket(run.created_at or run.started_at)
        ensure_month(month)
        if month:
            series[month]["scans"] += 1

    if not month_order:
        current_month = datetime.now(UTC).strftime("%b")
        month_order = [current_month]
        series[current_month] = {"alerts": 0, "str_reports": 0, "cases": 0, "scans": 0}

    return [
        TrendPoint(month=month, **series[month])
        for month in month_order
    ]


def _build_operational_notes(
    *,
    reports: list[STRReport],
    matches: list[Match],
    alerts: list[Alert],
    runs: list[DetectionRun],
    user: AuthenticatedUser,
) -> list[str]:
    if user.persona == "bank_camlco":
        latest_run = max(
            runs,
            key=lambda item: item.created_at or item.started_at or datetime.min.replace(tzinfo=UTC),
            default=None,
        )
        latest_flagged = 0
        if latest_run and isinstance(latest_run.results, dict):
            latest_flagged = len((latest_run.results or {}).get("flagged_accounts", []))
        return [
            f"{sum(1 for report in reports if report.cross_bank_hit)} submitted STRs already carry cross-bank hits.",
            f"Latest detection run produced {latest_flagged} flagged account candidate{'s' if latest_flagged != 1 else ''}.",
            f"{len(matches)} shared-intelligence overlap cluster{'s' if len(matches) != 1 else ''} are visible to this bank.",
        ]

    if user.persona == "bfiu_director":
        category_counter = Counter(report.category for report in reports)
        top_categories = [
            f"{category.replace('_', ' ')} leads with {count} STR{'s' if count != 1 else ''}."
            for category, count in category_counter.most_common(3)
        ]
        if top_categories:
            return top_categories
        return ["Live typology summaries will appear here as reports accumulate."]

    return [
        f"{sum(1 for alert in alerts if alert.status in _OPEN_ALERT_STATUSES)} alerts remain in active triage.",
        f"{len(matches)} cross-bank match cluster{'s' if len(matches) != 1 else ''} are ready for validation.",
        f"{sum(1 for report in reports if report.cross_bank_hit)} STRs already include shared-intelligence enrichment.",
    ]


def _build_overview_stats(
    *,
    user: AuthenticatedUser,
    reports: list[STRReport],
    alerts: list[Alert],
    cases: list[Case],
    matches: list[Match],
    runs: list[DetectionRun],
    compliance_rows: list[ComplianceScore],
    entities: list[Entity],
) -> tuple[str, list[KpiStat], list[str]]:
    open_alerts = [alert for alert in alerts if alert.status in _OPEN_ALERT_STATUSES]
    critical_alerts = [alert for alert in open_alerts if _as_int(alert.risk_score) >= 90]
    active_cases = [linked_case for linked_case in cases if linked_case.status in _ACTIVE_CASE_STATUSES]
    recent_matches = [match for match in matches if match.status not in {"false_positive"}]

    operational = _build_operational_notes(
        reports=reports,
        matches=matches,
        alerts=alerts,
        runs=runs,
        user=user,
    )

    if user.persona == "bfiu_director":
        lagging_banks = [row for row in compliance_rows if row.score < 70]
        category_count = len({report.category for report in reports if report.category})
        stats = [
            KpiStat(
                label="High-severity networks",
                value=str(sum(1 for match in recent_matches if (match.severity or "").lower() in {"critical", "high"})),
                delta=_recent_delta(len(recent_matches), max(0, len(recent_matches) - 1), neutral_label="steady"),
                detail="cross-bank clusters with regulator visibility",
            ),
            KpiStat(
                label="Peer banks lagging",
                value=str(len(lagging_banks)),
                delta=f"{len(compliance_rows)} scored",
                detail="institutions below the live readiness baseline",
            ),
            KpiStat(
                label="Evaluation-ready packs",
                value=str(category_count),
                delta=f"{len(_build_threat_map_rows(reports, alerts))} channel brief{'s' if len(_build_threat_map_rows(reports, alerts)) != 1 else ''}",
                detail="typology and compliance narratives assembled from live data",
            ),
        ]
        return (
            "National threat posture across banks, channels, and typologies.",
            stats,
            operational,
        )

    if user.persona == "bank_camlco":
        latest_run = max(
            runs,
            key=lambda item: item.created_at or item.started_at or datetime.min.replace(tzinfo=UTC),
            default=None,
        )
        latest_flagged_accounts = 0
        previous_flagged_accounts = 0
        sorted_runs = sorted(
            runs,
            key=lambda item: item.created_at or item.started_at or datetime.min.replace(tzinfo=UTC),
            reverse=True,
        )
        if latest_run and isinstance(latest_run.results, dict):
            latest_flagged_accounts = len((latest_run.results or {}).get("flagged_accounts", []))
        if len(sorted_runs) > 1 and isinstance(sorted_runs[1].results, dict):
            previous_flagged_accounts = len((sorted_runs[1].results or {}).get("flagged_accounts", []))

        relevant_entity_count = sum(
            1
            for entity in entities
            if _as_int(entity.risk_score) >= 70 and user.org_id in {str(org_id) for org_id in entity.reporting_orgs or []}
        )
        own_score = compliance_rows[0].score if compliance_rows else 0
        stats = [
            KpiStat(
                label="Accounts above threshold",
                value=str(latest_flagged_accounts),
                delta=_recent_delta(latest_flagged_accounts, previous_flagged_accounts, neutral_label="first live run"),
                detail="ready for manual review from the latest persisted scan",
            ),
            KpiStat(
                label="Peer-network signals",
                value=str(relevant_entity_count),
                delta=f"{len(matches)} shared overlaps",
                detail="shared entities touching this bank's reporting perimeter",
            ),
            KpiStat(
                label="Submission posture",
                value=f"{own_score}/100",
                delta=f"{sum(1 for report in reports if report.cross_bank_hit)} cross-bank hits",
                detail="live compliance score from submitted reports, alerts, and scan activity",
            ),
        ]
        return (
            "Your bank posture with peer-network intelligence overlaid.",
            stats,
            operational,
        )

    stats = [
        KpiStat(
            label="Open priority alerts",
            value=str(len(open_alerts)),
            delta=f"{len(critical_alerts)} critical",
            detail="triage currently visible in the active queue",
        ),
        KpiStat(
            label="Cross-bank matches",
            value=str(len(recent_matches)),
            delta=_recent_delta(len(recent_matches), max(0, len(recent_matches) - 1), neutral_label="steady"),
            detail="shared-identifier overlaps ready for validation",
        ),
        KpiStat(
            label="Cases in motion",
            value=str(len(active_cases)),
            delta=f"{sum(1 for linked_case in active_cases if linked_case.status == 'escalated')} escalated",
            detail="shared evidence workspaces with active analyst handling",
        ),
    ]
    return (
        "Unified triage for entity overlaps, alerts, and active investigations.",
        stats,
        operational,
    )


async def build_overview(session: AsyncSession, *, user: AuthenticatedUser) -> OverviewResponse:
    context = await _load_reporting_context(session)
    compliance_rows = _build_compliance_rows(
        organizations=context["organizations"],
        reports=context["reports"],
        alerts=context["alerts"],
        cases=context["cases"],
        runs=context["runs"],
    )
    headline, stats, operational = _build_overview_stats(
        user=user,
        reports=context["reports"],
        alerts=context["alerts"],
        cases=context["cases"],
        matches=context["matches"],
        runs=context["runs"],
        compliance_rows=compliance_rows,
        entities=context["entities"],
    )
    return OverviewResponse(headline=headline, operational=operational, stats=stats)


async def build_national_dashboard(session: AsyncSession) -> NationalReportResponse:
    context = await _load_reporting_context(session)
    director = AuthenticatedUser(
        user_id="system-director",
        email="director@kestrel.local",
        org_id="system",
        org_type="regulator",
        role="admin",
        persona="bfiu_director",
        designation="Director",
    )
    compliance_rows = _build_compliance_rows(
        organizations=context["organizations"],
        reports=context["reports"],
        alerts=context["alerts"],
        cases=context["cases"],
        runs=context["runs"],
    )
    headline, stats, operational = _build_overview_stats(
        user=director,
        reports=context["reports"],
        alerts=context["alerts"],
        cases=context["cases"],
        matches=context["matches"],
        runs=context["runs"],
        compliance_rows=compliance_rows,
        entities=context["entities"],
    )
    return NationalReportResponse(
        headline=headline,
        operational=operational,
        stats=stats,
        threat_map=_build_threat_map_rows(context["reports"], context["alerts"]),
    )


async def build_compliance_scorecard(session: AsyncSession) -> ComplianceScorecard:
    context = await _load_reporting_context(session)
    return ComplianceScorecard(
        banks=_build_compliance_rows(
            organizations=context["organizations"],
            reports=context["reports"],
            alerts=context["alerts"],
            cases=context["cases"],
            runs=context["runs"],
        )
    )


async def build_trend_series(session: AsyncSession) -> TrendSeriesResponse:
    context = await _load_reporting_context(session)
    return TrendSeriesResponse(
        series=_build_trend_points(
            alerts=context["alerts"],
            reports=context["reports"],
            cases=context["cases"],
            runs=context["runs"],
        )
    )
