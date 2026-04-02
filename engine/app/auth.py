import time
from dataclasses import dataclass
from typing import Annotated

import httpx
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwk, jwt
from jose.utils import base64url_decode
from sqlalchemy import text

from app.database import SessionLocal

from app.config import get_settings

settings = get_settings()
bearer = HTTPBearer(auto_error=False)
_JWKS_CACHE_TTL_SECONDS = 600
_jwks_cache: dict[str, tuple[float, list[dict[str, object]]]] = {}


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


def _claim(payload: dict[str, object], key: str) -> object | None:
    if key in payload:
        return payload.get(key)

    user_metadata = payload.get("user_metadata")
    if isinstance(user_metadata, dict) and key in user_metadata:
        return user_metadata.get(key)

    app_metadata = payload.get("app_metadata")
    if isinstance(app_metadata, dict) and key in app_metadata:
        return app_metadata.get(key)

    return None


async def _load_profile_context(user_id: str) -> dict[str, object] | None:
    query = text(
        """
        select
            p.id,
            p.org_id,
            p.full_name,
            p.role,
            p.persona,
            p.designation,
            o.name as org_name,
            o.org_type
        from profiles p
        join organizations o on o.id = p.org_id
        where p.id = cast(:user_id as uuid)
        limit 1
        """
    )

    async with SessionLocal() as session:
        try:
            result = await session.execute(query, {"user_id": user_id})
        except Exception:
            return None

    row = result.mappings().first()
    return dict(row) if row else None


async def _fetch_jwks(jwks_url: str) -> list[dict[str, object]]:
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get(jwks_url)
        response.raise_for_status()
    payload = response.json()
    keys = payload.get("keys")
    if not isinstance(keys, list):
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Supabase JWKS response is invalid.")
    return [key for key in keys if isinstance(key, dict)]


async def _get_jwks(force_refresh: bool = False) -> list[dict[str, object]]:
    jwks_url = settings.resolved_supabase_jwks_url()
    if not jwks_url:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Supabase JWKS URL is not configured.",
        )

    now = time.time()
    cached = _jwks_cache.get(jwks_url)
    if cached and not force_refresh and now - cached[0] < _JWKS_CACHE_TTL_SECONDS:
        return cached[1]

    try:
        keys = await _fetch_jwks(jwks_url)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Unable to fetch Supabase JWKS: {exc}",
        ) from exc

    _jwks_cache[jwks_url] = (now, keys)
    return keys


def _validate_standard_claims(payload: dict[str, object]) -> None:
    now = time.time()
    issuer = settings.resolved_supabase_issuer()

    exp = payload.get("exp")
    if exp is not None and now >= float(exp):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token has expired")

    nbf = payload.get("nbf")
    if nbf is not None and now < float(nbf):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token is not yet valid")

    if issuer and payload.get("iss") not in (issuer, None):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token issuer")


def _decode_with_jwk(token: str, jwk_payload: dict[str, object]) -> dict[str, object]:
    try:
        header = jwt.get_unverified_header(token)
        segments = token.split(".")
        if len(segments) != 3:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token format")
        signing_input = ".".join(segments[0:2]).encode("utf-8")
        signature = base64url_decode(segments[2].encode("utf-8"))
        key = jwk.construct(jwk_payload, algorithm=header.get("alg"))
        if not key.verify(signing_input, signature):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token signature")
        payload = jwt.get_unverified_claims(token)
        _validate_standard_claims(payload)
        return payload
    except HTTPException:
        raise
    except JWTError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token") from exc
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token") from exc


async def decode_access_token(token: str) -> dict[str, object]:
    if not settings.has_complete_supabase_auth_config():
        if settings.demo_mode_enabled():
            return {
                "sub": _demo_user().user_id,
                "email": _demo_user().email,
                "org_id": _demo_user().org_id,
                "org_type": _demo_user().org_type,
                "role": _demo_user().role,
                "persona": _demo_user().persona,
                "designation": _demo_user().designation,
                "full_name": _demo_user().designation,
            }
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Supabase JWT validation is not configured.",
        )

    if settings.supabase_jwt_secret:
        try:
            payload = jwt.decode(
                token,
                settings.supabase_jwt_secret,
                algorithms=["HS256"],
                options={"verify_aud": False},
            )
        except JWTError as exc:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token") from exc
        return payload

    try:
        header = jwt.get_unverified_header(token)
    except JWTError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token") from exc
    kid = header.get("kid")
    keys = await _get_jwks()
    jwk_payload = next((candidate for candidate in keys if candidate.get("kid") == kid), None)

    if jwk_payload is None:
        keys = await _get_jwks(force_refresh=True)
        jwk_payload = next((candidate for candidate in keys if candidate.get("kid") == kid), None)
        if jwk_payload is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="No matching Supabase signing key found")

    return _decode_with_jwk(token, jwk_payload)


async def resolve_authenticated_user(payload: dict[str, object]) -> AuthenticatedUser:
    fallback = _demo_user()
    user_id = str(payload.get("sub") or fallback.user_id)
    email = str(payload.get("email") or fallback.email)
    profile_context = await _load_profile_context(user_id)

    if profile_context:
        return AuthenticatedUser(
            user_id=user_id,
            email=email,
            org_id=str(profile_context.get("org_id")),
            org_type=str(profile_context.get("org_type")),
            role=str(profile_context.get("role") or fallback.role),
            persona=str(profile_context.get("persona") or fallback.persona),
            designation=str(profile_context.get("designation") or fallback.designation),
        )

    org_id = _claim(payload, "org_id")
    org_type = _claim(payload, "org_type")
    role = _claim(payload, "role")
    persona = _claim(payload, "persona")
    designation = _claim(payload, "designation")

    if org_id and org_type and role:
        return AuthenticatedUser(
            user_id=user_id,
            email=email,
            org_id=str(org_id),
            org_type=str(org_type),
            role=str(role),
            persona=str(persona or fallback.persona),
            designation=str(designation or fallback.designation),
        )

    if settings.demo_mode_enabled():
        return fallback

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="No Kestrel profile is provisioned for this user.",
    )


async def authenticate_token(token: str) -> AuthenticatedUser:
    payload = await decode_access_token(token)
    if payload.get("sub") == _demo_user().user_id and settings.demo_mode_enabled():
        return _demo_user()
    return await resolve_authenticated_user(payload)


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
) -> AuthenticatedUser:
    if credentials is None:
        if settings.demo_mode_enabled():
            return _demo_user()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")

    return await authenticate_token(credentials.credentials)


def require_roles(*roles: str):
    async def _dependency(user: Annotated[AuthenticatedUser, Depends(get_current_user)]) -> AuthenticatedUser:
        if user.role not in roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role")
        return user

    return _dependency
