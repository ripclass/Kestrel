"""Public status surface (V2 phase 6.1).

Two endpoints, **no auth** — these power the public status page that
lives at ``status.kestrel-nine.vercel.app`` (or ``/status`` on the web
app). Rate-limit at the proxy layer; nothing here writes.
"""
from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import AuthenticatedUser, get_current_user
from app.dependencies import get_current_session
from app.database import SessionLocal
from app.schemas.status import (
    PlanView,
    StatusIncidentInput,
    StatusIncidentResolveInput,
    StatusIncidentView,
    StatusSummaryResponse,
    TenantPlanView,
)
from app.services.billing import (
    all_plans,
    plan_summary,
    resolve_tenant_plan,
)
from app.services.status import (
    build_status_summary,
    list_incidents,
    post_incident,
    resolve_incident,
)

# Public-read router. Mounted without an auth dep so the status page is
# anonymous like every other status board on the internet.
router = APIRouter()


@router.get("/summary", response_model=StatusSummaryResponse)
async def summary() -> StatusSummaryResponse:
    async with SessionLocal() as session:
        payload = await build_status_summary(session)
    return StatusSummaryResponse.model_validate(payload)


@router.get("/incidents", response_model=list[StatusIncidentView])
async def incidents(active_only: bool = False, limit: int = 25) -> list[StatusIncidentView]:
    async with SessionLocal() as session:
        rows = await list_incidents(session, active_only=active_only, limit=limit)
    return [StatusIncidentView.model_validate(row) for row in rows]


@router.get("/plans", response_model=list[PlanView])
async def plans() -> list[PlanView]:
    """Public plan reference. Used by the bank-direct landing's pricing
    section so any change to the in-code plan definitions flows through
    automatically."""
    return [PlanView.model_validate(p) for p in all_plans()]


# --- Authenticated companions -------------------------------------------------
# These live next to the public router but require auth — used by the admin
# UI to post incidents and by the platform shell to read the caller's plan.

admin_router = APIRouter()


@admin_router.post("/incidents", response_model=StatusIncidentView)
async def admin_post_incident(
    body: StatusIncidentInput,
    user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_current_session)],
) -> StatusIncidentView:
    try:
        payload = await post_incident(
            session,
            user=user,
            component=body.component,
            severity=body.severity,
            summary=body.summary,
            message=body.message,
        )
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    return StatusIncidentView.model_validate(payload)


@admin_router.post("/incidents/{incident_id}/resolve", response_model=StatusIncidentView)
async def admin_resolve_incident(
    incident_id: str,
    body: StatusIncidentResolveInput,
    user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_current_session)],
) -> StatusIncidentView:
    try:
        parsed = uuid.UUID(incident_id)
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid incident id") from exc
    try:
        payload = await resolve_incident(session, user=user, incident_id=parsed, message=body.message)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    return StatusIncidentView.model_validate(payload)


@admin_router.get("/plan", response_model=TenantPlanView)
async def admin_plan(
    user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_current_session)],
) -> TenantPlanView:
    """Caller's resolved plan. Surfaced in the admin UI as a read-only
    summary; superadmin assignment uses ``/admin/team`` (not added here)."""
    tenant = await resolve_tenant_plan(session, org_id=user.org_id)
    return TenantPlanView(
        org_id=tenant.org_id,
        plan=PlanView.model_validate(plan_summary(tenant.plan)),
        overrides=tenant.overrides,
        plan_set_at=tenant.plan_set_at,
        plan_set_by=tenant.plan_set_by,
    )
