from io import BytesIO
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import StreamingResponse
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
from app.services.xlsx_export import build_disseminations_xlsx

router = APIRouter()


@router.get("/export.xlsx")
async def export_disseminations_xlsx(
    user: Annotated[AuthenticatedUser, Depends(require_roles("analyst", "manager", "admin", "superadmin"))],
    session: Annotated[AsyncSession, Depends(get_current_session)],
    recipient_agency: Annotated[str | None, Query(alias="recipient_agency")] = None,
    recipient_type: Annotated[str | None, Query(alias="recipient_type")] = None,
) -> StreamingResponse:
    items = await list_disseminations(
        session,
        recipient_agency=recipient_agency,
        recipient_type=recipient_type,
    )
    rows = [record.model_dump(mode="json") for record in items]
    payload = build_disseminations_xlsx(rows)
    return StreamingResponse(
        BytesIO(payload),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": 'attachment; filename="kestrel-disseminations.xlsx"'},
    )


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
