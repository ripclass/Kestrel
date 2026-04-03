import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import AuthenticatedUser, require_roles
from app.config import get_settings
from app.dependencies import get_current_session
from app.schemas.admin import (
    AdminIntegrationsResponse,
    AdminRulesResponse,
    AdminSettingsResponse,
    AdminSummaryResponse,
    AdminTeamResponse,
)
from app.services.admin import (
    build_admin_integrations,
    build_admin_settings,
    build_admin_summary,
    build_rule_catalog,
    build_team_directory,
)
from seed.dbbl_synthetic import OUTPUT_DIR_DEFAULT
from seed.load_dbbl_synthetic import apply_dataset, build_load_plan

router = APIRouter()
logger = logging.getLogger(__name__)
settings = get_settings()


def _require_regulator_admin(user: AuthenticatedUser) -> AuthenticatedUser:
    if user.org_type != "regulator":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Synthetic backfill is limited to regulator administrators.",
        )
    return user


@router.get("/summary", response_model=AdminSummaryResponse)
async def summary(
    user: Annotated[AuthenticatedUser, Depends(require_roles("manager", "admin", "superadmin"))],
    session: Annotated[AsyncSession, Depends(get_current_session)],
) -> AdminSummaryResponse:
    return await build_admin_summary(session, user=user, settings=settings)


@router.get("/settings", response_model=AdminSettingsResponse)
async def settings_summary(
    user: Annotated[AuthenticatedUser, Depends(require_roles("manager", "admin", "superadmin"))],
    session: Annotated[AsyncSession, Depends(get_current_session)],
) -> AdminSettingsResponse:
    return await build_admin_settings(session, user=user, settings=settings)


@router.get("/team", response_model=AdminTeamResponse)
async def team(
    user: Annotated[AuthenticatedUser, Depends(require_roles("manager", "admin", "superadmin"))],
    session: Annotated[AsyncSession, Depends(get_current_session)],
) -> AdminTeamResponse:
    return await build_team_directory(session, user=user)


@router.get("/rules", response_model=AdminRulesResponse)
async def rules(
    user: Annotated[AuthenticatedUser, Depends(require_roles("manager", "admin", "superadmin"))],
    session: Annotated[AsyncSession, Depends(get_current_session)],
) -> AdminRulesResponse:
    return await build_rule_catalog(session)


@router.get("/api-keys", response_model=AdminIntegrationsResponse)
async def api_keys(
    user: Annotated[AuthenticatedUser, Depends(require_roles("manager", "admin", "superadmin"))],
) -> AdminIntegrationsResponse:
    return await build_admin_integrations(user=user, settings=settings)


@router.get("/synthetic-backfill")
async def synthetic_backfill_plan(
    user: Annotated[AuthenticatedUser, Depends(require_roles("admin", "superadmin"))],
) -> dict[str, object]:
    _require_regulator_admin(user)
    return build_load_plan(OUTPUT_DIR_DEFAULT)


@router.post("/synthetic-backfill")
async def apply_synthetic_backfill(
    user: Annotated[AuthenticatedUser, Depends(require_roles("admin", "superadmin"))],
) -> dict[str, object]:
    _require_regulator_admin(user)
    try:
        return await apply_dataset(OUTPUT_DIR_DEFAULT)
    except Exception as exc:
        logger.exception("Synthetic backfill failed.")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Synthetic backfill failed. Check engine logs for details.",
        ) from exc
