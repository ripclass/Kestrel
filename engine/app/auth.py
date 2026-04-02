from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt

from app.config import get_settings

settings = get_settings()
bearer = HTTPBearer(auto_error=False)


@dataclass(slots=True)
class AuthenticatedUser:
    user_id: str
    email: str
    org_id: str
    org_type: str
    role: str
    persona: str
    designation: str


DEMO_USERS = {
    "bfiu_analyst": AuthenticatedUser(
        user_id="viewer-analyst",
        email="analyst@bfiu.gov.bd",
        org_id="org-bfiu",
        org_type="regulator",
        role="analyst",
        persona="bfiu_analyst",
        designation="Deputy Director, Intelligence Analysis",
    ),
    "bank_camlco": AuthenticatedUser(
        user_id="viewer-bank",
        email="camlco@sonali.example",
        org_id="org-sonali",
        org_type="bank",
        role="manager",
        persona="bank_camlco",
        designation="Chief AML Compliance Officer",
    ),
    "bfiu_director": AuthenticatedUser(
        user_id="viewer-director",
        email="director@bfiu.gov.bd",
        org_id="org-bfiu",
        org_type="regulator",
        role="admin",
        persona="bfiu_director",
        designation="Director, BFIU",
    ),
}


def _demo_user() -> AuthenticatedUser:
    return DEMO_USERS.get(settings.kestrel_demo_persona, DEMO_USERS["bfiu_analyst"])


def decode_access_token(token: str) -> AuthenticatedUser:
    if not settings.has_complete_supabase_auth_config():
        if settings.demo_mode_enabled():
            return _demo_user()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Supabase JWT validation is not configured.",
        )

    try:
        payload = jwt.decode(token, settings.supabase_jwt_secret, algorithms=["HS256"])
    except JWTError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token") from exc

    persona = payload.get("persona") or payload.get("user_metadata", {}).get("persona") or "bfiu_analyst"
    return AuthenticatedUser(
        user_id=str(payload.get("sub")),
        email=str(payload.get("email", _demo_user().email)),
        org_id=str(payload.get("org_id", _demo_user().org_id)),
        org_type=str(payload.get("org_type", _demo_user().org_type)),
        role=str(payload.get("role", _demo_user().role)),
        persona=str(persona),
        designation=str(payload.get("designation", _demo_user().designation)),
    )


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
) -> AuthenticatedUser:
    if credentials is None:
        if settings.demo_mode_enabled():
            return _demo_user()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")

    return decode_access_token(credentials.credentials)


def require_roles(*roles: str):
    async def _dependency(user: Annotated[AuthenticatedUser, Depends(get_current_user)]) -> AuthenticatedUser:
        if user.role not in roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role")
        return user

    return _dependency
