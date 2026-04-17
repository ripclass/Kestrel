from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import AuthenticatedUser, get_current_user, require_roles
from app.dependencies import get_current_session
from app.schemas.match_definition import (
    MatchDefinitionCreate,
    MatchDefinitionDetail,
    MatchDefinitionListResponse,
    MatchDefinitionMutationResponse,
    MatchDefinitionUpdate,
    MatchExecutionResponse,
)
from app.services.match_definitions import (
    create_match_definition,
    delete_match_definition,
    execute_match_definition,
    get_match_definition,
    list_match_definitions,
    update_match_definition,
)

router = APIRouter()


@router.get("", response_model=MatchDefinitionListResponse)
async def list_records(
    user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_current_session)],
    is_active: Annotated[bool | None, Query(alias="is_active")] = None,
) -> MatchDefinitionListResponse:
    items = await list_match_definitions(session, is_active=is_active)
    return MatchDefinitionListResponse(match_definitions=items)


@router.post("", response_model=MatchDefinitionMutationResponse)
async def create_record(
    body: MatchDefinitionCreate,
    request: Request,
    user: Annotated[AuthenticatedUser, Depends(require_roles("manager", "admin", "superadmin"))],
    session: Annotated[AsyncSession, Depends(get_current_session)],
) -> MatchDefinitionMutationResponse:
    return await create_match_definition(
        session, user=user, payload=body, ip=request.client.host if request.client else None
    )


@router.get("/{definition_id}", response_model=MatchDefinitionDetail)
async def record_detail(
    definition_id: str,
    user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_current_session)],
) -> MatchDefinitionDetail:
    return await get_match_definition(session, definition_id)


@router.patch("/{definition_id}", response_model=MatchDefinitionMutationResponse)
async def update_record(
    definition_id: str,
    body: MatchDefinitionUpdate,
    request: Request,
    user: Annotated[AuthenticatedUser, Depends(require_roles("manager", "admin", "superadmin"))],
    session: Annotated[AsyncSession, Depends(get_current_session)],
) -> MatchDefinitionMutationResponse:
    return await update_match_definition(
        session,
        user=user,
        definition_id=definition_id,
        payload=body,
        ip=request.client.host if request.client else None,
    )


@router.delete("/{definition_id}", status_code=204)
async def delete_record(
    definition_id: str,
    request: Request,
    user: Annotated[AuthenticatedUser, Depends(require_roles("manager", "admin", "superadmin"))],
    session: Annotated[AsyncSession, Depends(get_current_session)],
) -> None:
    await delete_match_definition(
        session,
        user=user,
        definition_id=definition_id,
        ip=request.client.host if request.client else None,
    )


@router.post("/{definition_id}/execute", response_model=MatchExecutionResponse)
async def execute_record(
    definition_id: str,
    request: Request,
    user: Annotated[AuthenticatedUser, Depends(require_roles("manager", "admin", "superadmin"))],
    session: Annotated[AsyncSession, Depends(get_current_session)],
) -> MatchExecutionResponse:
    return await execute_match_definition(
        session,
        user=user,
        definition_id=definition_id,
        ip=request.client.host if request.client else None,
    )
