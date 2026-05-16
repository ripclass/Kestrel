"""Pure-helper tests for the realtime TBML modifiers (Phase B).

Three modifiers added to ``realtime_scoring.py``:
  * _score_tbml_payment_mode     — LC-vs-open-account on trade-shaped txns
  * _score_tbml_hs_code_anomaly  — invoice vs market-reference ratio
  * _score_tbml_country_pair     — counterparty in high-risk jurisdiction

Composite ``_score_trade_context`` orchestrates all three. Tests pin each
modifier in isolation + the composite + the no-trade-context skip path.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.services.realtime_scoring import (
    RealtimeScoringRequest,
    _merge_trade_context,
    _score_tbml_country_pair,
    _score_tbml_hs_code_anomaly,
    _score_tbml_payment_mode,
    _score_trade_context,
    _TBML_HIGH_RISK_JURISDICTIONS,
)


def _empty_state() -> tuple[list[dict[str, Any]], dict[str, Any]]:
    return [], {}


def _trade_meta(**trade) -> dict[str, Any]:
    return {"name": "Rahman Enterprises", "trade": dict(trade)}


# _merge_trade_context -----------------------------------------------------


def test_merge_trade_context_pulls_from_either_side() -> None:
    from_meta = {"trade": {"hs_code": "8517.12.00", "invoice_value": 200_000}}
    to_meta = {"trade": {"counterparty_country": "HK", "payment_mode": "open_account"}}
    merged = _merge_trade_context(from_meta, to_meta)
    assert merged == {
        "hs_code": "8517.12.00",
        "invoice_value": 200_000,
        "counterparty_country": "HK",
        "payment_mode": "open_account",
    }


def test_merge_trade_context_empty_when_no_trade_blocks() -> None:
    assert _merge_trade_context({"name": "X"}, None) == {}
    assert _merge_trade_context(None, None) == {}


def test_merge_trade_context_first_side_wins_on_conflict() -> None:
    from_meta = {"trade": {"hs_code": "8517.12.00"}}
    to_meta = {"trade": {"hs_code": "9999.99.99"}}
    merged = _merge_trade_context(from_meta, to_meta)
    assert merged["hs_code"] == "8517.12.00"


# _score_tbml_payment_mode -------------------------------------------------


def test_payment_mode_open_account_on_lc_channel_above_5lakh_fires() -> None:
    reasons, evidence = _empty_state()
    points = _score_tbml_payment_mode(
        channel="LC",
        trade={"payment_mode": "open_account"},
        amount=750_000,
        reasons=reasons,
        evidence=evidence,
    )
    assert points == 15
    assert reasons[0]["rule"] == "tbml_payment_mode_open_account"
    assert "no bank-to-bank" in reasons[0]["reason_text"]
    assert evidence["tbml_payment_mode"] == "open_account"


def test_payment_mode_below_5lakh_does_not_fire() -> None:
    reasons, evidence = _empty_state()
    points = _score_tbml_payment_mode(
        channel="LC",
        trade={"payment_mode": "open_account"},
        amount=200_000,  # below 5 lakh
        reasons=reasons,
        evidence=evidence,
    )
    assert points == 0
    assert reasons == []


def test_payment_mode_lc_sight_does_not_fire() -> None:
    # LC variants are the SAFE path; only non-LC modes flag.
    reasons, evidence = _empty_state()
    points = _score_tbml_payment_mode(
        channel="LC",
        trade={"payment_mode": "lc_sight"},
        amount=10_000_000,
        reasons=reasons,
        evidence=evidence,
    )
    assert points == 0


def test_payment_mode_no_trade_context_skips() -> None:
    reasons, evidence = _empty_state()
    # Empty trade block + non-trade channel
    points = _score_tbml_payment_mode(
        channel="NPSB",
        trade={},
        amount=10_000_000,
        reasons=reasons,
        evidence=evidence,
    )
    assert points == 0


# _score_tbml_hs_code_anomaly ----------------------------------------------


def test_hs_code_over_invoicing_fires_at_3x() -> None:
    reasons, evidence = _empty_state()
    points = _score_tbml_hs_code_anomaly(
        trade={"invoice_value": 300_000, "market_reference_value": 100_000, "hs_code": "8517.12.00"},
        reasons=reasons,
        evidence=evidence,
    )
    assert points == 25
    assert reasons[0]["rule"] == "tbml_hs_code_over_invoicing"
    assert "BFIU §2.4.1.iv" in reasons[0]["reason_text"]
    assert evidence["tbml_invoice_to_market_ratio"] == 3.0


def test_hs_code_under_invoicing_fires_at_0_2x() -> None:
    reasons, evidence = _empty_state()
    points = _score_tbml_hs_code_anomaly(
        trade={"invoice_value": 20_000, "market_reference_value": 100_000, "hs_code": "8517.12.00"},
        reasons=reasons,
        evidence=evidence,
    )
    assert points == 25
    assert reasons[0]["rule"] == "tbml_hs_code_under_invoicing"
    assert evidence["tbml_invoice_to_market_ratio"] == 0.2


def test_hs_code_within_band_does_not_fire() -> None:
    reasons, evidence = _empty_state()
    points = _score_tbml_hs_code_anomaly(
        trade={"invoice_value": 100_000, "market_reference_value": 90_000, "hs_code": "X"},
        reasons=reasons,
        evidence=evidence,
    )
    assert points == 0  # ratio 1.11 within [0.5, 2.0]
    assert reasons == []


def test_hs_code_missing_market_ref_does_not_fire() -> None:
    reasons, evidence = _empty_state()
    points = _score_tbml_hs_code_anomaly(
        trade={"invoice_value": 500_000, "hs_code": "X"},
        reasons=reasons,
        evidence=evidence,
    )
    assert points == 0


# _score_tbml_country_pair -------------------------------------------------


def test_country_pair_high_risk_iran_fires() -> None:
    reasons, evidence = _empty_state()
    points = _score_tbml_country_pair(
        trade={"counterparty_country": "IR"},
        reasons=reasons,
        evidence=evidence,
    )
    assert points == 20
    assert reasons[0]["rule"] == "tbml_country_pair_high_risk"
    assert evidence["tbml_counterparty_country"] == "IR"


def test_country_pair_normal_country_does_not_fire() -> None:
    reasons, evidence = _empty_state()
    points = _score_tbml_country_pair(
        trade={"counterparty_country": "HK"},
        reasons=reasons,
        evidence=evidence,
    )
    assert points == 0


def test_country_pair_missing_does_not_fire() -> None:
    reasons, evidence = _empty_state()
    points = _score_tbml_country_pair(trade={}, reasons=reasons, evidence=evidence)
    assert points == 0


def test_high_risk_jurisdictions_match_trade_evaluator_default() -> None:
    # Realtime modifier list mirrors the batch detection rule default. Keep
    # them in sync; this test fails when one drifts and the other doesn't.
    from app.core.detection.trade_evaluator import DEFAULT_HIGH_RISK_JURISDICTIONS
    assert _TBML_HIGH_RISK_JURISDICTIONS == DEFAULT_HIGH_RISK_JURISDICTIONS


# _score_trade_context composite ------------------------------------------


def test_composite_fires_three_modifiers_on_severe_case() -> None:
    request = RealtimeScoringRequest(
        transaction_id="TX-001",
        from_account="123456789",
        to_account="987654321",
        amount=10_000_000,
        channel="LC",
        transaction_type="debit",
        from_account_metadata=_trade_meta(
            hs_code="8517.12.00",
            invoice_value=300_000,
            market_reference_value=100_000,
            counterparty_country="IR",
            payment_mode="open_account",
        ),
        to_account_metadata=None,
    )
    reasons, evidence = _empty_state()
    score = _score_trade_context(request=request, reasons=reasons, evidence=evidence)
    # 15 (open_account) + 25 (over-invoice 3x) + 20 (Iran) = 60
    assert score == 60
    rules_fired = {r["rule"] for r in reasons}
    assert rules_fired == {
        "tbml_payment_mode_open_account",
        "tbml_hs_code_over_invoicing",
        "tbml_country_pair_high_risk",
    }
    assert evidence["tbml_trade_context"] is True


def test_composite_skips_when_no_trade_block() -> None:
    request = RealtimeScoringRequest(
        transaction_id="TX-002",
        from_account="111",
        to_account="222",
        amount=10_000_000,
        channel="NPSB",
        transaction_type="credit",
        from_account_metadata={"name": "Rahman"},  # no `trade` key
        to_account_metadata={"name": "Pacific"},
    )
    reasons, evidence = _empty_state()
    score = _score_trade_context(request=request, reasons=reasons, evidence=evidence)
    assert score == 0
    assert reasons == []
    assert "tbml_trade_context" not in evidence
