"""Pure-helper tests for the 6 TBML detection rules (Phase B).

Each test exercises one rule with a SimpleNamespace trade row + the loaded
YAML config. Cross-org rule (multiple_invoicing) also passes a peer-trade
list for the same B/L number.
"""
from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.core.detection.trade_evaluator import (
    DEFAULT_HIGH_RISK_JURISDICTIONS,
    evaluate_declaration_value_mismatch,
    evaluate_multiple_invoicing,
    evaluate_over_invoicing,
    evaluate_phantom_shipment,
    evaluate_trade_transactions,
    evaluate_transshipment_routing,
    evaluate_under_invoicing,
    load_trade_rules,
)


@pytest.fixture(scope="module")
def rules() -> dict[str, dict]:
    return {rule["code"]: rule for rule in load_trade_rules()}


def _trade(**kwargs) -> SimpleNamespace:
    defaults = dict(
        id="trade-test-001",
        org_id="org-001",
        trade_ref="TBT-2604-00001",
        trade_side="import",
        payment_mode="lc_sight",
        subject_name="Rahman Enterprises",
        subject_account="018020012345",
        counterparty_name="Pacific Trading HK",
        counterparty_country="HK",
        counterparty_bank=None,
        notify_party=None,
        consignee=None,
        hs_code="8517.12.00",
        invoice_value=100_000,
        declared_value=None,
        market_reference_value=None,
        settlement_amount=None,
        currency="USD",
        lc_reference=None,
        lc_advising_bank=None,
        bl_number=None,
        vessel=None,
        port_of_loading=None,
        port_of_discharge=None,
        transshipment_ports=[],
        be_number=None,
        status="open",
    )
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


# -- over_invoicing --------------------------------------------------------


def test_loaded_six_rules(rules) -> None:
    assert set(rules) == {
        "over_invoicing",
        "under_invoicing",
        "multiple_invoicing",
        "phantom_shipment",
        "declaration_value_mismatch",
        "transshipment_routing",
    }


def test_over_invoicing_fires_at_3x(rules) -> None:
    trade = _trade(invoice_value=300_000, market_reference_value=100_000)
    hit = evaluate_over_invoicing(trade, rule_config=rules["over_invoicing"])
    assert hit is not None
    assert hit.severity == "critical" or hit.severity == "high"
    assert hit.score >= 75
    assert hit.predicate_offences == ["smuggling_customs_excise", "tax_related_offences"]
    assert hit.bfiu_avenue_ref == "2.4.1.iv"
    assert "ratio" in hit.evidence and hit.evidence["ratio"] == 3.0


def test_over_invoicing_within_band_does_not_fire(rules) -> None:
    trade = _trade(invoice_value=120_000, market_reference_value=100_000)
    hit = evaluate_over_invoicing(trade, rule_config=rules["over_invoicing"])
    assert hit is None  # ratio 1.2 below 1.5 threshold


def test_over_invoicing_no_market_reference_does_not_fire(rules) -> None:
    trade = _trade(invoice_value=500_000)
    hit = evaluate_over_invoicing(trade, rule_config=rules["over_invoicing"])
    assert hit is None


# -- under_invoicing -------------------------------------------------------


def test_under_invoicing_fires_below_30pct(rules) -> None:
    trade = _trade(invoice_value=20_000, market_reference_value=100_000, payment_mode="lc_btb")
    hit = evaluate_under_invoicing(trade, rule_config=rules["under_invoicing"])
    assert hit is not None
    # base 55 + 25 (ratio <= 0.3) + 15 (lc_btb) = 95 → critical
    assert hit.severity == "critical"
    assert hit.evidence["ratio"] == 0.2


def test_under_invoicing_borderline_does_not_fire(rules) -> None:
    trade = _trade(invoice_value=60_000, market_reference_value=100_000)
    hit = evaluate_under_invoicing(trade, rule_config=rules["under_invoicing"])
    assert hit is None  # ratio 0.6 above 0.5 max


# -- multiple_invoicing ----------------------------------------------------


def test_multiple_invoicing_two_orgs_same_bl(rules) -> None:
    trade_a = _trade(id="trade-001", org_id="org-001", bl_number="HLCU-HKG-7712-0011", invoice_value=500_000)
    trade_b = _trade(id="trade-002", org_id="org-002", bl_number="HLCU-HKG-7712-0011", invoice_value=500_000)
    hit = evaluate_multiple_invoicing(trade_a, rule_config=rules["multiple_invoicing"], peer_trades=[trade_b])
    assert hit is not None
    assert hit.evidence["distinct_orgs"] == 2
    assert hit.evidence["match_key"] == "HLCU-HKG-7712-0011"
    assert hit.severity in {"high", "critical"}


def test_multiple_invoicing_three_orgs_same_lc(rules) -> None:
    trade_a = _trade(id="trade-001", org_id="org-001", lc_reference="LC-2026-04123", invoice_value=4_000_000)
    peer_b = _trade(id="trade-002", org_id="org-002", lc_reference="LC-2026-04123", invoice_value=4_000_000)
    peer_c = _trade(id="trade-003", org_id="org-003", lc_reference="LC-2026-04123", invoice_value=4_000_000)
    hit = evaluate_multiple_invoicing(
        trade_a, rule_config=rules["multiple_invoicing"], peer_trades=[peer_b, peer_c]
    )
    assert hit is not None
    assert hit.evidence["distinct_orgs"] == 3
    # base 70 + 20 (distinct >= 3) + 10 (lc_match) + 10 (aggregate > 1cr) = 110 → clamped 100 → critical
    assert hit.score == 100
    assert hit.severity == "critical"


def test_multiple_invoicing_single_org_does_not_fire(rules) -> None:
    trade_a = _trade(id="trade-001", org_id="org-001", bl_number="X-123")
    trade_b = _trade(id="trade-002", org_id="org-001", bl_number="X-123")  # same org
    hit = evaluate_multiple_invoicing(trade_a, rule_config=rules["multiple_invoicing"], peer_trades=[trade_b])
    assert hit is None


# -- phantom_shipment ------------------------------------------------------


def test_phantom_shipment_settlement_without_evidence(rules) -> None:
    trade = _trade(
        settlement_amount=10_000_000,
        status="settled",
        bl_number=None,
        port_of_loading=None,
        vessel=None,
    )
    hit = evaluate_phantom_shipment(trade, rule_config=rules["phantom_shipment"])
    assert hit is not None
    assert hit.severity in {"critical", "high"}
    assert hit.evidence["settlement_amount"] == 10_000_000


def test_phantom_shipment_with_bl_does_not_fire(rules) -> None:
    trade = _trade(
        settlement_amount=10_000_000,
        status="settled",
        bl_number="HLCU-X-1",
    )
    hit = evaluate_phantom_shipment(trade, rule_config=rules["phantom_shipment"])
    assert hit is None


def test_phantom_shipment_unsettled_does_not_fire(rules) -> None:
    trade = _trade(settlement_amount=0, status="open")
    hit = evaluate_phantom_shipment(trade, rule_config=rules["phantom_shipment"])
    assert hit is None


# -- declaration_value_mismatch -------------------------------------------


def test_declaration_value_mismatch_undervaluing_be(rules) -> None:
    trade = _trade(invoice_value=200_000, declared_value=80_000, be_number=None)
    hit = evaluate_declaration_value_mismatch(trade, rule_config=rules["declaration_value_mismatch"])
    assert hit is not None
    # base 50 + 25 (ratio<=0.5) + 15 (be_number null) = 90 → critical
    assert hit.severity == "critical"
    assert hit.evidence["ratio_pct"] == 40.0


def test_declaration_value_mismatch_overdeclaration(rules) -> None:
    trade = _trade(invoice_value=100_000, declared_value=200_000, be_number="BE-1")
    hit = evaluate_declaration_value_mismatch(trade, rule_config=rules["declaration_value_mismatch"])
    assert hit is not None
    # base 50 + 20 (ratio>=1.5) = 70 → high
    assert hit.severity == "high"


def test_declaration_value_within_band_does_not_fire(rules) -> None:
    trade = _trade(invoice_value=100_000, declared_value=90_000)
    hit = evaluate_declaration_value_mismatch(trade, rule_config=rules["declaration_value_mismatch"])
    assert hit is None  # ratio 0.9 within 0.7..1.3


# -- transshipment_routing -------------------------------------------------


def test_transshipment_routing_high_risk_jurisdiction(rules) -> None:
    trade = _trade(transshipment_ports=["SG", "IR"])
    hit = evaluate_transshipment_routing(trade, rule_config=rules["transshipment_routing"])
    assert hit is not None
    # base 40 + 30 (via high risk) + 15 (lc_route_undeclared) = 85 → critical band
    assert hit.severity == "critical"
    assert "IR" in hit.evidence["transshipment_chain"] or "IR" in str(hit.evidence)


def test_transshipment_routing_single_normal_port_does_not_fire(rules) -> None:
    trade = _trade(transshipment_ports=["SG"])  # 1 port, not high-risk
    hit = evaluate_transshipment_routing(trade, rule_config=rules["transshipment_routing"])
    assert hit is None


def test_transshipment_routing_three_ports_fires(rules) -> None:
    trade = _trade(transshipment_ports=["SG", "AE", "MY"])
    hit = evaluate_transshipment_routing(trade, rule_config=rules["transshipment_routing"])
    assert hit is not None
    # base 40 + 25 (count>=3) + 15 (lc undeclared) = 80 → high
    assert hit.evidence["transshipment_port_count"] == 3


# -- evaluate_trade_transactions top-level entry --------------------------


def test_top_level_runs_all_rules_against_all_trades() -> None:
    a = _trade(
        id="trade-001",
        org_id="org-001",
        invoice_value=300_000,
        market_reference_value=100_000,  # over-invoicing
        bl_number="BL-XYZ",
        port_of_loading="HKG",
    )
    b = _trade(
        id="trade-002",
        org_id="org-002",
        invoice_value=20_000,
        market_reference_value=100_000,  # under-invoicing
        bl_number="BL-XYZ",  # same B/L as A — also fires multiple_invoicing
        port_of_loading="HKG",
    )
    hits = evaluate_trade_transactions([a, b])
    codes = sorted({hit.rule_code for hit in hits})
    assert "over_invoicing" in codes
    assert "under_invoicing" in codes
    assert "multiple_invoicing" in codes


# -- BFIU avenue ref + predicate offences propagate -----------------------


def test_every_rule_has_bfiu_avenue_ref_and_predicates(rules) -> None:
    for code, rule in rules.items():
        assert rule.get("bfiu_avenue_ref"), f"{code} missing bfiu_avenue_ref"
        offences = rule.get("predicate_offences") or []
        assert offences, f"{code} missing predicate_offences"
        assert "smuggling_customs_excise" in offences, (
            f"{code} should cite §2(cc)(18) smuggling_customs_excise for TBML"
        )


def test_default_high_risk_jurisdictions_includes_sanctioned_countries() -> None:
    # Cuba (CU), Iran (IR), North Korea (KP), Syria (SY) all in the default set.
    for code in ("CU", "IR", "KP", "SY"):
        assert code in DEFAULT_HIGH_RISK_JURISDICTIONS
