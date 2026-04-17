from io import BytesIO
from typing import Annotated

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import AuthenticatedUser, get_current_user, require_roles
from app.dependencies import get_current_session
from app.schemas.alert import AlertDetail, AlertMutationRequest, AlertMutationResponse, AlertSummary
from app.services.alerts import get_alert_detail, list_alerts, update_alert
from app.services.xlsx_export import build_alerts_xlsx

router = APIRouter()


@router.get("/export.xlsx")
async def export_alerts_xlsx(
    user: Annotated[AuthenticatedUser, Depends(require_roles("analyst", "manager", "admin", "superadmin"))],
    session: Annotated[AsyncSession, Depends(get_current_session)],
) -> StreamingResponse:
    items = await list_alerts(session)
    payload = build_alerts_xlsx(items)
    return StreamingResponse(
        BytesIO(payload),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": 'attachment; filename="kestrel-alerts.xlsx"'},
    )


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
