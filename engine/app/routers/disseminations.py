from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import AuthenticatedUser, get_current_user, require_roles
from app.dependencies import get_current_session
from app.schemas.dissemination import (
    DisseminationCreate,
    DisseminationDetail,
    DisseminationListResponse,
    DisseminationMutationResponse,
)
from app.services.disseminations import (
    create_dissemination,
    get_dissemination,
    list_disseminations,
)

router = APIRouter()


@router.get("", response_model=DisseminationListResponse)
async def list_records(
    user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_current_session)],
    recipient_agency: Annotated[str | None, Query(alias="recipient_agency")] = None,
    recipient_type: Annotated[str | None, Query(alias="recipient_type")] = None,
) -> DisseminationListResponse:
    disseminations = await list_disseminations(
        session,
        recipient_agency=recipient_agency,
        recipient_type=recipient_type,
    )
    return DisseminationListResponse(disseminations=disseminations)


@router.post("", response_model=DisseminationMutationResponse)
async def create_record(
    body: DisseminationCreate,
    request: Request,
    user: Annotated[AuthenticatedUser, Depends(require_roles("analyst", "manager", "admin", "superadmin"))],
    session: Annotated[AsyncSession, Depends(get_current_session)],
) -> DisseminationMutationResponse:
    return await create_dissemination(
        session,
        user=user,
        payload=body,
        ip=request.client.host if request.client else None,
    )


@router.get("/{dissem_id}", response_model=DisseminationDetail)
async def record_detail(
    dissem_id: str,
    user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_current_session)],
) -> DisseminationDetail:
    return await get_dissemination(session, dissem_id)
