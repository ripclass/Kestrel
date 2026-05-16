"""Router for /trade — trade-transaction surface (Phase B / migration 027 + 028)."""
from __future__ import annotations

import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import AuthenticatedUser, get_current_user, require_roles
from app.core.tbml_pipeline import run_tbml_scan_for_org
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


class TbmlScanResponse(BaseModel):
    trades_scanned: int
    hits: int
    alerts_created: int
    alerts_skipped_existing: int
    by_rule: dict[str, int]


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


@router.post("/scan", response_model=TbmlScanResponse)
async def run_scan(
    user: Annotated[
        AuthenticatedUser,
        Depends(require_roles("analyst", "manager", "admin", "superadmin")),
    ],
    session: Annotated[AsyncSession, Depends(get_current_session)],
    status_filter: Annotated[str | None, Query(alias="status")] = None,
    limit: Annotated[int, Query(ge=1, le=5000)] = 500,
) -> TbmlScanResponse:
    """Run TBML detection rules over the caller's org's trade transactions.

    Each rule hit produces an Alert row with predicate_offences and the
    BFIU avenue reference pre-populated. Re-running the scan is idempotent
    against open alerts (existing open alerts for the same trade+rule are
    skipped).
    """
    try:
        org_uuid = uuid.UUID(str(user.org_id))
    except (TypeError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Authenticated user is missing a valid organization id.",
        ) from exc
    summary: dict[str, Any] = await run_tbml_scan_for_org(
        session,
        org_id=org_uuid,
        status_filter=status_filter,
        limit=limit,
    )
    return TbmlScanResponse(**summary)


@router.get("/{trade_id}", response_model=TradeTransactionDetail)
async def record_detail(
    trade_id: str,
    user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_current_session)],
) -> TradeTransactionDetail:
    return await get_trade(session, trade_id)
