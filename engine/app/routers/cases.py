from io import BytesIO
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import AuthenticatedUser, get_current_user, require_roles
from app.dependencies import get_current_session
from app.schemas.case import (
    CaseDecideRequest,
    CaseMutationRequest,
    CaseMutationResponse,
    CaseProposeRequest,
    CaseRfiRequest,
    CaseSummary,
    CaseWorkspace,
)
from app.services.case_mgmt import (
    create_rfi,
    decide_proposal,
    get_case_workspace,
    list_cases,
    propose_case,
    update_case,
)
from app.services.pdf_export import render_case_pdf

router = APIRouter()


@router.get("", response_model=list[CaseSummary])
async def cases(
    user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_current_session)],
    variant: Annotated[str | None, Query(alias="variant")] = None,
    status_filter: Annotated[str | None, Query(alias="status")] = None,
    assigned_to: Annotated[str | None, Query(alias="assigned_to")] = None,
) -> list[CaseSummary]:
    items = await list_cases(
        session,
        variant=variant,
        status_filter=status_filter,
        assigned_to=assigned_to,
    )
    return [CaseSummary.model_validate(item) for item in items]


@router.post("/propose", response_model=CaseMutationResponse)
async def propose_new_case(
    body: CaseProposeRequest,
    request: Request,
    user: Annotated[AuthenticatedUser, Depends(require_roles("analyst", "manager", "admin", "superadmin"))],
    session: Annotated[AsyncSession, Depends(get_current_session)],
) -> CaseMutationResponse:
    return await propose_case(
        session,
        user=user,
        request=body,
        ip=request.client.host if request.client else None,
    )


@router.post("/rfi", response_model=CaseMutationResponse)
async def open_rfi(
    body: CaseRfiRequest,
    request: Request,
    user: Annotated[AuthenticatedUser, Depends(require_roles("analyst", "manager", "admin", "superadmin"))],
    session: Annotated[AsyncSession, Depends(get_current_session)],
) -> CaseMutationResponse:
    return await create_rfi(
        session,
        user=user,
        request=body,
        ip=request.client.host if request.client else None,
    )


@router.get("/{case_id}", response_model=CaseWorkspace)
async def case_workspace(
    case_id: str,
    user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_current_session)],
) -> CaseWorkspace:
    return CaseWorkspace.model_validate(await get_case_workspace(session, user=user, case_id=case_id))


@router.get("/{case_id}/export.pdf")
async def export_case_pdf(
    case_id: str,
    user: Annotated[AuthenticatedUser, Depends(require_roles("analyst", "manager", "admin", "superadmin"))],
    session: Annotated[AsyncSession, Depends(get_current_session)],
) -> StreamingResponse:
    pdf_bytes = await render_case_pdf(session, case_id=case_id, user=user)
    return StreamingResponse(
        BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="case-{case_id}.pdf"'},
    )


@router.post("/{case_id}/decide", response_model=CaseMutationResponse)
async def decide_case_proposal(
    case_id: str,
    body: CaseDecideRequest,
    request: Request,
    user: Annotated[AuthenticatedUser, Depends(require_roles("manager", "admin", "superadmin"))],
    session: Annotated[AsyncSession, Depends(get_current_session)],
) -> CaseMutationResponse:
    return await decide_proposal(
        session,
        user=user,
        case_id=case_id,
        request=body,
        ip=request.client.host if request.client else None,
    )


@router.post("/{case_id}/actions", response_model=CaseMutationResponse)
async def mutate_case(
    case_id: str,
    body: CaseMutationRequest,
    request: Request,
    user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_current_session)],
) -> CaseMutationResponse:
    return await update_case(
        session,
        case_id=case_id,
        user=user,
        request=body,
        ip=request.client.host if request.client else None,
    )
