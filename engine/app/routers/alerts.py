from typing import Annotated

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import AuthenticatedUser, get_current_user
from app.dependencies import get_current_session
from app.schemas.alert import AlertDetail, AlertMutationRequest, AlertMutationResponse, AlertSummary
from app.services.alerts import get_alert_detail, list_alerts, update_alert

router = APIRouter()


@router.get("", response_model=list[AlertSummary])
async def alerts(
    user: Annotated[AuthenticatedUser, Depends(get_current_user)] = None,
    session: Annotated[AsyncSession, Depends(get_current_session)] = None,
) -> list[AlertSummary]:
    items = await list_alerts(session)
    return [AlertSummary.model_validate(item) for item in items]


@router.get("/{alert_id}", response_model=AlertDetail)
async def alert_detail(
    alert_id: str,
    user: Annotated[AuthenticatedUser, Depends(get_current_user)] = None,
    session: Annotated[AsyncSession, Depends(get_current_session)] = None,
) -> AlertDetail:
    return AlertDetail.model_validate(await get_alert_detail(session, user=user, alert_id=alert_id))


@router.post("/{alert_id}/actions", response_model=AlertMutationResponse)
async def mutate_alert(
    alert_id: str,
    body: AlertMutationRequest,
    request: Request,
    user: Annotated[AuthenticatedUser, Depends(get_current_user)] = None,
    session: Annotated[AsyncSession, Depends(get_current_session)] = None,
) -> AlertMutationResponse:
    return await update_alert(
        session,
        alert_id=alert_id,
        user=user,
        request=body,
        ip=request.client.host if request.client else None,
    )
