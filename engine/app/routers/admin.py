from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.auth import AuthenticatedUser, require_roles
from seed.dbbl_synthetic import OUTPUT_DIR_DEFAULT
from seed.load_dbbl_synthetic import apply_dataset, build_load_plan

router = APIRouter()


def _require_regulator_admin(user: AuthenticatedUser) -> AuthenticatedUser:
    if user.org_type != "regulator":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Synthetic backfill is limited to regulator administrators.",
        )
    return user


@router.get("/summary")
async def summary(
    user: Annotated[AuthenticatedUser, Depends(require_roles("manager", "admin", "superadmin"))],
) -> dict[str, object]:
    return {
        "goaml_sync_enabled": False,
        "api_keys": 2,
        "rules": 8,
        "team_members": 3,
    }


@router.get("/api-keys")
async def api_keys(
    user: Annotated[AuthenticatedUser, Depends(require_roles("manager", "admin", "superadmin"))],
) -> list[dict[str, object]]:
    return [
        {"name": "Case Export Integration", "scope": ["reports:write", "cases:read"]},
        {"name": "goAML Sandbox Adapter", "scope": ["str:sync", "matches:read"]},
    ]


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
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Synthetic backfill failed: {exc.__class__.__name__}: {exc}",
        ) from exc
