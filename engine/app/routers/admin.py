from typing import Annotated

from fastapi import APIRouter, Depends

from app.auth import AuthenticatedUser, require_roles

router = APIRouter()


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
