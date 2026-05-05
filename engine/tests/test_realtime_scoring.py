"""Pure-helper coverage for the realtime scoring service (V2 phase 3.1).

Async paths (score_transaction, record_feedback, list_recent_scores) need a
real Postgres session because they touch entities/matches/audit_log and the
new realtime_scoring_log table. This file pins the deterministic scoring
helpers — the decision bands, amount-band contributions, channel risk,
account-age signals, entity-risk pull, and cross-bank flagging — which is
where the regression risk lives.
"""
from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

from app.services.realtime_scoring import (
    _DECISION_APPROVE_MAX,
    _DECISION_HOLD_MAX,
    _DECISION_REVIEW_MAX,
    _account_age_days,
    _confidence_from_signals,
    _decide,
    _normalize_for_lookup,
    _percentile,
    _score_account_age,
    _score_amount,
    _score_channel,
    _score_cross_bank,
    _score_entity_risk,
)


# Decision-band invariants ---------------------------------------------------

def test_decide_approve_band() -> None:
    assert _decide(0) == "approve"
    assert _decide(15) == "approve"
    assert _decide(_DECISION_APPROVE_MAX - 1) == "approve"


def test_decide_review_band() -> None:
    assert _decide(_DECISION_APPROVE_MAX) == "review"
    assert _decide(45) == "review"
    assert _decide(_DECISION_REVIEW_MAX - 1) == "review"


def test_decide_hold_band() -> None:
    assert _decide(_DECISION_REVIEW_MAX) == "hold"
    assert _decide(70) == "hold"
    assert _decide(_DECISION_HOLD_MAX - 1) == "hold"


def test_decide_reject_band() -> None:
    assert _decide(_DECISION_HOLD_MAX) == "reject"
    assert _decide(85) == "reject"
    assert _decide(100) == "reject"


# Amount-band scoring --------------------------------------------------------

def test_score_amount_normal_amounts_score_zero() -> None:
    reasons: list[dict] = []
    evidence: dict = {}
    contribution = _score_amount(50_000, reasons, evidence)
    assert contribution == 0
    assert reasons == []
    assert evidence["amount_band"] == "normal"


def test_score_amount_large_band_adds_20() -> None:
    reasons: list[dict] = []
    evidence: dict = {}
    contribution = _score_amount(2_500_000, reasons, evidence)
    assert contribution == 20
    assert reasons[0]["rule"] == "amount_large"
    assert evidence["amount_band"] == "large"


def test_score_amount_very_large_band_adds_40() -> None:
    reasons: list[dict] = []
    evidence: dict = {}
    contribution = _score_amount(8_000_000, reasons, evidence)
    assert contribution == 40
    assert reasons[0]["rule"] == "amount_very_large"
    assert evidence["amount_band"] == "very_large"


def test_score_amount_structuring_band_adds_30() -> None:
    """Sub-threshold detection: amounts in [900k, 1M) signal possible structuring."""
    reasons: list[dict] = []
    evidence: dict = {}
    contribution = _score_amount(950_000, reasons, evidence)
    assert contribution == 30
    assert reasons[0]["rule"] == "structuring_suspect"
    assert evidence["amount_band"] == "structuring_band"


# Channel risk --------------------------------------------------------------

def test_score_channel_npsb_is_zero_risk() -> None:
    reasons: list[dict] = []
    evidence: dict = {}
    assert _score_channel("NPSB", reasons, evidence) == 0
    assert reasons == []


def test_score_channel_cash_adds_15() -> None:
    reasons: list[dict] = []
    evidence: dict = {}
    contribution = _score_channel("CASH", reasons, evidence)
    assert contribution == 15
    assert reasons[0]["rule"] == "channel_cash_like"


def test_score_channel_mfs_adds_8() -> None:
    reasons: list[dict] = []
    evidence: dict = {}
    contribution = _score_channel("MFS_BKASH", reasons, evidence)
    assert contribution == 8
    assert reasons[0]["rule"] == "channel_mfs"


def test_score_channel_lowercase_normalised() -> None:
    reasons: list[dict] = []
    evidence: dict = {}
    assert _score_channel("cash", reasons, evidence) == 15


# Account-age signal --------------------------------------------------------

def test_account_age_days_parses_isoformat() -> None:
    ref = datetime(2026, 5, 5, tzinfo=UTC)
    assert _account_age_days({"account_open_date": "2026-05-01"}, reference=ref) == 4


def test_account_age_days_handles_naive_datetime() -> None:
    ref = datetime(2026, 5, 5, tzinfo=UTC)
    assert _account_age_days({"opened_at": "2026-04-01T00:00:00"}, reference=ref) == 34


def test_account_age_days_returns_none_for_missing_metadata() -> None:
    ref = datetime(2026, 5, 5, tzinfo=UTC)
    assert _account_age_days(None, reference=ref) is None
    assert _account_age_days({}, reference=ref) is None


def test_score_account_age_new_account_high_value_fires() -> None:
    ref = datetime(2026, 5, 5, tzinfo=UTC)
    metadata = {"account_open_date": (ref - timedelta(days=10)).date().isoformat()}
    reasons: list[dict] = []
    evidence: dict = {}
    contribution = _score_account_age(
        metadata, 2_000_000, reference=ref, reasons=reasons, evidence=evidence
    )
    assert contribution == 20
    assert reasons[0]["rule"] == "new_account_high_value"
    assert evidence["from_account_age_days"] == 10


def test_score_account_age_old_account_does_not_fire() -> None:
    ref = datetime(2026, 5, 5, tzinfo=UTC)
    metadata = {"account_open_date": (ref - timedelta(days=400)).date().isoformat()}
    reasons: list[dict] = []
    evidence: dict = {}
    contribution = _score_account_age(
        metadata, 2_000_000, reference=ref, reasons=reasons, evidence=evidence
    )
    assert contribution == 0
    assert reasons == []


def test_score_account_age_small_amount_does_not_fire() -> None:
    ref = datetime(2026, 5, 5, tzinfo=UTC)
    metadata = {"account_open_date": (ref - timedelta(days=5)).date().isoformat()}
    reasons: list[dict] = []
    evidence: dict = {}
    contribution = _score_account_age(
        metadata, 50_000, reference=ref, reasons=reasons, evidence=evidence
    )
    assert contribution == 0


# Entity-risk pull ----------------------------------------------------------

def _entity(*, risk_score: int | None, severity: str | None) -> SimpleNamespace:
    return SimpleNamespace(id=uuid.uuid4(), risk_score=risk_score, severity=severity)


def test_score_entity_risk_below_threshold_skipped() -> None:
    reasons: list[dict] = []
    evidence: dict = {}
    contribution = _score_entity_risk(
        entity=_entity(risk_score=30, severity="low"),
        side="from",
        reasons=reasons,
        evidence=evidence,
    )
    assert contribution == 0
    assert reasons == []


def test_score_entity_risk_high_severity_contributes() -> None:
    reasons: list[dict] = []
    evidence: dict = {}
    contribution = _score_entity_risk(
        entity=_entity(risk_score=85, severity="high"),
        side="from",
        reasons=reasons,
        evidence=evidence,
    )
    # 85 * 0.3 = 25.5 -> 26 (Python's banker's rounding); clamped to [10, 30]
    assert 10 <= contribution <= 30
    assert reasons[0]["rule"] == "from_entity_flagged"
    assert evidence["from_entity_risk_score"] == 85


def test_score_entity_risk_none_entity_returns_zero() -> None:
    contribution = _score_entity_risk(
        entity=None, side="to", reasons=[], evidence={}
    )
    assert contribution == 0


# Cross-bank match ----------------------------------------------------------

def _match(*, match_count: int, severity: str = "high", risk_score: int = 80) -> SimpleNamespace:
    return SimpleNamespace(
        id=uuid.uuid4(),
        match_count=match_count,
        severity=severity,
        risk_score=risk_score,
    )


def test_score_cross_bank_two_banks_adds_15() -> None:
    reasons: list[dict] = []
    evidence: dict = {}
    contribution = _score_cross_bank(
        match=_match(match_count=2), side="from", reasons=reasons, evidence=evidence
    )
    assert contribution == 15
    assert reasons[0]["rule"] == "from_cross_bank_flagged"


def test_score_cross_bank_three_or_more_banks_adds_25() -> None:
    reasons: list[dict] = []
    evidence: dict = {}
    contribution = _score_cross_bank(
        match=_match(match_count=4), side="to", reasons=reasons, evidence=evidence
    )
    assert contribution == 25
    assert reasons[0]["rule"] == "to_cross_bank_flagged"


def test_score_cross_bank_single_bank_does_not_fire() -> None:
    """A 'cross-bank' match with only one institution involved is not actually
    cross-bank — the matcher writes these only when match_count >= 2 anyway,
    but defend against a stale row."""
    contribution = _score_cross_bank(
        match=_match(match_count=1), side="from", reasons=[], evidence={}
    )
    assert contribution == 0


def test_score_cross_bank_no_match_returns_zero() -> None:
    contribution = _score_cross_bank(
        match=None, side="from", reasons=[], evidence={}
    )
    assert contribution == 0


# Confidence + normalisation helpers ---------------------------------------

def test_confidence_grows_with_signal_count() -> None:
    no_reasons = _confidence_from_signals([])
    one_reason = _confidence_from_signals([{"rule": "amount_large"}])
    five_reasons = _confidence_from_signals([{"rule": f"r{i}"} for i in range(5)])
    ten_reasons = _confidence_from_signals([{"rule": f"r{i}"} for i in range(10)])
    assert no_reasons == 0.5
    assert no_reasons < one_reason < five_reasons < ten_reasons
    assert ten_reasons <= 0.95  # capped


def test_normalize_for_lookup_strips_separators() -> None:
    assert _normalize_for_lookup("account", "1234-5678 9012") == "123456789012"


def test_normalize_for_lookup_handles_blank() -> None:
    assert _normalize_for_lookup("account", None) is None
    assert _normalize_for_lookup("account", "") is None


# End-to-end composition with cross-bank flag ------------------------------

def test_decision_bands_cover_full_score_range() -> None:
    """Trace every decision band so a future refactor can't silently drop
    a band without breaking this test."""
    bands_seen = {_decide(s) for s in (0, 30, 60, 80, 100)}
    assert bands_seen == {"approve", "review", "hold", "reject"}


# Latency percentile helper -------------------------------------------------

def test_percentile_empty_returns_zero() -> None:
    assert _percentile([], 50) == 0
    assert _percentile([], 99) == 0


def test_percentile_single_value() -> None:
    assert _percentile([42], 50) == 42
    assert _percentile([42], 99) == 42


def test_percentile_p50_matches_median_on_odd_set() -> None:
    assert _percentile([10, 20, 30, 40, 50], 50) == 30


def test_percentile_p95_extrapolates_high() -> None:
    """For 1..100 the linear-interpolated p95 should land near 95."""
    values = list(range(1, 101))
    assert _percentile(values, 95) == 95
    assert _percentile(values, 99) == 99
    assert _percentile(values, 50) == 50


def test_percentile_independent_of_input_order() -> None:
    assert _percentile([100, 50, 25, 75, 10], 50) == _percentile([10, 25, 50, 75, 100], 50)
