from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import AuthenticatedUser, get_current_user, require_roles
from app.dependencies import get_current_session
from app.schemas.ier import (
    IERCloseRequest,
    IERDetail,
    IERInboundCreate,
    IERListResponse,
    IERMutationResponse,
    IEROutboundCreate,
    IERRespondRequest,
)
from app.services.ier import (
    close_ier,
    create_inbound_ier,
    create_outbound_ier,
    get_ier,
    list_iers,
    respond_to_ier,
)

router = APIRouter()


@router.get("", response_model=IERListResponse)
async def list_records(
    user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_current_session)],
    direction: Annotated[str | None, Query(alias="direction")] = None,
    status_filter: Annotated[str | None, Query(alias="status")] = None,
    counterparty: Annotated[str | None, Query(alias="counterparty")] = None,
) -> IERListResponse:
    return await list_iers(
        session,
        direction=direction,
        status_filter=status_filter,
        counterparty=counterparty,
    )


@router.post("/outbound", response_model=IERMutationResponse)
async def create_outbound(
    body: IEROutboundCreate,
    request: Request,
    user: Annotated[AuthenticatedUser, Depends(require_roles("analyst", "manager", "admin", "superadmin"))],
    session: Annotated[AsyncSession, Depends(get_current_session)],
) -> IERMutationResponse:
    return await create_outbound_ier(
        session, user=user, payload=body, ip=request.client.host if request.client else None
    )


@router.post("/inbound", response_model=IERMutationResponse)
async def create_inbound(
    body: IERInboundCreate,
    request: Request,
    user: Annotated[AuthenticatedUser, Depends(require_roles("analyst", "manager", "admin", "superadmin"))],
    session: Annotated[AsyncSession, Depends(get_current_session)],
) -> IERMutationResponse:
    return await create_inbound_ier(
        session, user=user, payload=body, ip=request.client.host if request.client else None
    )


@router.get("/{ier_id}", response_model=IERDetail)
async def record_detail(
    ier_id: str,
    user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_current_session)],
) -> IERDetail:
    return await get_ier(session, ier_id)


@router.post("/{ier_id}/respond", response_model=IERMutationResponse)
async def respond_record(
    ier_id: str,
    body: IERRespondRequest,
    request: Request,
    user: Annotated[AuthenticatedUser, Depends(require_roles("analyst", "manager", "admin", "superadmin"))],
    session: Annotated[AsyncSession, Depends(get_current_session)],
) -> IERMutationResponse:
    return await respond_to_ier(
        session,
        user=user,
        ier_id=ier_id,
        payload=body,
        ip=request.client.host if request.client else None,
    )


@router.post("/{ier_id}/close", response_model=IERMutationResponse)
async def close_record(
    ier_id: str,
    body: IERCloseRequest,
    request: Request,
    user: Annotated[AuthenticatedUser, Depends(require_roles("manager", "admin", "superadmin"))],
    session: Annotated[AsyncSession, Depends(get_current_session)],
) -> IERMutationResponse:
    return await close_ier(
        session,
        user=user,
        ier_id=ier_id,
        payload=body,
        ip=request.client.host if request.client else None,
    )
