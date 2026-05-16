"""Coverage for the typed-recipient additions (migration 024)."""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.schemas.dissemination import (
    DisseminationCreate,
    RecipientAuthority,
    MlpaSection,
)


# RecipientAuthority literal -----------------------------------------------

def test_recipient_authority_accepts_all_thirteen_named_codes() -> None:
    expected = {
        "bangladesh_police_cid",
        "anti_corruption_commission",
        "national_board_of_revenue",
        "dept_narcotics_control",
        "bangladesh_securities_exchange_commission",
        "insurance_dev_regulatory_authority",
        "microcredit_regulatory_authority",
        "dgfi",
        "nsi",
        "court_or_investigating_officer",
        "foreign_fiu_egmont",
        "bb_internal_dept",
        "peer_reporting_org_circular_22",
    }
    # The Literal arguments are the source of truth — keep this in sync with
    # the migration 024 CHECK constraint.
    actual = set(RecipientAuthority.__args__)
    assert actual == expected, f"missing or extra codes: {actual ^ expected}"


def test_recipient_authority_rejects_unknown_value() -> None:
    with pytest.raises(ValidationError):
        DisseminationCreate(
            recipient_agency="National Board of Revenue",
            recipient_type="regulator",
            recipient_authority="bangladesh_central_bank",  # not in the enum
            subject_summary="Test",
        )


def test_recipient_authority_optional_for_back_compat() -> None:
    # Legacy callers haven't been migrated and submit only the old fields.
    payload = DisseminationCreate(
        recipient_agency="National Board of Revenue",
        recipient_type="regulator",
        subject_summary="Customs anomaly referral.",
    )
    assert payload.recipient_authority is None
    assert payload.mlpa_section is None
    assert payload.circular_22_exchange is False


# MlpaSection literal -----------------------------------------------------

def test_mlpa_section_covers_23_1_a_through_g_plus_24_3_and_24_4() -> None:
    expected = {
        "mlpa_23_1_a",
        "mlpa_23_1_b",
        "mlpa_23_1_c",
        "mlpa_23_1_d",
        "mlpa_23_1_e",
        "mlpa_23_1_f",
        "mlpa_23_1_g",
        "mlpa_24_3",
        "mlpa_24_4",
        "ata_15_1_a",
        "ata_15_1_b",
        "ata_15_1_c",
        "ata_15_1_d",
        "ata_15_1_e",
        "ata_15_1_f",
        "ata_15_1_g",
    }
    actual = set(MlpaSection.__args__)
    assert actual == expected


def test_circular_22_exchange_to_peer_reporting_org() -> None:
    # The Circular 22 channel pairs `peer_reporting_org_circular_22` recipient
    # with `mlpa_23_1_d` enabling clause and circular_22_exchange=true.
    payload = DisseminationCreate(
        recipient_agency="BRAC Bank PLC",
        recipient_type="other",
        recipient_authority="peer_reporting_org_circular_22",
        mlpa_section="mlpa_23_1_d",
        circular_22_exchange=True,
        subject_summary="Customer KYC overlap exchange under Circular 22.",
    )
    assert payload.recipient_authority == "peer_reporting_org_circular_22"
    assert payload.mlpa_section == "mlpa_23_1_d"
    assert payload.circular_22_exchange is True


def test_foreign_fiu_dissemination_under_24_4() -> None:
    # Cross-border exchange under MLPA §24(4) (contract/agreement based).
    payload = DisseminationCreate(
        recipient_agency="FinCEN — US Treasury",
        recipient_type="foreign_fiu",
        recipient_authority="foreign_fiu_egmont",
        mlpa_section="mlpa_24_4",
        subject_summary="Egmont request — TBML investigation.",
    )
    assert payload.recipient_authority == "foreign_fiu_egmont"
    assert payload.mlpa_section == "mlpa_24_4"
    assert payload.circular_22_exchange is False
