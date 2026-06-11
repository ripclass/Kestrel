"""Persona-aware org labelling on the investigation surfaces.

/intelligence/matches, /investigate search, and the entity dossier all
serialise reporting_orgs / involved_orgs through investigation._label_orgs.
The engine session bypasses RLS, so the org-name map always resolves every
organisation's real name — these tests pin that the helper (not SQL) is what
keeps peer-bank names away from bank personas, mirroring the cross_bank
service invariant.
"""
from __future__ import annotations

import uuid
from types import SimpleNamespace

from app.services.investigation import _is_regulator, _label_orgs


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
    assert _is_regulator(_user(org_type="REGULATOR")) is True


def test_regulator_sees_real_names() -> None:
    bfiu = _user(org_type="regulator")
    org_a, org_b = str(uuid.uuid4()), str(uuid.uuid4())
    name_map = {org_a: "BRAC Bank PLC", org_b: "Sonali Bank PLC"}
    assert _label_orgs([org_a, org_b], bfiu, name_map) == ["BRAC Bank PLC", "Sonali Bank PLC"]


def test_bank_sees_own_name_and_anonymised_peers() -> None:
    own_org_id = str(uuid.uuid4())
    bank = _user(org_type="bank", org_id=own_org_id)
    peer_a, peer_b = str(uuid.uuid4()), str(uuid.uuid4())
    name_map = {own_org_id: "Sonali Bank PLC", peer_a: "BRAC Bank PLC", peer_b: "City Bank PLC"}
    labels = _label_orgs([own_org_id, peer_a, peer_b], bank, name_map)
    assert labels == ["Sonali Bank PLC", "Peer institution 1", "Peer institution 2"]
    assert "BRAC Bank PLC" not in labels
    assert "City Bank PLC" not in labels


def test_bank_with_only_peer_orgs_anonymises_all() -> None:
    bank = _user(org_type="bank", org_id=str(uuid.uuid4()))
    peers = [str(uuid.uuid4()) for _ in range(3)]
    name_map = {peers[0]: "BRAC", peers[1]: "City", peers[2]: "Islami"}
    labels = _label_orgs(peers, bank, name_map)
    assert labels == ["Peer institution 1", "Peer institution 2", "Peer institution 3"]


def test_bank_peer_names_never_leak_even_when_name_map_resolves_everything() -> None:
    # The regression this file exists for: the engine bypasses RLS, so the
    # name map contains EVERY org's real name. A bank caller must still get
    # anonymised peers.
    own_org_id = str(uuid.uuid4())
    bank = _user(org_type="bank", org_id=own_org_id)
    all_orgs = [own_org_id, *(str(uuid.uuid4()) for _ in range(4))]
    name_map = {
        all_orgs[0]: "Sonali Bank PLC",
        all_orgs[1]: "BRAC Bank PLC",
        all_orgs[2]: "City Bank PLC",
        all_orgs[3]: "Dutch-Bangla Bank PLC",
        all_orgs[4]: "Islami Bank Bangladesh PLC",
    }
    labels = _label_orgs(all_orgs, bank, name_map)
    assert labels[0] == "Sonali Bank PLC"
    assert labels[1:] == [f"Peer institution {i}" for i in range(1, 5)]
    for peer_name in ("BRAC Bank PLC", "City Bank PLC", "Dutch-Bangla Bank PLC", "Islami Bank Bangladesh PLC"):
        assert peer_name not in labels


def test_mfs_org_type_is_treated_as_non_regulator() -> None:
    mfs = _user(org_type="mfs")
    peer = str(uuid.uuid4())
    labels = _label_orgs([peer], mfs, {peer: "Sonali Bank PLC"})
    assert labels == ["Peer institution 1"]


def test_bank_own_org_missing_from_name_map_falls_back() -> None:
    own_org_id = str(uuid.uuid4())
    bank = _user(org_type="bank", org_id=own_org_id)
    assert _label_orgs([own_org_id], bank, {}) == ["Your institution"]


def test_uuid_inputs_are_normalised_to_strings() -> None:
    bfiu = _user(org_type="regulator")
    org_a = uuid.uuid4()
    name_map = {str(org_a): "BRAC Bank PLC"}
    assert _label_orgs([org_a], bfiu, name_map) == ["BRAC Bank PLC"]


def test_empty_and_none_inputs() -> None:
    bank = _user(org_type="bank")
    assert _label_orgs(None, bank, {}) == []
    assert _label_orgs([], bank, {}) == []
