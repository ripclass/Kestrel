from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import AuthenticatedUser, get_current_user, require_roles
from app.dependencies import get_current_session
from app.schemas.scan import DetectionRunDetail, DetectionRunSummary, FlaggedAccount, ScanQueueRequest, ScanQueueResponse
from app.services.scanning import get_results, get_run_detail, list_runs, queue_run

router = APIRouter()


@router.get("/runs", response_model=list[DetectionRunSummary])
async def runs(
    user: Annotated[AuthenticatedUser, Depends(get_current_user)] = None,
    session: Annotated[AsyncSession, Depends(get_current_session)] = None,
) -> list[DetectionRunSummary]:
    return [DetectionRunSummary.model_validate(item) for item in await list_runs(session)]


@router.post("/runs", response_model=ScanQueueResponse)
async def queue(
    body: ScanQueueRequest,
    user: Annotated[AuthenticatedUser, Depends(require_roles("manager", "admin", "superadmin"))],
    session: Annotated[AsyncSession, Depends(get_current_session)] = None,
) -> ScanQueueResponse:
    return await queue_run(session, user=user, request=body)


@router.get("/runs/{run_id}", response_model=DetectionRunDetail)
async def run_detail(
    run_id: str,
    user: Annotated[AuthenticatedUser, Depends(get_current_user)] = None,
    session: Annotated[AsyncSession, Depends(get_current_session)] = None,
) -> DetectionRunDetail:
    return DetectionRunDetail.model_validate(await get_run_detail(session, run_id=run_id))


@router.get("/runs/{run_id}/results", response_model=list[FlaggedAccount])
async def results(
    run_id: str,
    user: Annotated[AuthenticatedUser, Depends(get_current_user)] = None,
    session: Annotated[AsyncSession, Depends(get_current_session)] = None,
) -> list[FlaggedAccount]:
    return [FlaggedAccount.model_validate(item) for item in await get_results(session, run_id=run_id)]
