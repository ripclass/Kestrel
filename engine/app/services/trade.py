"""Service layer for trade_transactions (Phase B / migration 027)."""
from __future__ import annotations

from copy import deepcopy
from decimal import Decimal
from typing import Any
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import AuthenticatedUser
from app.models.audit import AuditLog
from app.models.trade_transaction import TradeTransaction
from app.services.tenancy import ensure_org_access, scope_to_user
from app.schemas.trade_transaction import (
    TradeTransactionCreate,
    TradeTransactionDetail,
    TradeTransactionMutationResponse,
    TradeTransactionSummary,
)


def _as_float(value: Decimal | float | int | None) -> float | None:
    if value is None:
        return None
    return float(value)


def _as_uuid(value: str | None) -> UUID | None:
    if not value:
        return None
    try:
        return UUID(value)
    except ValueError:
        return None


def _require_org(user: AuthenticatedUser) -> UUID:
    parsed = _as_uuid(user.org_id)
    if parsed is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Authenticated user is missing a valid organization id.",
        )
    return parsed


def _serialize_summary(record: TradeTransaction) -> TradeTransactionSummary:
    return TradeTransactionSummary(
        id=str(record.id),
        org_id=str(record.org_id),
        trade_ref=record.trade_ref,
        trade_side=record.trade_side,
        payment_mode=record.payment_mode,
        subject_name=record.subject_name,
        subject_account=record.subject_account,
        counterparty_name=record.counterparty_name,
        counterparty_country=record.counterparty_country,
        hs_code=record.hs_code,
        invoice_value=_as_float(record.invoice_value) or 0.0,
        declared_value=_as_float(record.declared_value),
        settlement_amount=_as_float(record.settlement_amount),
        currency=record.currency,
        status=record.status,
        shipment_date=record.shipment_date,
        settlement_date=record.settlement_date,
        lc_reference=record.lc_reference,
        bl_number=record.bl_number,
        created_at=record.created_at,
    )


def _serialize_detail(record: TradeTransaction) -> TradeTransactionDetail:
    summary = _serialize_summary(record)
    return TradeTransactionDetail(
        **summary.model_dump(),
        lc_issuing_bank=record.lc_issuing_bank,
        lc_advising_bank=record.lc_advising_bank,
        lc_confirming_bank=record.lc_confirming_bank,
        lc_issue_date=record.lc_issue_date,
        lc_expiry_date=record.lc_expiry_date,
        lcaf_reference=record.lcaf_reference,
        irc_or_erc=record.irc_or_erc,
        subject_bank=record.subject_bank,
        subject_country=record.subject_country,
        counterparty_bank=record.counterparty_bank,
        counterparty_account=record.counterparty_account,
        notify_party=record.notify_party,
        consignee=record.consignee,
        goods_description=record.goods_description,
        quantity=_as_float(record.quantity),
        unit=record.unit,
        unit_price=_as_float(record.unit_price),
        market_reference_value=_as_float(record.market_reference_value),
        bdt_equivalent=_as_float(record.bdt_equivalent),
        vessel=record.vessel,
        container_numbers=list(record.container_numbers or []),
        port_of_loading=record.port_of_loading,
        port_of_discharge=record.port_of_discharge,
        transshipment_ports=list(record.transshipment_ports or []),
        be_number=record.be_number,
        be_date=record.be_date,
        insurance_value=_as_float(record.insurance_value),
        discrepancies=list(record.discrepancies or []),
        linked_str_id=str(record.linked_str_id) if record.linked_str_id else None,
        linked_case_id=str(record.linked_case_id) if record.linked_case_id else None,
        metadata=deepcopy(record.metadata_json or {}),
        updated_at=record.updated_at,
    )


async def list_trades(
    session: AsyncSession,
    *,
    user: AuthenticatedUser,
    status_filter: str | None = None,
    payment_mode: str | None = None,
    counterparty_country: str | None = None,
    hs_code: str | None = None,
    limit: int = 100,
) -> list[TradeTransactionSummary]:
    stmt = select(TradeTransaction).order_by(TradeTransaction.created_at.desc()).limit(limit)
    stmt = scope_to_user(stmt, user, TradeTransaction.org_id)
    if status_filter:
        stmt = stmt.where(TradeTransaction.status == status_filter)
    if payment_mode:
        stmt = stmt.where(TradeTransaction.payment_mode == payment_mode)
    if counterparty_country:
        stmt = stmt.where(TradeTransaction.counterparty_country == counterparty_country)
    if hs_code:
        stmt = stmt.where(TradeTransaction.hs_code == hs_code)
    rows = (await session.execute(stmt)).scalars().all()
    return [_serialize_summary(row) for row in rows]


async def get_trade(session: AsyncSession, trade_id: str, *, user: AuthenticatedUser) -> TradeTransactionDetail:
    parsed = _as_uuid(trade_id)
    if parsed is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid trade id.")
    row = await session.get(TradeTransaction, parsed)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trade transaction not found.")
    ensure_org_access(row.org_id, user, detail="Trade transaction not found.")
    return _serialize_detail(row)


async def create_trade(
    session: AsyncSession,
    *,
    user: AuthenticatedUser,
    payload: TradeTransactionCreate,
    ip: str | None,
) -> TradeTransactionMutationResponse:
    org_id = _require_org(user)

    record = TradeTransaction(
        org_id=org_id,
        trade_ref="",
        trade_side=payload.trade_side,
        payment_mode=payload.payment_mode,
        lc_reference=payload.lc_reference,
        lc_issuing_bank=payload.lc_issuing_bank,
        lc_advising_bank=payload.lc_advising_bank,
        lc_confirming_bank=payload.lc_confirming_bank,
        lc_issue_date=payload.lc_issue_date,
        lc_expiry_date=payload.lc_expiry_date,
        lcaf_reference=payload.lcaf_reference,
        irc_or_erc=payload.irc_or_erc,
        subject_name=payload.subject_name.strip(),
        subject_account=payload.subject_account.strip(),
        subject_bank=payload.subject_bank,
        subject_country=payload.subject_country,
        counterparty_name=payload.counterparty_name.strip(),
        counterparty_country=payload.counterparty_country,
        counterparty_bank=payload.counterparty_bank,
        counterparty_account=payload.counterparty_account,
        notify_party=payload.notify_party,
        consignee=payload.consignee,
        hs_code=payload.hs_code,
        goods_description=payload.goods_description,
        quantity=payload.quantity,
        unit=payload.unit,
        unit_price=payload.unit_price,
        invoice_value=payload.invoice_value,
        declared_value=payload.declared_value,
        market_reference_value=payload.market_reference_value,
        settlement_amount=payload.settlement_amount,
        currency=payload.currency,
        bdt_equivalent=payload.bdt_equivalent,
        bl_number=payload.bl_number,
        vessel=payload.vessel,
        container_numbers=list(payload.container_numbers or []),
        port_of_loading=payload.port_of_loading,
        port_of_discharge=payload.port_of_discharge,
        transshipment_ports=list(payload.transshipment_ports or []),
        be_number=payload.be_number,
        be_date=payload.be_date,
        insurance_value=payload.insurance_value,
        status=payload.status,
        shipment_date=payload.shipment_date,
        settlement_date=payload.settlement_date,
        discrepancies=list(payload.discrepancies or []),
        linked_str_id=_as_uuid(payload.linked_str_id),
        linked_case_id=_as_uuid(payload.linked_case_id),
        metadata_json=payload.metadata,
    )
    session.add(record)
    await session.flush()

    audit_details: dict[str, Any] = {
        "trade_ref": record.trade_ref,
        "trade_side": record.trade_side,
        "payment_mode": record.payment_mode,
        "invoice_value": _as_float(record.invoice_value),
        "currency": record.currency,
        "counterparty_country": record.counterparty_country,
        "hs_code": record.hs_code,
    }
    session.add(
        AuditLog(
            org_id=org_id,
            user_id=_as_uuid(user.user_id),
            action="trade.created",
            resource_type="trade_transaction",
            resource_id=record.id,
            details=audit_details,
            ip=ip,
        )
    )
    await session.commit()
    await session.refresh(record)
    return TradeTransactionMutationResponse(trade=_serialize_detail(record))
