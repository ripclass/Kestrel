from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import AuthenticatedUser, get_current_user
from app.dependencies import get_current_session
from app.schemas.overview import OverviewResponse
from app.services.reporting import build_overview

router = APIRouter()


@router.get("", response_model=OverviewResponse)
async def get_overview(
    user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_current_session)],
) -> OverviewResponse:
    return await build_overview(session, user=user)
