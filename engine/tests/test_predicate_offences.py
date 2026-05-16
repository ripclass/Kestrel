"""Coverage for MLPA 2012 §2(cc) predicate offence wiring (migration 025)."""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.schemas.case import CaseProposeRequest
from app.schemas.dissemination import DisseminationCreate
from app.schemas.predicate_offence import PREDICATE_OFFENCES, PredicateOffence
from app.schemas.str_report import STRDraftUpsert


def test_28_predicate_offence_codes_present() -> None:
    expected = {
        "corruption_and_bribery",
        "counterfeiting_currency",
        "counterfeiting_deeds_and_documents",
        "extortion",
        "fraud",
        "forgery",
        "illegal_trade_firearms",
        "illegal_trade_narcotics",
        "illegal_trade_stolen_goods",
        "kidnapping_restraint_hostage",
        "murder_grievous_injury",
        "trafficking_women_children",
        "black_marketing",
        "smuggling_currency",
        "theft_robbery_dacoity_piracy_hijacking",
        "human_trafficking",
        "dowry",
        "smuggling_customs_excise",
        "tax_related_offences",
        "infringement_intellectual_property",
        "terrorism_or_terrorist_financing",
        "adulteration_title_infringement",
        "environmental_offences",
        "sexual_exploitation",
        "insider_trading_market_manipulation",
        "organized_crime",
        "racketeering",
        "other_bb_gazetted",
    }
    actual = set(PredicateOffence.__args__)
    assert actual == expected, f"missing or extra codes: {actual ^ expected}"
    assert len(PREDICATE_OFFENCES) == 28
    assert set(PREDICATE_OFFENCES) == expected


def test_predicate_offence_optional_on_dissemination() -> None:
    payload = DisseminationCreate(
        recipient_agency="National Board of Revenue",
        recipient_type="regulator",
        subject_summary="Routine referral.",
    )
    assert payload.predicate_offences == []


def test_predicate_offence_accepted_on_dissemination() -> None:
    payload = DisseminationCreate(
        recipient_agency="National Board of Revenue",
        recipient_type="regulator",
        recipient_authority="national_board_of_revenue",
        mlpa_section="mlpa_24_3",
        predicate_offences=["smuggling_customs_excise", "tax_related_offences"],
        subject_summary="TBML referral citing customs + tax predicates.",
    )
    assert payload.predicate_offences == ["smuggling_customs_excise", "tax_related_offences"]


def test_predicate_offence_rejects_unknown_value() -> None:
    with pytest.raises(ValidationError):
        DisseminationCreate(
            recipient_agency="NBR",
            recipient_type="regulator",
            predicate_offences=["money_laundering_self"],  # not in §2(cc)
            subject_summary="Test",
        )


def test_predicate_offence_on_case_propose() -> None:
    request = CaseProposeRequest(
        title="TBML cluster",
        summary="Multi-bank invoice mismatch.",
        severity="high",
        predicate_offences=["smuggling_customs_excise"],
    )
    assert request.predicate_offences == ["smuggling_customs_excise"]


def test_predicate_offence_on_str_draft_upsert() -> None:
    draft = STRDraftUpsert(
        subject_account="1234567890",
        subject_bank="Sonali Bank",
        narrative="Suspect TBML pattern observed.",
        predicate_offences=["smuggling_customs_excise", "tax_related_offences"],
    )
    assert draft.predicate_offences == ["smuggling_customs_excise", "tax_related_offences"]


def test_terrorism_predicate_pairs_naturally_with_ata_clause() -> None:
    # A terrorism-financing dissemination cites both §2(cc)(21) and an ATA
    # mirror enabling clause. Nothing enforces this in code yet but the
    # combination must validate without complaint.
    payload = DisseminationCreate(
        recipient_agency="DGFI",
        recipient_type="law_enforcement",
        recipient_authority="dgfi",
        mlpa_section="ata_15_1_a",
        predicate_offences=["terrorism_or_terrorist_financing"],
        subject_summary="TF referral to DGFI under ATA §15(1)(a).",
    )
    assert payload.predicate_offences == ["terrorism_or_terrorist_financing"]
    assert payload.mlpa_section == "ata_15_1_a"
