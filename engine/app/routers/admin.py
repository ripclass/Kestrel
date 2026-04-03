import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import AuthenticatedUser, require_roles
from app.config import get_settings
from app.dependencies import get_current_session
from app.schemas.admin import (
    AdminMaintenanceResponse,
    AdminIntegrationsResponse,
    AdminRuleMutationRequest,
    AdminRuleMutationResponse,
    AdminRulesResponse,
    AdminSettingsResponse,
    AdminSummaryResponse,
    AdminTeamMutationResponse,
    AdminTeamResponse,
    AdminTeamUpdateRequest,
    SyntheticBackfillPlanResponse,
    SyntheticBackfillResultResponse,
)
from app.services.admin import (
    apply_rules_insert_policy_fix,
    build_admin_integrations,
    build_admin_settings,
    build_admin_summary,
    build_synthetic_backfill_plan,
    build_rule_catalog,
    build_team_directory,
    normalize_synthetic_backfill_result,
    update_rule_configuration,
    update_team_member,
)
from seed.dbbl_synthetic import OUTPUT_DIR_DEFAULT
from seed.load_dbbl_synthetic import apply_dataset

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


@router.patch("/team/{member_id}", response_model=AdminTeamMutationResponse)
async def update_team(
    member_id: str,
    payload: AdminTeamUpdateRequest,
    user: Annotated[AuthenticatedUser, Depends(require_roles("manager", "admin", "superadmin"))],
    session: Annotated[AsyncSession, Depends(get_current_session)],
) -> AdminTeamMutationResponse:
    try:
        return await update_team_member(session, user=user, member_id=member_id, payload=payload)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get("/rules", response_model=AdminRulesResponse)
async def rules(
    user: Annotated[AuthenticatedUser, Depends(require_roles("manager", "admin", "superadmin"))],
    session: Annotated[AsyncSession, Depends(get_current_session)],
) -> AdminRulesResponse:
    return await build_rule_catalog(session)


@router.patch("/rules/{code}", response_model=AdminRuleMutationResponse)
async def update_rule(
    code: str,
    payload: AdminRuleMutationRequest,
    user: Annotated[AuthenticatedUser, Depends(require_roles("manager", "admin", "superadmin"))],
    session: Annotated[AsyncSession, Depends(get_current_session)],
) -> AdminRuleMutationResponse:
    try:
        return await update_rule_configuration(session, user=user, code=code, payload=payload)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Rule update failed.")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"{exc.__class__.__name__}: {exc}",
        ) from exc


@router.get("/api-keys", response_model=AdminIntegrationsResponse)
async def api_keys(
    user: Annotated[AuthenticatedUser, Depends(require_roles("manager", "admin", "superadmin"))],
) -> AdminIntegrationsResponse:
    return await build_admin_integrations(user=user, settings=settings)


@router.get("/synthetic-backfill", response_model=SyntheticBackfillPlanResponse)
async def synthetic_backfill_plan(
    user: Annotated[AuthenticatedUser, Depends(require_roles("admin", "superadmin"))],
) -> SyntheticBackfillPlanResponse:
    _require_regulator_admin(user)
    return build_synthetic_backfill_plan()


@router.post("/synthetic-backfill", response_model=SyntheticBackfillResultResponse)
async def apply_synthetic_backfill(
    user: Annotated[AuthenticatedUser, Depends(require_roles("admin", "superadmin"))],
) -> SyntheticBackfillResultResponse:
    _require_regulator_admin(user)
    try:
        return normalize_synthetic_backfill_result(await apply_dataset(OUTPUT_DIR_DEFAULT))
    except Exception as exc:
        logger.exception("Synthetic backfill failed.")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Synthetic backfill failed. Check engine logs for details.",
        ) from exc


@router.post("/maintenance/rules-policy-fix", response_model=AdminMaintenanceResponse)
async def apply_rules_policy_fix(
    user: Annotated[AuthenticatedUser, Depends(require_roles("admin", "superadmin"))],
) -> AdminMaintenanceResponse:
    _require_regulator_admin(user)
    try:
        return await apply_rules_insert_policy_fix()
    except Exception as exc:
        logger.exception("Rules policy fix failed.")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Rules policy fix failed. Check engine logs for details.",
        ) from exc
