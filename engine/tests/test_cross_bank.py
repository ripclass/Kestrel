"""Pure-helper coverage for the cross-bank intelligence service.

The full async paths (summarize_cross_bank, list_cross_bank_matches,
cross_bank_heatmap) need a real Postgres session because Match.involved_org_ids
is ARRAY(UUID). This file pins the persona-aware helpers — anonymisation
and label rewriting — which is where the "is the bank persona accidentally
seeing peer-bank names" risk lives.
"""
from __future__ import annotations

import uuid
from types import SimpleNamespace

from app.services.cross_bank import (
    _anonymize_match_key,
    _candidate_org_ids,
    _is_regulator,
    _label_orgs_for_user,
)


def _user(*, org_type: str, org_id: str | None = None) -> SimpleNamespace:
    return SimpleNamespace(
        user_id=str(uuid.uuid4()),
        email="user@example.test",
        org_id=org_id or str(uuid.uuid4()),
        org_type=org_type,
        role="analyst",
        persona="bfiu_analyst" if org_type == "regulator" else "bank_camlco",
        designation=None,
    )


def test_is_regulator_distinguishes_bank_from_regulator() -> None:
    assert _is_regulator(_user(org_type="regulator")) is True
    assert _is_regulator(_user(org_type="bank")) is False
    assert _is_regulator(_user(org_type="mfs")) is False
    assert _is_regulator(_user(org_type="REGULATOR")) is True  # case-insensitive


def test_candidate_org_ids_filters_falsy_and_stringifies() -> None:
    a, b = uuid.uuid4(), uuid.uuid4()
    assert _candidate_org_ids([a, b, None, ""]) == [str(a), str(b)]
    assert _candidate_org_ids(None) == []


def test_label_orgs_for_user_regulator_sees_real_names() -> None:
    bfiu = _user(org_type="regulator")
    org_a, org_b = str(uuid.uuid4()), str(uuid.uuid4())
    name_map = {org_a: "BRAC Bank PLC", org_b: "Sonali Bank PLC"}
    labels = _label_orgs_for_user([org_a, org_b], bfiu, name_map)
    assert labels == ["BRAC Bank PLC", "Sonali Bank PLC"]


def test_label_orgs_for_user_bank_sees_own_name_then_anon_peers() -> None:
    own_org_id = str(uuid.uuid4())
    bank = _user(org_type="bank", org_id=own_org_id)
    peer_a, peer_b = str(uuid.uuid4()), str(uuid.uuid4())
    name_map = {own_org_id: "Sonali Bank PLC", peer_a: "BRAC Bank PLC", peer_b: "City Bank PLC"}
    labels = _label_orgs_for_user([own_org_id, peer_a, peer_b], bank, name_map)
    assert labels == ["Sonali Bank PLC", "Peer institution 1", "Peer institution 2"]
    # Critical invariant: peer bank names must NEVER appear in the labels for a bank user
    assert "BRAC Bank PLC" not in labels
    assert "City Bank PLC" not in labels


def test_label_orgs_for_user_bank_with_only_peers_anonymises_all() -> None:
    own_org_id = str(uuid.uuid4())
    bank = _user(org_type="bank", org_id=own_org_id)
    peer_a, peer_b, peer_c = str(uuid.uuid4()), str(uuid.uuid4()), str(uuid.uuid4())
    name_map = {peer_a: "BRAC", peer_b: "City", peer_c: "Islami"}
    labels = _label_orgs_for_user([peer_a, peer_b, peer_c], bank, name_map)
    assert labels == ["Peer institution 1", "Peer institution 2", "Peer institution 3"]


def test_anonymize_match_key_regulator_sees_full_key() -> None:
    bfiu = _user(org_type="regulator")
    assert _anonymize_match_key("01711234567", bfiu) == "01711234567"


def test_anonymize_match_key_bank_redacts_to_last_four() -> None:
    bank = _user(org_type="bank")
    assert _anonymize_match_key("01711234567", bank) == "····4567"


def test_anonymize_match_key_handles_short_inputs() -> None:
    bank = _user(org_type="bank")
    assert _anonymize_match_key("abc", bank) == "····"
    assert _anonymize_match_key("", bank) == ""
