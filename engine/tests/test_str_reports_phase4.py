from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

from app.auth import AuthenticatedUser
from app.models.audit import AuditLog
from app.models.str_report import STRReport
from app.services.str_reports import _append_lifecycle_event, build_str_enrichment_payload, serialize_report_detail


def build_user(**overrides) -> AuthenticatedUser:
    payload = {
        "user_id": str(uuid4()),
        "email": "analyst@example.com",
        "org_id": str(uuid4()),
        "org_type": "bank",
        "role": "manager",
        "persona": "bank_camlco",
        "designation": "Chief AML Compliance Officer",
    }
    payload.update(overrides)
    return AuthenticatedUser(**payload)


def build_report() -> STRReport:
    return STRReport(
        id=uuid4(),
        org_id=uuid4(),
        report_ref="STR-2604-000001",
        status="draft",
        subject_name="Rizwana Enterprise",
        subject_account="1781430000701",
        subject_bank="Sonali Bank PLC",
        subject_phone="01712345678",
        subject_wallet="wallet-001",
        subject_nid="1999999999999",
        total_amount=Decimal("14000000.00"),
        currency="BDT",
        transaction_count=14,
        primary_channel="RTGS",
        category="fraud",
        narrative="Rapid inbound funds followed by wallet cash-out.",
        channels=["RTGS", "MFS"],
        cross_bank_hit=True,
        metadata_json={"review": {"notes": [{"note": "Initial note"}]}},
        created_at=datetime.now(UTC),
    )


def test_append_lifecycle_event_records_history_and_assignment() -> None:
    user = build_user()

    metadata = _append_lifecycle_event(
        {},
        action="start_review",
        user=user,
        from_status="submitted",
        to_status="under_review",
        note="Escalated for regulator review.",
        assigned_to=str(uuid4()),
    )

    assert metadata["review"]["assigned_to"]
    assert metadata["review"]["notes"][0]["note"] == "Escalated for regulator review."
    assert metadata["review"]["status_history"][0]["action"] == "start_review"
    assert metadata["review"]["status_history"][0]["to_status"] == "under_review"


def test_build_str_enrichment_payload_includes_trigger_facts() -> None:
    report = build_report()

    payload = build_str_enrichment_payload(report)

    assert payload["subject_account"] == "1781430000701"
    assert any("14 transactions" in fact for fact in payload["trigger_facts"])
    assert any("Cross-bank matches" in fact for fact in payload["trigger_facts"])
    assert any("review notes" in fact.lower() for fact in payload["trigger_facts"])


def test_serialize_report_detail_reads_embedded_review_and_enrichment() -> None:
    report = build_report()
    report.metadata_json = {
        "review": {
            "assigned_to": str(uuid4()),
            "notes": [{"actor_user_id": str(uuid4()), "actor_role": "analyst", "note": "Hold for review", "occurred_at": datetime.now(UTC).isoformat()}],
            "status_history": [
                {
                    "action": "submitted",
                    "actor_user_id": str(uuid4()),
                    "actor_role": "manager",
                    "actor_org_type": "bank",
                    "from_status": "draft",
                    "to_status": "submitted",
                    "occurred_at": datetime.now(UTC).isoformat(),
                }
            ],
        },
        "enrichment": {
            "draft_narrative": "Suggested narrative",
            "missing_fields": ["subject_nid"],
            "category_suggestion": "fraud",
            "severity_suggestion": "high",
            "trigger_facts": ["Fact 1"],
            "extracted_entities": [{"entity_type": "phone", "value": "[REDACTED_PHONE]", "confidence": 0.62}],
            "generated_at": datetime.now(UTC).isoformat(),
            "narrative_meta": {
                "task": "str_narrative",
                "provider": "heuristic",
                "model": "heuristic-v1",
                "prompt_version": "v1",
                "redaction_mode": "redact",
                "fallback_used": True,
                "audit_logged": True,
                "attempts": [{"provider": "heuristic", "model": "heuristic-v1", "success": True}],
            },
            "extraction_meta": {
                "task": "entity_extraction",
                "provider": "heuristic",
                "model": "heuristic-v1",
                "prompt_version": "v1",
                "redaction_mode": "redact",
                "fallback_used": True,
                "audit_logged": True,
                "attempts": [{"provider": "heuristic", "model": "heuristic-v1", "success": True}],
            },
        },
    }

    detail = serialize_report_detail(report, "Sonali Bank PLC")

    assert detail.org_name == "Sonali Bank PLC"
    assert detail.review.status_history[0].to_status == "submitted"
    assert detail.enrichment is not None
    assert detail.enrichment.category_suggestion == "fraud"
    assert detail.enrichment.extracted_entities[0].entity_type == "phone"


def test_audit_log_uses_server_default_timestamp() -> None:
    assert AuditLog.__table__.c.created_at.server_default is not None


def test_timestamp_mixin_sets_server_default_for_updated_at() -> None:
    assert STRReport.__table__.c.updated_at.server_default is not None
