from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import AuthenticatedUser, get_current_user, require_roles
from app.dependencies import get_current_session
from app.schemas.diagram import (
    DiagramCreate,
    DiagramDetail,
    DiagramListResponse,
    DiagramMutationResponse,
    DiagramUpdate,
)
from app.services.diagrams import (
    create_diagram,
    delete_diagram,
    get_diagram,
    list_diagrams,
    update_diagram,
)

router = APIRouter()


@router.get("", response_model=DiagramListResponse)
async def list_records(
    user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_current_session)],
    linked_case_id: Annotated[str | None, Query(alias="linked_case_id")] = None,
    linked_str_id: Annotated[str | None, Query(alias="linked_str_id")] = None,
) -> DiagramListResponse:
    items = await list_diagrams(
        session, linked_case_id=linked_case_id, linked_str_id=linked_str_id
    )
    return DiagramListResponse(diagrams=items)


@router.post("", response_model=DiagramMutationResponse)
async def create_record(
    body: DiagramCreate,
    request: Request,
    user: Annotated[AuthenticatedUser, Depends(require_roles("analyst", "manager", "admin", "superadmin"))],
    session: Annotated[AsyncSession, Depends(get_current_session)],
) -> DiagramMutationResponse:
    return await create_diagram(
        session, user=user, payload=body, ip=request.client.host if request.client else None
    )


@router.get("/{diagram_id}", response_model=DiagramDetail)
async def record_detail(
    diagram_id: str,
    user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_current_session)],
) -> DiagramDetail:
    return await get_diagram(session, diagram_id)


@router.patch("/{diagram_id}", response_model=DiagramMutationResponse)
async def update_record(
    diagram_id: str,
    body: DiagramUpdate,
    request: Request,
    user: Annotated[AuthenticatedUser, Depends(require_roles("analyst", "manager", "admin", "superadmin"))],
    session: Annotated[AsyncSession, Depends(get_current_session)],
) -> DiagramMutationResponse:
    return await update_diagram(
        session,
        user=user,
        diagram_id=diagram_id,
        payload=body,
        ip=request.client.host if request.client else None,
    )


@router.delete("/{diagram_id}", status_code=204)
async def delete_record(
    diagram_id: str,
    request: Request,
    user: Annotated[AuthenticatedUser, Depends(require_roles("analyst", "manager", "admin", "superadmin"))],
    session: Annotated[AsyncSession, Depends(get_current_session)],
) -> None:
    await delete_diagram(
        session, user=user, diagram_id=diagram_id, ip=request.client.host if request.client else None
    )
