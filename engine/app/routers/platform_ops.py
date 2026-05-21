"""Platform-operator console — cross-tenant pilot-health surface.

Enso-internal. Gated by ``require_platform_operator`` (operator email
allow-list), *not* the per-tenant role model — a bank or BFIU customer
must never see pilot-engagement telemetry across other tenants.

Reads run on the plain ``SessionLocal`` (engine connects as ``postgres``
/ BYPASSRLS) because the whole point of this surface is cross-tenant
visibility, which RLS denies normal sessions.
"""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.auth import AuthenticatedUser, require_platform_operator
from app.database import SessionLocal
from app.schemas.platform_ops import PilotDetailResponse, PilotOverviewResponse
from app.services.platform_ops import build_pilot_detail, build_pilot_overview

router = APIRouter()


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
