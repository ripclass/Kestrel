from typing import Annotated

from fastapi import APIRouter, Depends

from app.auth import AuthenticatedUser, get_current_user
from app.schemas.case import CaseSummary, CaseWorkspace
from app.services.case_mgmt import get_case_workspace, list_cases

router = APIRouter()


@router.get("", response_model=list[CaseSummary])
async def cases(user: Annotated[AuthenticatedUser, Depends(get_current_user)]) -> list[CaseSummary]:
    return [CaseSummary.model_validate(item) for item in list_cases()]


@router.get("/{case_id}", response_model=CaseWorkspace)
async def case_workspace(
    case_id: str,
    user: Annotated[AuthenticatedUser, Depends(get_current_user)] = None,
) -> CaseWorkspace:
    return CaseWorkspace.model_validate(get_case_workspace(case_id))
