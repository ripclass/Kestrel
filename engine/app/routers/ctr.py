from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import AuthenticatedUser, get_current_user, require_roles
from app.dependencies import get_current_session
from app.schemas.ctr import CTRBulkImportRequest, CTRBulkImportResponse, CTRListResponse
from app.services.ctr import bulk_import_ctrs, list_ctrs

router = APIRouter()


@router.get("", response_model=CTRListResponse)
async def list_ctr_records(
    user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_current_session)],
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> CTRListResponse:
    return await list_ctrs(session, user=user, limit=limit, offset=offset)


@router.post("/import", response_model=CTRBulkImportResponse)
async def import_ctr_records(
    body: CTRBulkImportRequest,
    request: Request,
    user: Annotated[AuthenticatedUser, Depends(require_roles("analyst", "manager", "admin", "superadmin"))],
    session: Annotated[AsyncSession, Depends(get_current_session)],
) -> CTRBulkImportResponse:
    return await bulk_import_ctrs(
        session,
        user=user,
        records=[item.model_dump() for item in body.records],
        ip=request.client.host if request.client else None,
    )
