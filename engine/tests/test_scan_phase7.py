from datetime import UTC, datetime
from uuid import uuid4

from app.models.alert import Alert
from app.models.case import Case
from app.models.detection_run import DetectionRun
from app.models.entity import Entity
from app.models.match import Match
from app.services.scanning import _serialize_flagged_account, _serialize_run_detail


def test_serialize_flagged_account_prefers_alert_explainability() -> None:
    entity = Entity(
        id=uuid4(),
        entity_type="account",
        canonical_value="1781430000701",
        display_value="1781430000701",
        display_name="Rizwana Enterprise",
        risk_score=94,
        severity="critical",
        reporting_orgs=[uuid4(), uuid4(), uuid4()],
        report_count=3,
        total_exposure=22_140_000,
        tags=["rapid_cashout", "cross_bank"],
    )
    match = Match(
        id=uuid4(),
        entity_id=entity.id,
        match_key="1781430000701",
        match_type="account",
        involved_org_ids=[uuid4(), uuid4(), uuid4()],
        involved_str_ids=[],
        match_count=3,
        total_exposure=22_140_000,
        risk_score=92,
        severity="critical",
        detected_at=datetime.now(UTC),
    )
    alert = Alert(
        id=uuid4(),
        org_id=uuid4(),
        source_type="cross_bank",
        source_id=uuid4(),
        entity_id=entity.id,
        title="Rapid cashout",
        description="Cross-bank overlap detected.",
        alert_type="cross_bank",
        risk_score=94,
        severity="critical",
        reasons=[
            {
                "rule": "rapid_cashout",
                "score": 75,
                "weight": 8.0,
                "explanation": "83% of inbound funds left the account inside 12 minutes.",
                "evidence": {"debit_pct": 83},
            }
        ],
        created_at=datetime.now(UTC),
    )
    linked_case = Case(
        id=uuid4(),
        org_id=uuid4(),
        case_ref="KST-2604-00011",
        title="Merchant front investigation",
        summary="Rapid cashout with wallet fan-out.",
        severity="critical",
        status="investigating",
        linked_entity_ids=[entity.id],
        linked_alert_ids=[alert.id],
    )

    payload = _serialize_flagged_account(entity, match=match, alert=alert, linked_case=linked_case)

    assert payload["entity_id"] == str(entity.id)
    assert payload["account_name"] == "Rizwana Enterprise"
    assert payload["summary"] == "83% of inbound funds left the account inside 12 minutes."
    assert payload["matched_banks"] == 3
    assert payload["linked_alert_id"] == str(alert.id)
    assert payload["linked_case_id"] == str(linked_case.id)


def test_serialize_run_detail_returns_flagged_accounts_payload() -> None:
    run = DetectionRun(
        id=uuid4(),
        org_id=uuid4(),
        run_type="upload",
        status="completed",
        file_name="dbbl-network-scan.csv",
        tx_count=547,
        accounts_scanned=4,
        alerts_generated=1,
        results={
            "summary": "1 account candidate flagged with highest score 94/100.",
            "flagged_accounts": [
                {
                    "entity_id": str(uuid4()),
                    "account_number": "3480123251160",
                    "account_name": "Eastern Lantern Logistics",
                    "score": 94,
                    "severity": "critical",
                    "summary": "Rapid cashout and cross-bank overlap.",
                    "matched_banks": 4,
                    "total_exposure": 22140000,
                    "tags": ["rapid_cashout"],
                }
            ],
        },
        created_at=datetime.now(UTC),
        started_at=datetime.now(UTC),
        completed_at=datetime.now(UTC),
    )

    payload = _serialize_run_detail(run)

    assert payload["run_type"] == "upload"
    assert payload["summary"] == "1 account candidate flagged with highest score 94/100."
    assert len(payload["flagged_accounts"]) == 1
    assert payload["flagged_accounts"][0]["account_name"] == "Eastern Lantern Logistics"
