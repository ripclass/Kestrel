"""Unit coverage for the match-definition executor's pure helpers.

The full ``execute_match_definition`` flow needs an async Postgres
session (Entity / Alert use UUID + ARRAY + JSONB types that don't
translate to SQLite). This file pins the shape/contract of the
helpers that build the entity record and the resulting Alert row,
which is where most of the "did the executor produce the right
data?" risk lives.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from types import SimpleNamespace

from app.core.match_dsl import AlertTemplate, validate_definition
from app.services.match_definitions import _build_alert, _entity_to_dict


def _entity(**overrides: object) -> SimpleNamespace:
    base = dict(
        id=uuid.uuid4(),
        entity_type="account",
        canonical_value="1234567890",
        display_value="Account 1234567890",
        display_name="Acme Holdings",
        risk_score=82,
        severity="high",
        confidence=0.91,
        status="active",
        source="system",
        report_count=3,
        total_exposure=4_500_000,
        tags=["mfs", "rapid_cashout"],
        reporting_orgs=[uuid.uuid4(), uuid.uuid4()],
        first_seen=datetime(2026, 1, 1, tzinfo=timezone.utc),
        last_seen=datetime(2026, 4, 1, tzinfo=timezone.utc),
    )
    base.update(overrides)
    return SimpleNamespace(**base)


def _definition(name: str = "Custom MFS sweep") -> SimpleNamespace:
    return SimpleNamespace(id=uuid.uuid4(), org_id=uuid.uuid4(), name=name)


def test_entity_to_dict_normalises_arrays_and_numbers() -> None:
    e = _entity()
    record = _entity_to_dict(e)
    assert record["entity_type"] == "account"
    assert record["risk_score"] == 82
    assert record["confidence"] == 0.91
    # reporting_orgs are stringified UUIDs, ready for DSL evaluation
    assert all(isinstance(rid, str) for rid in record["reporting_orgs"])  # type: ignore[arg-type]
    assert record["tags"] == ["mfs", "rapid_cashout"]
    # nullable fields default to safe values
    e2 = _entity(risk_score=None, tags=None, reporting_orgs=None)
    rec2 = _entity_to_dict(e2)
    assert rec2["risk_score"] == 0
    assert rec2["tags"] == []
    assert rec2["reporting_orgs"] == []


def test_build_alert_inherits_severity_and_score_when_template_blank() -> None:
    e = _entity(severity="critical", risk_score=92)
    d = _definition()
    alert = _build_alert(definition=d, entity=e, template=AlertTemplate())
    assert alert.severity == "critical"
    assert alert.risk_score == 92
    assert alert.source_type == "match_definition"
    assert alert.source_id == d.id
    assert alert.entity_id == e.id
    assert alert.alert_type == "match_definition"
    assert alert.status == "open"
    assert "Account 1234567890" in alert.title


def test_build_alert_template_overrides_take_precedence() -> None:
    e = _entity(severity="high", risk_score=70)
    d = _definition(name="Tier-1 watchlist sweep")
    template = AlertTemplate(
        title="Watchlist hit: {display_name} ({display_value})",
        description="Picked up by {name}",
        severity="critical",
        risk_score=88,
        alert_type="watchlist",
    )
    alert = _build_alert(definition=d, entity=e, template=template)
    assert alert.severity == "critical"
    assert alert.risk_score == 88
    assert alert.alert_type == "watchlist"
    assert alert.title == "Watchlist hit: Acme Holdings (Account 1234567890)"
    assert alert.description == "Picked up by Tier-1 watchlist sweep"


def test_build_alert_clamps_risk_score_into_zero_to_hundred() -> None:
    e = _entity()
    d = _definition()
    over = _build_alert(
        definition=d,
        entity=e,
        template=AlertTemplate(risk_score=900, severity="medium"),
    )
    under = _build_alert(
        definition=d,
        entity=e,
        template=AlertTemplate(risk_score=-25, severity="low"),
    )
    assert over.risk_score == 100
    assert under.risk_score == 0


def test_build_alert_falls_back_to_medium_for_unknown_severity() -> None:
    e = _entity(severity=None, risk_score=None)
    d = _definition()
    alert = _build_alert(
        definition=d,
        entity=e,
        template=AlertTemplate(severity="bogus"),
    )
    assert alert.severity == "medium"
    # No score on entity or template -> derived from severity
    assert alert.risk_score == 50


def test_build_alert_attaches_definition_reason() -> None:
    e = _entity()
    d = _definition(name="Tier-1 watchlist sweep")
    alert = _build_alert(definition=d, entity=e, template=AlertTemplate())
    assert isinstance(alert.reasons, list)
    assert alert.reasons[0]["rule"] == "match_definition"
    assert "Tier-1 watchlist sweep" in alert.reasons[0]["explanation"]


def test_dsl_round_trip_against_entity_record() -> None:
    """Smoke check: the DSL validator + evaluator + entity dict all line up."""
    dsl = validate_definition(
        {
            "match": {
                "scope": "entity",
                "where": {
                    "all": [
                        {"field": "risk_score", "op": ">=", "value": 80},
                        {"field": "tags", "op": "contains", "value": "mfs"},
                    ]
                },
                "alert": {"title": "Watchlist hit: {display_value}"},
            }
        }
    )
    from app.core.match_dsl import evaluate

    record = _entity_to_dict(_entity(risk_score=85))
    assert evaluate(record, dsl) is True
    record_low = _entity_to_dict(_entity(risk_score=10))
    assert evaluate(record_low, dsl) is False
