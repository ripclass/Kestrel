from typing import Annotated

from fastapi import APIRouter, Depends

from app.auth import AuthenticatedUser, get_current_user, require_roles
from app.schemas.scan import DetectionRunSummary, FlaggedAccount, ScanQueueResponse
from app.services.scanning import get_results, list_runs, queue_run

router = APIRouter()


@router.get("/runs", response_model=list[DetectionRunSummary])
async def runs(user: Annotated[AuthenticatedUser, Depends(get_current_user)]) -> list[DetectionRunSummary]:
    return [DetectionRunSummary.model_validate(item) for item in list_runs()]


@router.post("/runs", response_model=ScanQueueResponse)
async def queue(
    user: Annotated[AuthenticatedUser, Depends(require_roles("manager", "admin", "superadmin"))],
) -> ScanQueueResponse:
    return ScanQueueResponse.model_validate(queue_run())


@router.get("/runs/{run_id}/results", response_model=list[FlaggedAccount])
async def results(
    run_id: str,
    user: Annotated[AuthenticatedUser, Depends(get_current_user)] = None,
) -> list[FlaggedAccount]:
    return [FlaggedAccount.model_validate(item) for item in get_results()]
