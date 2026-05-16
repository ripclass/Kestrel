"""Trade-transaction model — Phase B foundation (migration 027).

Captures the per-trade-deal data BFIU TBML Guidelines 2019 expects banks to
record on every international trade. The 6 TBML detection rules in the next
PR read against this schema.
"""
from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, Numeric, String, func
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class TradeTransaction(Base):
    __tablename__ = "trade_transactions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("organizations.id"))
    trade_ref: Mapped[str] = mapped_column(String(64))
    trade_side: Mapped[str] = mapped_column(String(16))
    payment_mode: Mapped[str] = mapped_column(String(32))

    # LC structure (only populated when payment_mode is an LC variant)
    lc_reference: Mapped[str | None] = mapped_column(String, default=None, nullable=True)
    lc_issuing_bank: Mapped[str | None] = mapped_column(String, default=None, nullable=True)
    lc_advising_bank: Mapped[str | None] = mapped_column(String, default=None, nullable=True)
    lc_confirming_bank: Mapped[str | None] = mapped_column(String, default=None, nullable=True)
    lc_issue_date: Mapped[date | None] = mapped_column(Date(), default=None, nullable=True)
    lc_expiry_date: Mapped[date | None] = mapped_column(Date(), default=None, nullable=True)
    lcaf_reference: Mapped[str | None] = mapped_column(String, default=None, nullable=True)

    # Importer / Exporter cert
    irc_or_erc: Mapped[str | None] = mapped_column(String, default=None, nullable=True)

    # Subject (own-side customer)
    subject_name: Mapped[str] = mapped_column(String)
    subject_account: Mapped[str] = mapped_column(String)
    subject_bank: Mapped[str | None] = mapped_column(String, default=None, nullable=True)
    subject_country: Mapped[str] = mapped_column(String(8), default="BD")

    # Counterparty (foreign side)
    counterparty_name: Mapped[str] = mapped_column(String)
    counterparty_country: Mapped[str] = mapped_column(String(8))
    counterparty_bank: Mapped[str | None] = mapped_column(String, default=None, nullable=True)
    counterparty_account: Mapped[str | None] = mapped_column(String, default=None, nullable=True)

    # Notify party + consignee
    notify_party: Mapped[str | None] = mapped_column(String, default=None, nullable=True)
    consignee: Mapped[str | None] = mapped_column(String, default=None, nullable=True)

    # Goods
    hs_code: Mapped[str | None] = mapped_column(String, default=None, nullable=True)
    goods_description: Mapped[str | None] = mapped_column(String, default=None, nullable=True)
    quantity: Mapped[float | None] = mapped_column(Numeric(18, 4), default=None, nullable=True)
    unit: Mapped[str | None] = mapped_column(String, default=None, nullable=True)
    unit_price: Mapped[float | None] = mapped_column(Numeric(18, 4), default=None, nullable=True)

    # Values
    invoice_value: Mapped[float] = mapped_column(Numeric(18, 2))
    declared_value: Mapped[float | None] = mapped_column(Numeric(18, 2), default=None, nullable=True)
    market_reference_value: Mapped[float | None] = mapped_column(Numeric(18, 2), default=None, nullable=True)
    settlement_amount: Mapped[float | None] = mapped_column(Numeric(18, 2), default=None, nullable=True)
    currency: Mapped[str] = mapped_column(String(8), default="USD")
    bdt_equivalent: Mapped[float | None] = mapped_column(Numeric(18, 2), default=None, nullable=True)

    # Shipment / logistics
    bl_number: Mapped[str | None] = mapped_column(String, default=None, nullable=True)
    vessel: Mapped[str | None] = mapped_column(String, default=None, nullable=True)
    container_numbers: Mapped[list[str]] = mapped_column(ARRAY(String), default=list, server_default="{}")
    port_of_loading: Mapped[str | None] = mapped_column(String, default=None, nullable=True)
    port_of_discharge: Mapped[str | None] = mapped_column(String, default=None, nullable=True)
    transshipment_ports: Mapped[list[str]] = mapped_column(ARRAY(String), default=list, server_default="{}")

    # Customs
    be_number: Mapped[str | None] = mapped_column(String, default=None, nullable=True)
    be_date: Mapped[date | None] = mapped_column(Date(), default=None, nullable=True)

    # Insurance
    insurance_value: Mapped[float | None] = mapped_column(Numeric(18, 2), default=None, nullable=True)

    # State + lifecycle
    status: Mapped[str] = mapped_column(String(16), default="open")
    shipment_date: Mapped[date | None] = mapped_column(Date(), default=None, nullable=True)
    settlement_date: Mapped[date | None] = mapped_column(Date(), default=None, nullable=True)

    # Discrepancies + linkage
    discrepancies: Mapped[list[str]] = mapped_column(ARRAY(String), default=list, server_default="{}")
    linked_str_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), default=None, nullable=True)
    linked_case_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), default=None, nullable=True)

    metadata_json: Mapped[dict] = mapped_column("metadata", JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
