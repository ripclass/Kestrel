"""Kestrel operator console — cross-tenant Enso-internal surface.

Enso-internal. Gated by ``require_platform_operator`` (operator email
allow-list), *not* the per-tenant role model — a bank or BFIU customer
must never see operator telemetry across other tenants.

Reads run on the plain ``SessionLocal`` (engine connects as ``postgres``
/ BYPASSRLS) because the whole point of this surface is cross-tenant
visibility, which RLS denies normal sessions.
"""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.auth import AuthenticatedUser, require_platform_operator
from app.config import get_settings
from app.database import SessionLocal
from app.schemas.platform_ops import (
    OperatorSession,
    PilotDetailResponse,
    PilotOverviewResponse,
    SystemHealthResponse,
    TenantClassifyInput,
    TenantListResponse,
    TenantSummary,
)
from app.services.platform_ops import (
    build_pilot_detail,
    build_pilot_overview,
    build_system_health,
    list_tenants,
    update_tenant_classification,
)

router = APIRouter()


@router.get("/session", response_model=OperatorSession)
async def session_info(
    operator: Annotated[AuthenticatedUser, Depends(require_platform_operator)],
) -> OperatorSession:
    """The calling operator's identity + console role. Drives which modules
    the web shell shows."""
    role = get_settings().platform_operator_role(operator.email) or "owner"
    return OperatorSession(
        email=operator.email,
        name=operator.designation or None,
        role=role,
    )


@router.get("/pilots", response_model=PilotOverviewResponse)
async def pilots(
    _: Annotated[AuthenticatedUser, Depends(require_platform_operator)],
) -> PilotOverviewResponse:
    """Cross-tenant pilot-health overview: a summary row plus one card per
    tenant (seats, login coverage, action counts, engagement, trend)."""
    async with SessionLocal() as session:
        payload = await build_pilot_overview(session)
    return PilotOverviewResponse.model_validate(payload)


@router.get("/pilots/{org_id}", response_model=PilotDetailResponse)
async def pilot_detail(
    org_id: str,
    _: Annotated[AuthenticatedUser, Depends(require_platform_operator)],
) -> PilotDetailResponse:
    """Drill-down for one tenant: per-user activity, recent-action feed, and
    a 30-day action breakdown by resource type."""
    async with SessionLocal() as session:
        try:
            payload = await build_pilot_detail(session, org_id=org_id)
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
            ) from exc
        except LookupError as exc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
            ) from exc
    return PilotDetailResponse.model_validate(payload)


@router.get("/tenants", response_model=TenantListResponse)
async def tenants(
    _: Annotated[AuthenticatedUser, Depends(require_platform_operator)],
) -> TenantListResponse:
    """Every tenant with management fields — plan, classification, seat
    coverage, last activity. Pilots/live sort ahead of demo tenants."""
    async with SessionLocal() as session:
        rows = await list_tenants(session)
    return TenantListResponse(tenants=rows)


@router.patch("/tenants/{org_id}", response_model=TenantSummary)
async def classify_tenant(
    org_id: str,
    body: TenantClassifyInput,
    operator: Annotated[AuthenticatedUser, Depends(require_platform_operator)],
) -> TenantSummary:
    """Set a tenant's demo / pilot / live classification (a label only —
    it does not touch the tenant's data, plan, or RLS)."""
    async with SessionLocal() as session:
        try:
            payload = await update_tenant_classification(
                session, org_id=org_id, tenant_kind=body.tenant_kind, user=operator
            )
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
            ) from exc
        except LookupError as exc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
            ) from exc
    return TenantSummary.model_validate(payload)


@router.get("/system-health", response_model=SystemHealthResponse)
async def system_health(
    _: Annotated[AuthenticatedUser, Depends(require_platform_operator)],
) -> SystemHealthResponse:
    """Live component probes (auth/db/redis/storage/worker/ai) plus uptime
    % and active incidents — the operator System Health pane."""
    async with SessionLocal() as session:
        payload = await build_system_health(session)
    return SystemHealthResponse.model_validate(payload)
