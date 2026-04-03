from typing import Annotated

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import AuthenticatedUser, get_current_user
from app.dependencies import get_current_session
from app.schemas.case import CaseMutationRequest, CaseMutationResponse, CaseSummary, CaseWorkspace
from app.services.case_mgmt import get_case_workspace, list_cases, update_case

router = APIRouter()


@router.get("", response_model=list[CaseSummary])
async def cases(
    user: Annotated[AuthenticatedUser, Depends(get_current_user)] = None,
    session: Annotated[AsyncSession, Depends(get_current_session)] = None,
) -> list[CaseSummary]:
    items = await list_cases(session)
    return [CaseSummary.model_validate(item) for item in items]


@router.get("/{case_id}", response_model=CaseWorkspace)
async def case_workspace(
    case_id: str,
    user: Annotated[AuthenticatedUser, Depends(get_current_user)] = None,
    session: Annotated[AsyncSession, Depends(get_current_session)] = None,
) -> CaseWorkspace:
    return CaseWorkspace.model_validate(await get_case_workspace(session, user=user, case_id=case_id))


@router.post("/{case_id}/actions", response_model=CaseMutationResponse)
async def mutate_case(
    case_id: str,
    body: CaseMutationRequest,
    request: Request,
    user: Annotated[AuthenticatedUser, Depends(get_current_user)] = None,
    session: Annotated[AsyncSession, Depends(get_current_session)] = None,
) -> CaseMutationResponse:
    return await update_case(
        session,
        case_id=case_id,
        user=user,
        request=body,
        ip=request.client.host if request.client else None,
    )
