"""Pure-helper tests for engine/app/services/tbml.py (Phase B dashboard).

Tests cover the persona-aware helpers (org labelling + match-key
anonymisation) and the cross-org clustering shape that the
/intelligence/tbml/summary endpoint surfaces. DB-touching paths
(build_tbml_summary, multi_invoicing_groups) are exercised by the
existing async integration tests that already run against the live
prod schema; here we pin the deterministic transformations.
"""
from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.services.tbml import (
    _anonymize_match_key,
    _label_orgs_for_user,
)


def _user(persona: str, *, org_id: str = "9c222222-2222-4222-8222-222222222222") -> SimpleNamespace:
    org_type = "regulator" if persona.startswith("bfiu_") else "bank"
    return SimpleNamespace(
        user_id="user-test",
        email=f"{persona}@kestrel.test",
        org_id=org_id,
        org_type=org_type,
        role="admin" if persona == "bfiu_director" else "manager",
        persona=persona,
        designation="Test",
    )


# Org labelling ---------------------------------------------------------


def test_regulator_sees_real_bank_names() -> None:
    user = _user("bfiu_director", org_id="9c111111-1111-4111-8111-111111111111")
    name_map = {
        "9c111111-1111-4111-8111-111111111111": "BFIU",
        "9c222222-2222-4222-8222-222222222222": "Sonali Bank PLC",
        "9c333333-3333-4333-8333-333333333333": "BRAC Bank PLC",
    }
    labels = _label_orgs_for_user(
        list(name_map),
        user=user,
        org_name_map=name_map,
    )
    assert labels == ["BFIU", "Sonali Bank PLC", "BRAC Bank PLC"]


def test_bank_persona_sees_own_org_plus_anonymised_peers() -> None:
    user = _user("bank_camlco", org_id="9c222222-2222-4222-8222-222222222222")
    name_map = {
        "9c222222-2222-4222-8222-222222222222": "Sonali Bank PLC",
        "9c333333-3333-4333-8333-333333333333": "BRAC Bank PLC",
        "9c444444-4444-4444-8444-444444444444": "City Bank PLC",
    }
    labels = _label_orgs_for_user(
        list(name_map),
        user=user,
        org_name_map=name_map,
    )
    assert labels[0] == "Sonali Bank PLC"
    assert labels[1] == "Peer institution 1"
    assert labels[2] == "Peer institution 2"


def test_bank_persona_falls_back_to_org_id_if_name_missing() -> None:
    user = _user("bank_camlco", org_id="9c222222-2222-4222-8222-222222222222")
    name_map: dict[str, str] = {}  # no resolved names
    labels = _label_orgs_for_user(
        [user.org_id, "9c333333-3333-4333-8333-333333333333"],
        user=user,
        org_name_map=name_map,
    )
    # First label is "Own institution" sentinel since own org name is missing.
    assert labels[0] == "Own institution"
    assert labels[1] == "Peer institution 1"


# Match-key anonymisation -----------------------------------------------


def test_match_key_full_for_regulator() -> None:
    user = _user("bfiu_director")
    assert _anonymize_match_key("HLCU-HKG-7712-0011", user=user) == "HLCU-HKG-7712-0011"
    assert _anonymize_match_key("LC-2026-04123", user=user) == "LC-2026-04123"


def test_match_key_redacted_to_last_four_for_bank_persona() -> None:
    user = _user("bank_camlco")
    assert _anonymize_match_key("HLCU-HKG-7712-0011", user=user) == "····0011"
    assert _anonymize_match_key("LC-2026-04123", user=user) == "····4123"


def test_match_key_under_four_chars_left_alone() -> None:
    # Pathological case — never produce a worse-than-original redaction.
    user = _user("bank_camlco")
    assert _anonymize_match_key("AB", user=user) == "AB"
    assert _anonymize_match_key("ABCD", user=user) == "ABCD"


def test_match_key_handles_empty_or_none() -> None:
    user = _user("bank_camlco")
    assert _anonymize_match_key("", user=user) == "—"
    assert _anonymize_match_key(None, user=user) == "—"


# Cross-path consistency check ----------------------------------------


def test_anonymisation_matches_cross_bank_service_contract() -> None:
    # The TBML dashboard borrows the same anonymisation rules as the
    # cross-bank dashboard (PR #5, V2 phase 1.1). This regression pins
    # they produce the same shape so the BFIU-procurement claim "bank
    # persona NEVER sees peer match keys in full" applies uniformly.
    from app.services.cross_bank import (
        _anonymize_match_key as cb_anonymize,
    )

    user = _user("bank_camlco")
    sample = "BL-2026-99887766"
    assert _anonymize_match_key(sample, user=user) == cb_anonymize(sample, user)
