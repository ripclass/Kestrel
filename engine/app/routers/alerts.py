from typing import Annotated

from fastapi import APIRouter, Depends

from app.auth import AuthenticatedUser, get_current_user
from app.schemas.alert import AlertDetail, AlertSummary
from seed.fixtures import ALERTS

router = APIRouter()


@router.get("", response_model=list[AlertSummary])
async def list_alerts(user: Annotated[AuthenticatedUser, Depends(get_current_user)]) -> list[AlertSummary]:
    return [AlertSummary.model_validate(item.model_dump()) for item in ALERTS]


@router.get("/{alert_id}", response_model=AlertDetail)
async def get_alert(alert_id: str, user: Annotated[AuthenticatedUser, Depends(get_current_user)]) -> AlertDetail:
    for alert in ALERTS:
        if alert.id == alert_id:
            return alert
    return ALERTS[0]
