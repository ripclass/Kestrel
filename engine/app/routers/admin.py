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
from app.schemas.statistics import OperationalStatisticsResponse
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
from app.services.schedules import ScheduleListResponse, build_schedule_list
from app.services.statistics import build_operational_statistics
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
    return await build_rule_catalog(session, user=user)


@router.patch("/rules/{code}", response_model=AdminRuleMutationResponse)
async def update_rule(
    code: str,
    payload: AdminRuleMutationRequest,
    user: Annotated[AuthenticatedUser, Depends(require_roles("manager", "admin", "superadmin"))],
) -> AdminRuleMutationResponse:
    try:
        return await update_rule_configuration(user=user, code=code, payload=payload)
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


@router.get("/statistics", response_model=OperationalStatisticsResponse)
async def operational_statistics(
    user: Annotated[AuthenticatedUser, Depends(require_roles("analyst", "manager", "admin", "superadmin"))],
    session: Annotated[AsyncSession, Depends(get_current_session)],
) -> OperationalStatisticsResponse:
    _require_regulator_admin(user)
    return await build_operational_statistics(session, user=user)


@router.get("/schedules", response_model=ScheduleListResponse)
async def scheduled_processes(
    user: Annotated[AuthenticatedUser, Depends(require_roles("admin", "superadmin"))],
) -> ScheduleListResponse:
    _require_regulator_admin(user)
    return build_schedule_list()


@router.get("/screening/outbound-probe")
async def screening_outbound_probe(
    user: Annotated[AuthenticatedUser, Depends(require_roles("admin", "superadmin"))],
) -> dict:
    """V2 P4 watchlist outbound verification.

    Streams a small GET against each upstream sanctions feed and reads
    only the first 256 bytes — confirms Render network egress + the URL
    is alive + the body looks like the expected format (XML/CSV) without
    pulling the full multi-MB payload. Some endpoints (UN consolidated)
    reject HEAD requests entirely, so HEAD is unreliable for this probe;
    GET with an early close is the right shape."""
    import time

    import httpx

    from app.screening.sources import ofac, uk_ofsi, un

    _require_regulator_admin(user)
    targets = [
        (ofac.LIST_SOURCE, ofac.FEED_URL),
        (un.LIST_SOURCE, un.FEED_URL),
        (uk_ofsi.LIST_SOURCE, uk_ofsi.FEED_URL),
    ]
    results: list[dict] = []
    async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
        for source, url in targets:
            t0 = time.perf_counter()
            entry: dict = {"source": source, "url": url}
            try:
                async with client.stream("GET", url) as resp:
                    entry["status_code"] = resp.status_code
                    entry["content_length"] = resp.headers.get("content-length")
                    entry["content_type"] = resp.headers.get("content-type")
                    sample = b""
                    async for chunk in resp.aiter_bytes(chunk_size=256):
                        sample = chunk
                        break  # first chunk is enough; close stream early
                    entry["body_preview"] = sample[:128].decode("utf-8", errors="replace")
                    entry["latency_ms"] = int((time.perf_counter() - t0) * 1000)
                    entry["reachable"] = resp.status_code < 500 and bool(sample)
                    entry["body_looks_like_expected"] = _shape_check(source, sample)
            except httpx.RequestError as exc:
                entry["reachable"] = False
                entry["error_type"] = type(exc).__name__
                entry["error"] = str(exc)[:200]
                entry["latency_ms"] = int((time.perf_counter() - t0) * 1000)
            results.append(entry)
    return {
        "ingestion_enabled_env": settings_module_value("kestrel_watchlist_ingestion_enabled"),
        "results": results,
    }


@router.get("/screening/adverse-media-probe")
async def screening_adverse_media_probe(
    user: Annotated[AuthenticatedUser, Depends(require_roles("admin", "superadmin"))],
) -> dict:
    """Validate the ComplyAdvantage API key once it's set on Render.

    Reports configuration state and (when configured) runs a single
    benign search against the live API. Operators hit this immediately
    after setting `COMPLYADVANTAGE_API_KEY` to confirm the key works
    before user traffic depends on it. No business data sent — query
    string is the literal `health-probe`."""
    import time

    from app.services import adverse_media

    _require_regulator_admin(user)
    if not adverse_media.is_provider_configured():
        return {
            "configured": False,
            "provider": "stub",
            "note": "Set COMPLYADVANTAGE_API_KEY on engine + worker + beat to enable.",
        }

    t0 = time.perf_counter()
    try:
        hits = await adverse_media.search_adverse_media(
            adverse_media.AdverseMediaQuery(name="health-probe")
        )
        return {
            "configured": True,
            "provider": "complyadvantage",
            "reachable": True,
            "latency_ms": int((time.perf_counter() - t0) * 1000),
            "hit_count": len(hits),
            "note": "Key validated; hit_count is the count for the literal probe term and is expected to be small/zero.",
        }
    except Exception as exc:  # noqa: BLE001 — operator-facing surface
        return {
            "configured": True,
            "provider": "complyadvantage",
            "reachable": False,
            "error_type": type(exc).__name__,
            "error": str(exc)[:300],
            "latency_ms": int((time.perf_counter() - t0) * 1000),
        }


@router.post("/screening/refresh-now")
async def screening_refresh_now(
    user: Annotated[AuthenticatedUser, Depends(require_roles("admin", "superadmin"))],
) -> dict:
    """Trigger the daily watchlist refresh task immediately on the worker.

    Returns the Celery task_id so the operator can correlate with worker
    logs. The actual ingestion runs async on the worker; query
    watchlist_entries 60-90s later to confirm rows landed."""
    _require_regulator_admin(user)
    from app.tasks.screening_tasks import refresh_all

    async_result = refresh_all.delay()
    return {
        "task_id": async_result.id,
        "task": "app.tasks.screening_tasks.refresh_all",
        "note": "Async dispatch. Watch worker logs for `watchlist.ingestion.batch` or `watchlist.source.*`. Query watchlist_entries in 60-90s to confirm.",
    }


@router.get("/screening/refresh-status/{task_id}")
async def screening_refresh_status(
    task_id: str,
    user: Annotated[AuthenticatedUser, Depends(require_roles("admin", "superadmin"))],
) -> dict:
    """Read the AsyncResult for a previously dispatched refresh task."""
    _require_regulator_admin(user)
    from app.tasks.celery_app import celery_app

    result = celery_app.AsyncResult(task_id)
    payload: dict = {"task_id": task_id, "state": result.state, "ready": result.ready()}
    if result.ready():
        try:
            payload["result"] = result.result
        except Exception as exc:  # noqa: BLE001 — surface raw error to operator
            payload["error"] = str(exc)[:300]
    return payload


def _shape_check(source: str, sample: bytes) -> bool:
    """Quick sanity that the first bytes match the expected format. Catches
    the case where a feed URL serves an HTML wrapper page instead of XML/CSV."""
    if not sample:
        return False
    text = sample.lstrip().lower()
    if source in ("OFAC", "UN"):
        return text.startswith(b"<?xml") or text.startswith(b"<sdnlist") or text.startswith(b"<consolidated")
    if source == "UK_OFSI":
        # Header row begins with "Last Updated," in the new unified format.
        return b"," in sample[:200] and not text.startswith(b"<!doctype") and not text.startswith(b"<html")
    return True


def settings_module_value(_name: str) -> bool:
    """Read the env-flag the way the Beat task does, without importing
    Settings (Settings ignores extras so `kestrel_watchlist_ingestion_enabled`
    isn't on the model — the Beat task reads `os.environ` directly)."""
    import os

    return os.environ.get("KESTREL_WATCHLIST_INGESTION_ENABLED", "false").lower() == "true"
