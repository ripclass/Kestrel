"""Pure-helper tests for the TBML pipeline integration (Phase B).

Tests cover the TradeRuleHit → Alert kwargs translation, evidence
sanitization, and the round-trip from a TradeRuleHit through to the
data shape that gets persisted on the alerts table.

Skips the DB layer — the SQLAlchemy session interaction is exercised by
the integration tests that already cover scan_pipeline.py. Here we pin
the pure-function shape.
"""
from __future__ import annotations

import uuid
from types import SimpleNamespace

import pytest

from app.core.detection.trade_evaluator import (
    TradeRuleHit,
    evaluate_over_invoicing,
    load_trade_rules,
)
from app.core.tbml_pipeline import (
    _normalize_evidence,
    _rule_hit_to_alert_kwargs,
)


@pytest.fixture(scope="module")
def rules() -> dict[str, dict]:
    return {rule["code"]: rule for rule in load_trade_rules()}


def _trade(**kwargs) -> SimpleNamespace:
    defaults = dict(
        id=uuid.uuid4(),
        org_id=uuid.uuid4(),
        trade_ref="TBT-2604-00001",
        trade_side="import",
        payment_mode="lc_sight",
        subject_name="Rahman Enterprises",
        subject_account="018020012345",
        counterparty_name="Pacific Trading HK",
        counterparty_country="HK",
        counterparty_bank=None,
        hs_code="8517.12.00",
        invoice_value=300_000,
        market_reference_value=100_000,
        currency="USD",
        lc_advising_bank=None,
        status="open",
    )
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


def test_rule_hit_translates_to_alert_kwargs(rules) -> None:
    trade = _trade()
    hit = evaluate_over_invoicing(trade, rule_config=rules["over_invoicing"])
    assert hit is not None
    kwargs = _rule_hit_to_alert_kwargs(hit, trade=trade)
    assert kwargs["source_type"] == "tbml_scan"
    assert kwargs["alert_type"] == "over_invoicing"
    assert kwargs["org_id"] == trade.org_id
    assert kwargs["linked_trade_id"] == trade.id
    assert kwargs["source_id"] == trade.id
    assert kwargs["bfiu_avenue_ref"] == "2.4.1.iv"
    assert "smuggling_customs_excise" in kwargs["predicate_offences"]
    assert "tax_related_offences" in kwargs["predicate_offences"]
    # Reasons array carries one envelope per rule with nested modifier reasons.
    assert isinstance(kwargs["reasons"], list)
    assert len(kwargs["reasons"]) == 1
    envelope = kwargs["reasons"][0]
    assert envelope["rule"] == "over_invoicing"
    assert envelope["weight"] == 7.0
    assert envelope["explanation"]  # alert_description
    assert isinstance(envelope["evidence"], dict)
    assert envelope["evidence"]["ratio"] == 3.0
    assert envelope["evidence"]["currency"] == "USD"


def test_alert_kwargs_severity_and_score_passed_through(rules) -> None:
    # An extreme over-invoicing case → critical severity.
    trade = _trade(invoice_value=1_000_000, market_reference_value=100_000, payment_mode="open_account")
    hit = evaluate_over_invoicing(trade, rule_config=rules["over_invoicing"])
    assert hit is not None
    kwargs = _rule_hit_to_alert_kwargs(hit, trade=trade)
    assert kwargs["severity"] == "critical"
    assert kwargs["risk_score"] >= 90


def test_normalize_evidence_drops_none_and_stringifies_complex_values() -> None:
    evidence = {
        "trade_ref": "TBT-001",
        "invoice_value": 100.0,
        "currency": "USD",
        "settled": True,
        "lc_issue_date": None,  # dropped
        "uuid": uuid.UUID("12345678-1234-5678-1234-567812345678"),  # stringified
    }
    cleaned = _normalize_evidence(evidence)
    assert "lc_issue_date" not in cleaned
    assert cleaned["trade_ref"] == "TBT-001"
    assert cleaned["invoice_value"] == 100.0
    assert cleaned["settled"] is True
    assert cleaned["uuid"] == "12345678-1234-5678-1234-567812345678"


def test_rule_hit_to_alert_kwargs_handles_missing_org_id() -> None:
    # A TradeRuleHit with no org_id and no fallback trade → org_id=None
    # which the pipeline filters out before insert.
    hit = TradeRuleHit(
        trade_id="trade-orphan",
        org_id="",
        rule_code="over_invoicing",
        score=50,
        weight=1.0,
        severity="medium",
    )
    kwargs = _rule_hit_to_alert_kwargs(hit, trade=None)
    assert kwargs["org_id"] is None
    assert kwargs["linked_trade_id"] is None  # 'trade-orphan' isn't a uuid


def test_alert_kwargs_reasons_envelope_matches_existing_alert_shape(rules) -> None:
    # The pipeline emits a reasons array of {rule, score, weight,
    # explanation, evidence, reasons[]} — same shape as the existing
    # scan alerts (services/scan_pipeline.py), so the alerts UI doesn't
    # need a TBML-specific code path.
    trade = _trade()
    hit = evaluate_over_invoicing(trade, rule_config=rules["over_invoicing"])
    kwargs = _rule_hit_to_alert_kwargs(hit, trade=trade)
    envelope = kwargs["reasons"][0]
    assert set(envelope.keys()) == {"rule", "score", "weight", "explanation", "evidence", "reasons"}
    # Nested 'reasons' is the per-modifier breakdown (modifier/score_added/reason).
    for modifier in envelope["reasons"]:
        assert set(modifier.keys()) >= {"modifier", "score_added", "reason"}
