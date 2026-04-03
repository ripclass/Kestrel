from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

from app.auth import AuthenticatedUser
from app.models.alert import Alert
from app.models.case import Case
from app.models.detection_run import DetectionRun
from app.models.entity import Entity
from app.models.match import Match
from app.models.org import Organization
from app.models.str_report import STRReport
from app.services.reporting import (
    _build_compliance_rows,
    _build_overview_stats,
    _build_threat_map_rows,
    _build_trend_points,
)


def test_build_compliance_rows_scores_bank_orgs_from_live_counts() -> None:
    bank_a = Organization(id=uuid4(), name="Sonali Bank PLC", slug="sonali", org_type="bank")
    bank_b = Organization(id=uuid4(), name="BRAC Bank PLC", slug="brac", org_type="bank")
    regulator = Organization(id=uuid4(), name="BFIU", slug="bfiu", org_type="regulator")

    reports = [
        STRReport(
            id=uuid4(),
            org_id=bank_a.id,
            report_ref="STR-1",
            subject_account="1781430000701",
            category="fraud",
            total_amount=Decimal("14000000.00"),
            transaction_count=14,
            cross_bank_hit=True,
        ),
        STRReport(
            id=uuid4(),
            org_id=bank_a.id,
            report_ref="STR-2",
            subject_account="207810004901",
            category="fraud",
            total_amount=Decimal("5100000.00"),
            transaction_count=9,
            cross_bank_hit=False,
        ),
        STRReport(
            id=uuid4(),
            org_id=bank_b.id,
            report_ref="STR-3",
            subject_account="540022100018",
            category="money_laundering",
            total_amount=Decimal("2200000.00"),
            transaction_count=6,
            cross_bank_hit=False,
        ),
    ]
    alerts = [
        Alert(
            id=uuid4(),
            org_id=bank_a.id,
            source_type="cross_bank",
            source_id=uuid4(),
            title="Cross-bank overlap",
            alert_type="cross_bank",
            risk_score=88,
            severity="high",
            status="reviewing",
        )
    ]
    cases = [
        Case(
            id=uuid4(),
            org_id=bank_a.id,
            case_ref="KST-2604-00001",
            title="Merchant front case",
            severity="critical",
            status="investigating",
        )
    ]
    runs = [
        DetectionRun(
            id=uuid4(),
            org_id=bank_a.id,
            run_type="upload",
            status="completed",
            file_name="bank-a.csv",
        )
    ]

    rows = _build_compliance_rows(
        organizations=[bank_a, bank_b, regulator],
        reports=reports,
        alerts=alerts,
        cases=cases,
        runs=runs,
    )

    assert [row.org_name for row in rows] == ["Sonali Bank PLC", "BRAC Bank PLC"]
    assert rows[0].score > rows[1].score
    assert rows[0].submission_timeliness >= rows[1].submission_timeliness


def test_build_threat_map_rows_aggregates_channels_and_exposure() -> None:
    reports = [
        STRReport(
            id=uuid4(),
            org_id=uuid4(),
            report_ref="STR-1",
            subject_account="1781430000701",
            category="fraud",
            total_amount=Decimal("14000000.00"),
            transaction_count=14,
            primary_channel="RTGS",
            channels=["RTGS", "MFS"],
        ),
        STRReport(
            id=uuid4(),
            org_id=uuid4(),
            report_ref="STR-2",
            subject_account="207810004901",
            category="money_laundering",
            total_amount=Decimal("3500000.00"),
            transaction_count=10,
            primary_channel="MFS",
            channels=["MFS"],
        ),
    ]
    alerts = [
        Alert(
            id=uuid4(),
            org_id=uuid4(),
            source_type="cross_bank",
            source_id=uuid4(),
            title="MFS cashout",
            description="MFS burst linked to recent peer-bank overlap.",
            alert_type="cross_bank",
            risk_score=82,
            severity="high",
            status="open",
        )
    ]

    rows = _build_threat_map_rows(reports, alerts)

    assert rows[0].channel == "MFS"
    assert rows[0].signal_count >= 2
    assert rows[0].total_exposure >= 17_500_000
    assert any(row.channel == "RTGS" for row in rows)


def test_build_trend_points_groups_live_activity_by_month() -> None:
    january = datetime(2026, 1, 10, 10, 0, tzinfo=UTC)
    february = datetime(2026, 2, 11, 10, 0, tzinfo=UTC)

    alerts = [
        Alert(
            id=uuid4(),
            org_id=uuid4(),
            source_type="cross_bank",
            source_id=uuid4(),
            title="Jan alert",
            alert_type="cross_bank",
            risk_score=82,
            severity="high",
            status="open",
            created_at=january,
        )
    ]
    reports = [
        STRReport(
            id=uuid4(),
            org_id=uuid4(),
            report_ref="STR-1",
            subject_account="1781430000701",
            category="fraud",
            total_amount=Decimal("1200000.00"),
            transaction_count=4,
            reported_at=february,
        )
    ]
    cases = [
        Case(
            id=uuid4(),
            org_id=uuid4(),
            case_ref="KST-2602-00002",
            title="Feb case",
            severity="high",
            status="investigating",
            created_at=february,
        )
    ]
    runs = [
        DetectionRun(
            id=uuid4(),
            org_id=uuid4(),
            run_type="upload",
            status="completed",
            file_name="feb.csv",
            created_at=february,
        )
    ]

    series = _build_trend_points(alerts=alerts, reports=reports, cases=cases, runs=runs)

    assert [point.month for point in series] == ["Jan", "Feb"]
    assert series[0].alerts == 1
    assert series[1].str_reports == 1
    assert series[1].cases == 1
    assert series[1].scans == 1


def test_build_overview_stats_bank_persona_uses_live_run_and_signal_counts() -> None:
    org_id = str(uuid4())
    user = AuthenticatedUser(
        user_id=str(uuid4()),
        email="camlco@kestrel-sonali.test",
        org_id=org_id,
        org_type="bank",
        role="manager",
        persona="bank_camlco",
        designation="Chief AML Compliance Officer",
    )
    entities = [
        Entity(
            id=uuid4(),
            entity_type="account",
            canonical_value="3502735816440",
            display_value="3502735816440",
            display_name="Delta Anchor Partners",
            risk_score=82,
            severity="high",
            reporting_orgs=[uuid4(), uuid4(), uuid4(), uuid4()],
        )
    ]
    entities[0].reporting_orgs = [uuid4(), uuid4()]
    entities[0].reporting_orgs.append(uuid4())
    entities[0].reporting_orgs.append(uuid4())
    matching_org_uuid = uuid4()
    entities[0].reporting_orgs = [matching_org_uuid]
    user.org_id = str(matching_org_uuid)

    runs = [
        DetectionRun(
            id=uuid4(),
            org_id=matching_org_uuid,
            run_type="upload",
            status="completed",
            file_name="dbbl.csv",
            results={"flagged_accounts": [{"entity_id": "x"}]},
            created_at=datetime.now(UTC),
        )
    ]
    matches = [
        Match(
            id=uuid4(),
            entity_id=entities[0].id,
            match_key="3502735816440",
            match_type="account",
            involved_org_ids=[uuid4(), uuid4()],
            involved_str_ids=[],
            match_count=4,
            total_exposure=Decimal("11000000.00"),
            risk_score=81,
            severity="high",
        )
    ]
    compliance_rows = []

    headline, stats, operational = _build_overview_stats(
        user=user,
        reports=[],
        alerts=[],
        cases=[],
        matches=matches,
        runs=runs,
        compliance_rows=compliance_rows,
        entities=entities,
    )

    assert headline == "Your bank posture with peer-network intelligence overlaid."
    assert stats[0].label == "Accounts above threshold"
    assert stats[0].value == "1"
    assert stats[1].label == "Peer-network signals"
    assert len(operational) == 3
