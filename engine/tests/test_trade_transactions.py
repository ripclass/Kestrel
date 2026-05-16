"""Pure-helper + schema validation tests for trade_transactions (migration 027)."""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.schemas.trade_transaction import (
    PaymentMode,
    TradeSide,
    TradeStatus,
    TradeTransactionCreate,
)


def test_trade_side_literal_covers_three_values() -> None:
    assert set(TradeSide.__args__) == {"import", "export", "royalty"}


def test_payment_mode_literal_covers_all_lc_variants_and_modes() -> None:
    expected = {
        "lc_sight",
        "lc_usance",
        "lc_btb",
        "lc_transferable",
        "lc_standby",
        "lc_red_clause",
        "open_account",
        "cash_in_advance",
        "documentary_collection_da",
        "documentary_collection_dp",
        "royalty_fee",
        "other",
    }
    assert set(PaymentMode.__args__) == expected


def test_trade_status_literal_covers_six_values() -> None:
    assert set(TradeStatus.__args__) == {
        "open",
        "in_progress",
        "settled",
        "overdue",
        "cancelled",
        "flagged",
    }


def test_minimum_trade_create_payload_validates() -> None:
    payload = TradeTransactionCreate(
        trade_side="import",
        payment_mode="lc_sight",
        subject_name="Sonali Trading Co.",
        subject_account="123456789",
        counterparty_name="Hong Kong Supplier Ltd",
        counterparty_country="HK",
        invoice_value=125_000.00,
    )
    assert payload.trade_side == "import"
    assert payload.payment_mode == "lc_sight"
    assert payload.currency == "USD"
    assert payload.status == "open"
    assert payload.subject_country == "BD"
    assert payload.container_numbers == []
    assert payload.transshipment_ports == []
    assert payload.discrepancies == []
    assert payload.metadata == {}


def test_full_tbml_red_flag_payload_validates() -> None:
    # An over-invoicing case: invoice_value far above market_reference_value,
    # paying to a counterparty account in a third country.
    payload = TradeTransactionCreate(
        trade_side="import",
        payment_mode="lc_usance",
        lc_reference="SOBLBD-LC-2026-04123",
        lc_issuing_bank="Sonali Bank PLC",
        lc_advising_bank="HSBC Hong Kong",
        lc_issue_date="2026-04-01",
        lc_expiry_date="2026-07-01",
        lcaf_reference="LCAF-04-77891",
        irc_or_erc="IRC-BD-ABC-001",
        subject_name="Rahman Enterprises",
        subject_account="018020012345",
        counterparty_name="Pacific Trading HK",
        counterparty_country="HK",
        notify_party="Khulna Logistics Pvt Ltd",
        hs_code="8517.12.00",
        goods_description="Smartphones — entry-level",
        quantity=1000,
        unit="pcs",
        unit_price=250.00,
        invoice_value=250_000.00,
        declared_value=185_000.00,
        market_reference_value=80_000.00,
        currency="USD",
        bdt_equivalent=27_500_000,
        bl_number="HLCU-HKG-7712-0011",
        vessel="MV Pacific Cygnus",
        container_numbers=["MSKU-7711889", "MSKU-7712441"],
        port_of_loading="Hong Kong",
        port_of_discharge="Chittagong",
        transshipment_ports=["Singapore"],
        be_number="BE-CTG-2026-094412",
        shipment_date="2026-04-15",
        status="flagged",
        discrepancies=[
            "Invoice value >3x market reference",
            "Transshipment via Singapore not declared on LC",
        ],
    )
    assert payload.invoice_value == 250_000.00
    assert payload.market_reference_value == 80_000.00
    assert payload.invoice_value / payload.market_reference_value > 3
    assert payload.status == "flagged"
    assert "Invoice value >3x market reference" in payload.discrepancies


def test_invoice_value_is_required() -> None:
    with pytest.raises(ValidationError):
        TradeTransactionCreate(
            trade_side="import",
            payment_mode="lc_sight",
            subject_name="X",
            subject_account="1",
            counterparty_name="Y",
            counterparty_country="HK",
        )


def test_unknown_payment_mode_rejected() -> None:
    with pytest.raises(ValidationError):
        TradeTransactionCreate(
            trade_side="import",
            payment_mode="hawala",  # not in PaymentMode literal
            subject_name="X",
            subject_account="1",
            counterparty_name="Y",
            counterparty_country="HK",
            invoice_value=100,
        )


def test_unknown_status_rejected() -> None:
    with pytest.raises(ValidationError):
        TradeTransactionCreate(
            trade_side="import",
            payment_mode="lc_sight",
            subject_name="X",
            subject_account="1",
            counterparty_name="Y",
            counterparty_country="HK",
            invoice_value=100,
            status="under_investigation",  # not in TradeStatus
        )
