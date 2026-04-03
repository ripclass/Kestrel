from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

from app.models.alert import Alert
from app.models.case import Case
from app.services.alerts import _normalize_reasons, _serialize_alert_summary
from app.services.case_mgmt import _serialize_case_notes, _serialize_case_summary, _serialize_case_timeline


def test_serialize_alert_summary_exposes_assignment_case_and_reasons() -> None:
    assignee_id = uuid4()
    case_id = uuid4()
    entity_id = uuid4()

    alert = Alert(
        id=uuid4(),
        org_id=uuid4(),
        source_type="cross_bank",
        source_id=uuid4(),
        entity_id=entity_id,
        title="Cross-bank overlap",
        description="Identifier matched across peer banks.",
        alert_type="cross_bank",
        risk_score=87,
        severity="high",
        status="reviewing",
        reasons=[
            {
                "rule": "cross_bank_overlap",
                "score": 64,
                "weight": 6.0,
                "explanation": "Matched across three peer institutions.",
                "evidence": {"banks": 3},
            }
        ],
        assigned_to=assignee_id,
        case_id=case_id,
        created_at=datetime.now(UTC),
    )

    payload = _serialize_alert_summary(
        alert,
        org_name="Bangladesh Financial Intelligence Unit",
        profile_name_map={str(assignee_id): "Sadia Rahman"},
    )

    assert payload["assigned_to"] == "Sadia Rahman"
    assert payload["case_id"] == str(case_id)
    assert payload["entity_id"] == str(entity_id)
    assert payload["reasons"][0]["rule"] == "cross_bank_overlap"


def test_case_serializers_preserve_linked_alerts_notes_and_timeline_order() -> None:
    assignee_id = uuid4()
    linked_alert_id = uuid4()
    linked_entity_id = uuid4()
    earlier = "2026-04-01T16:30:00+00:00"
    later = "2026-04-01T18:45:00+00:00"

    case = Case(
        id=uuid4(),
        org_id=uuid4(),
        case_ref="KST-2604-00001",
        title="Merchant front investigation",
        summary="Rapid cashout and wallet fan-out.",
        category="fraud",
        severity="critical",
        status="investigating",
        assigned_to=assignee_id,
        linked_alert_ids=[linked_alert_id],
        linked_entity_ids=[linked_entity_id],
        total_exposure=Decimal("22140000.00"),
        recovered=Decimal("0.00"),
        timeline=[
            {"type": "note", "user_id": str(assignee_id), "timestamp": earlier, "content": "Requested KYC pack."},
            {"type": "status_change", "user_id": str(assignee_id), "timestamp": later, "content": "Escalated for case review."},
        ],
        tags=["rapid_cashout"],
    )

    profile_name_map = {str(assignee_id): "Sadia Rahman"}

    summary = _serialize_case_summary(case, profile_name_map)
    notes = _serialize_case_notes(case.timeline, profile_name_map)
    timeline = _serialize_case_timeline(case.timeline, profile_name_map)

    assert summary["assigned_to"] == "Sadia Rahman"
    assert summary["linked_alert_ids"] == [str(linked_alert_id)]
    assert summary["linked_entity_ids"] == [str(linked_entity_id)]
    assert notes[0]["actor_user_id"] == "Sadia Rahman"
    assert notes[0]["note"] == "Requested KYC pack."
    assert timeline[0]["description"] == "Escalated for case review."
    assert timeline[1]["description"] == "Requested KYC pack."


def test_normalize_reasons_backfills_legacy_seed_shape() -> None:
    payload = _normalize_reasons(
        [
            {
                "rule": "rapid_cashout",
                "score": 28,
                "explanation": "Peak same-day outflow reached 90% of inbound funds.",
            }
        ]
    )

    assert payload[0]["rule"] == "rapid_cashout"
    assert payload[0]["weight"] == 1.0
    assert payload[0]["evidence"] == {}
