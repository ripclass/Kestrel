"""Router for /trade — trade-transaction surface (Phase B / migration 027)."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import AuthenticatedUser, get_current_user, require_roles
from app.dependencies import get_current_session
from app.schemas.trade_transaction import (
    TradeTransactionCreate,
    TradeTransactionDetail,
    TradeTransactionListResponse,
    TradeTransactionMutationResponse,
)
from app.services.trade import (
    create_trade,
    get_trade,
    list_trades,
)

router = APIRouter()


@router.get("", response_model=TradeTransactionListResponse)
async def list_records(
    user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_current_session)],
    status_filter: Annotated[str | None, Query(alias="status")] = None,
    payment_mode: Annotated[str | None, Query(alias="payment_mode")] = None,
    counterparty_country: Annotated[str | None, Query(alias="counterparty_country")] = None,
    hs_code: Annotated[str | None, Query(alias="hs_code")] = None,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
) -> TradeTransactionListResponse:
    trades = await list_trades(
        session,
        status_filter=status_filter,
        payment_mode=payment_mode,
        counterparty_country=counterparty_country,
        hs_code=hs_code,
        limit=limit,
    )
    return TradeTransactionListResponse(trades=trades)


@router.post("", response_model=TradeTransactionMutationResponse)
async def create_record(
    body: TradeTransactionCreate,
    request: Request,
    user: Annotated[
        AuthenticatedUser,
        Depends(require_roles("analyst", "manager", "admin", "superadmin")),
    ],
    session: Annotated[AsyncSession, Depends(get_current_session)],
) -> TradeTransactionMutationResponse:
    return await create_trade(
        session,
        user=user,
        payload=body,
        ip=request.client.host if request.client else None,
    )


@router.get("/{trade_id}", response_model=TradeTransactionDetail)
async def record_detail(
    trade_id: str,
    user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_current_session)],
) -> TradeTransactionDetail:
    return await get_trade(session, trade_id)
