"""Pure-helper coverage for the screening service (V2 phase 4).

The async ``screen_entity`` path needs a real Postgres session because the
fuzzy search uses pg_trgm. This file pins the deterministic pieces — name
normalisation, weighted score composition, identifier matching, the
date/nationality matchers, and the realtime-scoring helper that converts
matches into reason rows.
"""
from __future__ import annotations

import uuid
from datetime import date
from types import SimpleNamespace

from app.services.realtime_scoring import (
    _SANCTIONS_HIT_POINTS,
    _SANCTIONS_HIT_THRESHOLD,
    _score_sanctions,
)
from app.services.screening import (
    ScreeningMatch,
    alias_similarity,
    best_screening_score,
    compose_match_score,
    date_match,
    identifier_match,
    nationality_match,
    normalize_identifier,
    normalize_name,
    normalize_nationality,
    parse_screening_date,
)


# Name normalisation ---------------------------------------------------------

def test_normalize_name_handles_diacritics() -> None:
    assert normalize_name("Mohámmád  Karím") == "mohammad karim"
    assert normalize_name("José García") == "jose garcia"


def test_normalize_name_collapses_whitespace() -> None:
    assert normalize_name("  john\t doe ") == "john doe"


def test_normalize_name_handles_blank() -> None:
    assert normalize_name(None) == ""
    assert normalize_name("") == ""
    assert normalize_name("   ") == ""


def test_normalize_nationality_uppercase_and_strips() -> None:
    assert normalize_nationality("bd") == "BD"
    assert normalize_nationality("Bangladesh") == "BANGLADESH"
    assert normalize_nationality("U.S.A.") == "USA"


def test_normalize_identifier_strips_separators() -> None:
    assert normalize_identifier("BR-99-12345") == "BR9912345"
    assert normalize_identifier("a 1234 5678") == "A12345678"


# Date / nationality / identifier matchers ----------------------------------

def test_date_match_exact_only() -> None:
    assert date_match(date(1980, 1, 1), date(1980, 1, 1)) is True
    assert date_match(date(1980, 1, 1), date(1980, 1, 2)) is False
    assert date_match(None, date(1980, 1, 1)) is False
    assert date_match(date(1980, 1, 1), None) is False


def test_nationality_match_iso_normalisation() -> None:
    assert nationality_match("BD", "BD") is True
    # Prefix match catches the common US/USA pattern and avoids false negatives
    # when one feed uses ISO2 and another ISO3 for the same country.
    assert nationality_match("US", "USA") is True
    # BD and BGD share neither a textual prefix nor an exact value, so the
    # default matcher returns False — the screening service still scores name
    # + DOB + identifier independently, so this rarely costs us a hit.
    assert nationality_match("BD", "BGD") is False
    assert nationality_match("Bangladesh", "BD") is False
    assert nationality_match("US", "BD") is False
    assert nationality_match(None, "BD") is False


def test_identifier_match_handles_string_and_list_targets() -> None:
    assert (
        identifier_match(
            candidate_nid="1979314001234",
            candidate_passport=None,
            entry_identifiers={"nid": ["1979314001234"]},
        )
        is True
    )
    assert (
        identifier_match(
            candidate_nid=None,
            candidate_passport="BR9912345",
            entry_identifiers={"passport": "BR-99-12345"},
        )
        is True
    )
    assert (
        identifier_match(
            candidate_nid="1979314001234",
            candidate_passport="BR9912345",
            entry_identifiers={"passport": "OTHER", "nid": ["OTHER"]},
        )
        is False
    )


def test_identifier_match_inspects_docs_bag() -> None:
    """Some adapters store IDs under a nested 'docs' bag."""
    assert (
        identifier_match(
            candidate_nid="1234567890",
            candidate_passport=None,
            entry_identifiers={
                "docs": [{"type": "national-id", "number": "1234567890"}]
            },
        )
        is True
    )


# Score composition ---------------------------------------------------------

def test_compose_match_score_only_name_below_minimum() -> None:
    """A 0.5 name similarity alone lands at 0.2 (under the default 0.7)."""
    score, reasons = compose_match_score(
        name_similarity=0.5, dob_hit=False, nationality_hit=False, identifier_hit=False
    )
    assert score == 0.2
    assert len(reasons) == 1
    assert "fuzzy match similarity" in reasons[0]


def test_compose_match_score_full_house_caps_at_one() -> None:
    score, reasons = compose_match_score(
        name_similarity=1.0, dob_hit=True, nationality_hit=True, identifier_hit=True
    )
    assert score == 1.0
    assert len(reasons) == 4


def test_compose_match_score_strong_name_plus_dob_clears_default_threshold() -> None:
    """Realistic case: 0.9 name + DOB = 0.66 — just under the default 0.7. Adding
    nationality bumps to 0.86, comfortably above."""
    score_no_nat, _ = compose_match_score(
        name_similarity=0.9, dob_hit=True, nationality_hit=False, identifier_hit=False
    )
    score_with_nat, _ = compose_match_score(
        name_similarity=0.9, dob_hit=True, nationality_hit=True, identifier_hit=False
    )
    assert score_no_nat == 0.66
    assert score_with_nat == 0.86


def test_compose_match_score_clamps_negative_similarity() -> None:
    score, _ = compose_match_score(
        name_similarity=-0.5, dob_hit=True, nationality_hit=False, identifier_hit=False
    )
    # Negative similarity clamps to 0; only DOB contributes.
    assert score == 0.3


# Alias similarity ----------------------------------------------------------

def test_alias_similarity_jaccard() -> None:
    aliases = ["Mohammad Hossain", "Hossain Karim"]
    # Candidate shares 1 token with the first alias; alias has 2 tokens; candidate has 2.
    # Jaccard = 1 / 3 ≈ 0.333.
    sim = alias_similarity("Mohammad Karim", aliases)
    assert 0.3 < sim < 0.4


def test_alias_similarity_no_aliases_returns_zero() -> None:
    assert alias_similarity("Mohammad Karim", []) == 0.0


def test_alias_similarity_blank_candidate_returns_zero() -> None:
    assert alias_similarity("   ", ["Some Name"]) == 0.0


# parse_screening_date ------------------------------------------------------

def test_parse_screening_date_iso() -> None:
    assert parse_screening_date("1980-01-01") == date(1980, 1, 1)
    assert parse_screening_date("1980-01-01T12:00:00Z") == date(1980, 1, 1)


def test_parse_screening_date_handles_bad_input() -> None:
    assert parse_screening_date(None) is None
    assert parse_screening_date("") is None
    assert parse_screening_date("not a date") is None
    assert parse_screening_date(12345) is None


# best_screening_score ------------------------------------------------------

def _match(score: float) -> ScreeningMatch:
    return ScreeningMatch(
        list_source="OFAC",
        list_version="v",
        entry_id=str(uuid.uuid4()),
        entry_type="individual",
        matched_name="Test",
        matched_aliases=[],
        matched_entry={},
        match_score=score,
        match_reasons=[],
    )


def test_best_screening_score_picks_highest() -> None:
    assert best_screening_score([_match(0.5), _match(0.85), _match(0.6)]) == 0.85


def test_best_screening_score_empty_returns_zero() -> None:
    assert best_screening_score([]) == 0.0


# Realtime _score_sanctions integration -------------------------------------

def test_score_sanctions_no_matches_contributes_zero() -> None:
    reasons: list[dict] = []
    evidence: dict = {}
    contribution = _score_sanctions(matches=[], side="from", reasons=reasons, evidence=evidence)
    assert contribution == 0
    assert reasons == []
    assert "from_sanctions_hit" not in evidence


def test_score_sanctions_one_match_adds_50() -> None:
    reasons: list[dict] = []
    evidence: dict = {}
    contribution = _score_sanctions(
        matches=[_match(0.85)], side="from", reasons=reasons, evidence=evidence
    )
    assert contribution == _SANCTIONS_HIT_POINTS
    assert reasons[0]["rule"] == "from_sanctions_hit"
    assert evidence["from_sanctions_hit"]["match_score"] == 0.85


def test_score_sanctions_uses_top_match_only() -> None:
    """Multiple matches still emit one reason row; remaining hits are noted in
    detail.additional_hits."""
    matches = [_match(0.95), _match(0.8), _match(0.75)]
    reasons: list[dict] = []
    contribution = _score_sanctions(
        matches=matches, side="to", reasons=reasons, evidence={}
    )
    assert contribution == _SANCTIONS_HIT_POINTS
    assert reasons[0]["rule"] == "to_sanctions_hit"
    assert reasons[0]["detail"]["match_score"] == 0.95
    assert reasons[0]["detail"]["additional_hits"] == 2


def test_sanctions_threshold_constant_matches_default() -> None:
    """The realtime sanctions threshold should equal the screening service default."""
    assert _SANCTIONS_HIT_THRESHOLD == 0.7


def test_screening_match_serializes_via_asdict_not_dunder_dict() -> None:
    """Regression: ScreeningMatch is a slots=True dataclass, so it has no
    __dict__. The /screening/entity router must serialise matches via
    dataclasses.asdict — `ScreeningMatchModel(**match.__dict__)` raised
    AttributeError and 500'd on every actual hit (zero-match screens slipped
    through because the list comprehension never ran)."""
    from dataclasses import asdict

    from app.schemas.screening import ScreeningMatchModel

    match = ScreeningMatch(
        list_source="BIS",
        list_version="2026-06-12",
        entry_id=str(uuid.uuid4()),
        entry_type="entity",
        matched_name="Meridian Precision Instruments Co",
        matched_aliases=["Meridian Precision", "MPI Co"],
        matched_entry={"reason": "BIS Entity List"},
        match_score=0.82,
        match_reasons=["name 0.95"],
    )

    # slots dataclass → no __dict__ (the old code path).
    assert not hasattr(match, "__dict__")

    payload = asdict(match)
    assert set(payload) == set(ScreeningMatchModel.model_fields)
    model = ScreeningMatchModel(**payload)
    assert model.list_source == "BIS"
    assert model.match_score == 0.82
    assert model.matched_aliases == ["Meridian Precision", "MPI Co"]


def test_screen_entity_fails_closed_on_db_error() -> None:
    """A DB error on the watchlist query must raise ScreeningUnavailableError,
    not return [] (which reads as a clean screen and silently feeds a false
    all-clear into realtime approve / KYC low-risk / the agent tool)."""
    import asyncio

    from app.services.screening import (
        ScreeningRequest,
        ScreeningUnavailableError,
        screen_entity,
    )

    class _BoomSession:
        async def execute(self, _stmt):
            raise RuntimeError("connection reset by peer")

    async def _run():
        await screen_entity(
            _BoomSession(), request=ScreeningRequest(name="Some Person")
        )

    try:
        asyncio.run(_run())
    except ScreeningUnavailableError:
        return  # expected
    raise AssertionError("screen_entity should have raised ScreeningUnavailableError")
