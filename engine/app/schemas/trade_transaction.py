"""TradeTransaction Pydantic schemas (Phase B / migration 027)."""
from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field

TradeSide = Literal["import", "export", "royalty"]

PaymentMode = Literal[
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
]

TradeStatus = Literal[
    "open",
    "in_progress",
    "settled",
    "overdue",
    "cancelled",
    "flagged",
]


class TradeTransactionCreate(BaseModel):
    trade_side: TradeSide
    payment_mode: PaymentMode

    # LC structure — only populated for LC variants. Schema doesn't reject
    # populated LC fields on non-LC modes (some banks back-fill the LC ref
    # after an open-account deal converts to LC mid-flight); the realtime
    # scorer treats inconsistent combinations as a soft signal.
    lc_reference: str | None = None
    lc_issuing_bank: str | None = None
    lc_advising_bank: str | None = None
    lc_confirming_bank: str | None = None
    lc_issue_date: date | None = None
    lc_expiry_date: date | None = None
    lcaf_reference: str | None = None

    irc_or_erc: str | None = None

    subject_name: str
    subject_account: str
    subject_bank: str | None = None
    subject_country: str = "BD"

    counterparty_name: str
    counterparty_country: str
    counterparty_bank: str | None = None
    counterparty_account: str | None = None

    notify_party: str | None = None
    consignee: str | None = None

    hs_code: str | None = None
    goods_description: str | None = None
    quantity: float | None = None
    unit: str | None = None
    unit_price: float | None = None

    invoice_value: float
    declared_value: float | None = None
    market_reference_value: float | None = None
    settlement_amount: float | None = None
    currency: str = "USD"
    bdt_equivalent: float | None = None

    bl_number: str | None = None
    vessel: str | None = None
    container_numbers: list[str] = Field(default_factory=list)
    port_of_loading: str | None = None
    port_of_discharge: str | None = None
    transshipment_ports: list[str] = Field(default_factory=list)

    be_number: str | None = None
    be_date: date | None = None

    insurance_value: float | None = None

    status: TradeStatus = "open"
    shipment_date: date | None = None
    settlement_date: date | None = None

    discrepancies: list[str] = Field(default_factory=list)
    linked_str_id: str | None = None
    linked_case_id: str | None = None

    metadata: dict[str, object] = Field(default_factory=dict)


class TradeTransactionSummary(BaseModel):
    id: str
    org_id: str
    trade_ref: str
    trade_side: TradeSide
    payment_mode: PaymentMode
    subject_name: str
    subject_account: str
    counterparty_name: str
    counterparty_country: str
    hs_code: str | None = None
    invoice_value: float
    declared_value: float | None = None
    settlement_amount: float | None = None
    currency: str
    status: TradeStatus
    shipment_date: date | None = None
    settlement_date: date | None = None
    lc_reference: str | None = None
    bl_number: str | None = None
    created_at: datetime


class TradeTransactionDetail(TradeTransactionSummary):
    lc_issuing_bank: str | None = None
    lc_advising_bank: str | None = None
    lc_confirming_bank: str | None = None
    lc_issue_date: date | None = None
    lc_expiry_date: date | None = None
    lcaf_reference: str | None = None
    irc_or_erc: str | None = None
    subject_bank: str | None = None
    subject_country: str = "BD"
    counterparty_bank: str | None = None
    counterparty_account: str | None = None
    notify_party: str | None = None
    consignee: str | None = None
    goods_description: str | None = None
    quantity: float | None = None
    unit: str | None = None
    unit_price: float | None = None
    market_reference_value: float | None = None
    bdt_equivalent: float | None = None
    vessel: str | None = None
    container_numbers: list[str] = Field(default_factory=list)
    port_of_loading: str | None = None
    port_of_discharge: str | None = None
    transshipment_ports: list[str] = Field(default_factory=list)
    be_number: str | None = None
    be_date: date | None = None
    insurance_value: float | None = None
    discrepancies: list[str] = Field(default_factory=list)
    linked_str_id: str | None = None
    linked_case_id: str | None = None
    metadata: dict[str, object] = Field(default_factory=dict)
    updated_at: datetime


class TradeTransactionListResponse(BaseModel):
    trades: list[TradeTransactionSummary]


class TradeTransactionMutationResponse(BaseModel):
    trade: TradeTransactionDetail
