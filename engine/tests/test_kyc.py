"""Pure-helper coverage for the KYC service (V2 phase 5).

The async paths (onboard_customer, list_customers, …) need a real Postgres
session because they touch customers + screening + audit_log. This file
pins the deterministic pieces — risk-band decision logic, score
composition across primary + beneficial owners, the previous-top-score
detection used by the re-screening Beat task, and the screening-result
serialisation.
"""
from __future__ import annotations

import uuid

from app.services.kyc import (
    _DIRECT_SANCTIONS_THRESHOLD,
    _RISK_BAND_HIGH_MAX,
    _RISK_BAND_LOW_MAX,
    _RISK_BAND_MEDIUM_MAX,
    _compose_risk_score,
    _decide_risk,
    _matches_to_payload,
)
from app.services.screening import ScreeningMatch
from app.tasks.kyc_tasks import _previous_top_primary_score


def _match(score: float, list_source: str = "OFAC") -> ScreeningMatch:
    return ScreeningMatch(
        list_source=list_source,
        list_version="v",
        entry_id=str(uuid.uuid4()),
        entry_type="individual",
        matched_name="Test",
        matched_aliases=[],
        matched_entry={},
        match_score=score,
        match_reasons=[],
    )


# Risk-band decision -------------------------------------------------------

def test_decide_risk_low_band_approves() -> None:
    assert _decide_risk(score=0, has_direct_hit=False) == ("low", "approved")
    assert _decide_risk(score=_RISK_BAND_LOW_MAX - 1, has_direct_hit=False) == ("low", "approved")


def test_decide_risk_medium_band_approves() -> None:
    assert _decide_risk(score=_RISK_BAND_LOW_MAX, has_direct_hit=False) == ("medium", "approved")
    assert _decide_risk(score=_RISK_BAND_MEDIUM_MAX - 1, has_direct_hit=False) == ("medium", "approved")


def test_decide_risk_high_band_routes_to_review() -> None:
    assert _decide_risk(score=_RISK_BAND_MEDIUM_MAX, has_direct_hit=False) == ("high", "review")
    assert _decide_risk(score=_RISK_BAND_HIGH_MAX - 1, has_direct_hit=False) == ("high", "review")


def test_decide_risk_above_high_threshold_declines() -> None:
    assert _decide_risk(score=_RISK_BAND_HIGH_MAX, has_direct_hit=False) == ("declined", "declined")
    assert _decide_risk(score=100, has_direct_hit=False) == ("declined", "declined")


def test_decide_risk_direct_hit_overrides_low_score() -> None:
    """A direct sanctions hit forces decline even if the composed score is low.

    This guards against the case where a fuzzy primary match comes in below
    the high-band threshold but is still a real hit — onboarding a sanctioned
    party at any composed score is itself a regulatory violation.
    """
    assert _decide_risk(score=10, has_direct_hit=True) == ("declined", "declined")


# Risk-score composition ---------------------------------------------------

def test_compose_risk_score_no_matches_returns_zero() -> None:
    assert _compose_risk_score(primary_matches=[], bo_matches_by_name={}) == 0


def test_compose_risk_score_strong_primary_lands_above_threshold() -> None:
    """A 0.95 primary hit alone should land in the decline band (>= 80)."""
    score = _compose_risk_score(primary_matches=[_match(0.95)], bo_matches_by_name={})
    assert score >= _RISK_BAND_HIGH_MAX
    assert score <= 100


def test_compose_risk_score_borderline_primary_lands_in_high_band() -> None:
    """A 0.7 primary hit (the screening floor) should land in the high band."""
    score = _compose_risk_score(primary_matches=[_match(_DIRECT_SANCTIONS_THRESHOLD)], bo_matches_by_name={})
    assert _RISK_BAND_MEDIUM_MAX <= score < _RISK_BAND_HIGH_MAX


def test_compose_risk_score_beneficial_owner_only_elevates_to_medium() -> None:
    """A flagged beneficial owner doesn't disqualify but does elevate risk."""
    score = _compose_risk_score(
        primary_matches=[],
        bo_matches_by_name={"Tariq Rahman": [_match(0.92)]},
    )
    assert 0 < score <= _RISK_BAND_HIGH_MAX  # not auto-declined
    # A single BO contributes 10 points, capped per the helper.
    assert score == 10


def test_compose_risk_score_multiple_bo_hits_stack() -> None:
    score = _compose_risk_score(
        primary_matches=[],
        bo_matches_by_name={
            "A": [_match(0.92)],
            "B": [_match(0.88)],
        },
    )
    assert score == 20


def test_compose_risk_score_clamps_at_100() -> None:
    score = _compose_risk_score(
        primary_matches=[_match(0.99)],
        bo_matches_by_name={
            "A": [_match(0.95)],
            "B": [_match(0.95)],
            "C": [_match(0.95)],
            "D": [_match(0.95)],
        },
    )
    assert score == 100


# Match payload serialisation ----------------------------------------------

def test_matches_to_payload_round_trips_fields() -> None:
    matches = [
        ScreeningMatch(
            list_source="OFAC",
            list_version="v1",
            entry_id="abc",
            entry_type="individual",
            matched_name="Mohammad Karim",
            matched_aliases=["M. Karim"],
            matched_entry={},
            match_score=0.94,
            match_reasons=["primary_name fuzzy match similarity=0.99", "date_of_birth exact match"],
        )
    ]
    payload = _matches_to_payload(matches)
    assert payload[0]["list_source"] == "OFAC"
    assert payload[0]["match_score"] == 0.94
    assert payload[0]["matched_aliases"] == ["M. Karim"]
    assert payload[0]["match_reasons"] == [
        "primary_name fuzzy match similarity=0.99",
        "date_of_birth exact match",
    ]


def test_matches_to_payload_empty_input() -> None:
    assert _matches_to_payload([]) == []


# Beat task — _previous_top_primary_score ----------------------------------

def test_previous_top_primary_score_extracts_max() -> None:
    screening_results = {
        "primary": [
            {"match_score": 0.4},
            {"match_score": 0.85},
            {"match_score": 0.7},
        ],
    }
    assert _previous_top_primary_score(screening_results) == 0.85


def test_previous_top_primary_score_handles_empty() -> None:
    assert _previous_top_primary_score({}) == 0.0
    assert _previous_top_primary_score({"primary": []}) == 0.0
    assert _previous_top_primary_score(None) == 0.0


def test_previous_top_primary_score_skips_non_dict_items() -> None:
    """Defensive: stored JSON might have stale shapes."""
    screening_results = {"primary": ["bad", {"match_score": 0.5}, None]}
    assert _previous_top_primary_score(screening_results) == 0.5


def test_previous_top_primary_score_handles_non_numeric() -> None:
    screening_results = {
        "primary": [
            {"match_score": "not a number"},
            {"match_score": 0.6},
        ],
    }
    assert _previous_top_primary_score(screening_results) == 0.6
