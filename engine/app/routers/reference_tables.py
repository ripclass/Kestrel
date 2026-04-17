from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import AuthenticatedUser, get_current_user, require_roles
from app.dependencies import get_current_session
from app.schemas.reference_table import (
    ReferenceEntryCreate,
    ReferenceEntryMutationResponse,
    ReferenceEntryUpdate,
    ReferenceTableCountsResponse,
    ReferenceTableListResponse,
)
from app.services.reference_tables import (
    create_entry,
    delete_entry,
    list_entries,
    table_counts,
    update_entry,
)

router = APIRouter()


@router.get("", response_model=ReferenceTableListResponse)
async def list_records(
    user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_current_session)],
    table_name: Annotated[str, Query(alias="table_name")],
    include_inactive: Annotated[bool, Query(alias="include_inactive")] = False,
) -> ReferenceTableListResponse:
    entries = await list_entries(
        session, table_name=table_name, include_inactive=include_inactive
    )
    return ReferenceTableListResponse(entries=entries)


@router.get("/tables", response_model=ReferenceTableCountsResponse)
async def list_tables(
    user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_current_session)],
) -> ReferenceTableCountsResponse:
    tables = await table_counts(session)
    return ReferenceTableCountsResponse(tables=tables)


@router.post("", response_model=ReferenceEntryMutationResponse)
async def create_record(
    body: ReferenceEntryCreate,
    request: Request,
    user: Annotated[AuthenticatedUser, Depends(require_roles("admin", "superadmin"))],
    session: Annotated[AsyncSession, Depends(get_current_session)],
) -> ReferenceEntryMutationResponse:
    return await create_entry(
        session, user=user, payload=body, ip=request.client.host if request.client else None
    )


@router.patch("/{entry_id}", response_model=ReferenceEntryMutationResponse)
async def update_record(
    entry_id: str,
    body: ReferenceEntryUpdate,
    request: Request,
    user: Annotated[AuthenticatedUser, Depends(require_roles("admin", "superadmin"))],
    session: Annotated[AsyncSession, Depends(get_current_session)],
) -> ReferenceEntryMutationResponse:
    return await update_entry(
        session,
        user=user,
        entry_id=entry_id,
        payload=body,
        ip=request.client.host if request.client else None,
    )


@router.delete("/{entry_id}", status_code=204)
async def delete_record(
    entry_id: str,
    request: Request,
    user: Annotated[AuthenticatedUser, Depends(require_roles("admin", "superadmin"))],
    session: Annotated[AsyncSession, Depends(get_current_session)],
) -> None:
    await delete_entry(
        session, user=user, entry_id=entry_id, ip=request.client.host if request.client else None
    )
