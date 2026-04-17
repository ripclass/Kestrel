from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import AuthenticatedUser, get_current_user, require_roles
from app.dependencies import get_current_session
from app.schemas.saved_query import (
    SavedQueryCreate,
    SavedQueryDetail,
    SavedQueryListResponse,
    SavedQueryMutationResponse,
    SavedQueryUpdate,
)
from app.services.saved_queries import (
    create_saved_query,
    delete_saved_query,
    get_saved_query,
    list_saved_queries,
    record_run,
    update_saved_query,
)

router = APIRouter()


@router.get("", response_model=SavedQueryListResponse)
async def list_records(
    user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_current_session)],
    query_type: Annotated[str | None, Query(alias="query_type")] = None,
) -> SavedQueryListResponse:
    items = await list_saved_queries(session, user=user, query_type=query_type)
    return SavedQueryListResponse(saved_queries=items)


@router.post("", response_model=SavedQueryMutationResponse)
async def create_record(
    body: SavedQueryCreate,
    request: Request,
    user: Annotated[AuthenticatedUser, Depends(require_roles("analyst", "manager", "admin", "superadmin"))],
    session: Annotated[AsyncSession, Depends(get_current_session)],
) -> SavedQueryMutationResponse:
    return await create_saved_query(
        session, user=user, payload=body, ip=request.client.host if request.client else None
    )


@router.get("/{query_id}", response_model=SavedQueryDetail)
async def record_detail(
    query_id: str,
    user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_current_session)],
) -> SavedQueryDetail:
    return await get_saved_query(session, user=user, query_id=query_id)


@router.patch("/{query_id}", response_model=SavedQueryMutationResponse)
async def update_record(
    query_id: str,
    body: SavedQueryUpdate,
    request: Request,
    user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_current_session)],
) -> SavedQueryMutationResponse:
    return await update_saved_query(
        session,
        user=user,
        query_id=query_id,
        payload=body,
        ip=request.client.host if request.client else None,
    )


@router.delete("/{query_id}", status_code=204)
async def delete_record(
    query_id: str,
    request: Request,
    user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_current_session)],
) -> None:
    await delete_saved_query(
        session, user=user, query_id=query_id, ip=request.client.host if request.client else None
    )


@router.post("/{query_id}/record-run", response_model=SavedQueryMutationResponse)
async def log_run(
    query_id: str,
    user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_current_session)],
) -> SavedQueryMutationResponse:
    return await record_run(session, user=user, query_id=query_id)
