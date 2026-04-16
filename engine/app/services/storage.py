"""Supabase Storage client — thin httpx wrapper, no SDK.

Writes raw bytes to the uploads bucket via the Supabase Storage REST API.
Non-critical: failures are logged and raised, but callers can choose to
swallow them (the DB write is the authoritative source of truth).
"""

from __future__ import annotations

import httpx

from app.config import Settings, get_settings


class StorageError(RuntimeError):
    pass


async def upload_to_uploads_bucket(
    *,
    path: str,
    content: bytes,
    content_type: str = "text/csv",
    settings: Settings | None = None,
) -> str:
    """Upload `content` to `{bucket}/{path}`. Returns the storage path on success."""
    settings = settings or get_settings()
    if not settings.supabase_url or not settings.supabase_service_role_key:
        raise StorageError("Supabase storage is not configured.")

    bucket = settings.storage_bucket_uploads
    url = f"{settings.supabase_url.rstrip('/')}/storage/v1/object/{bucket}/{path.lstrip('/')}"
    headers = {
        "apikey": settings.supabase_service_role_key,
        "Authorization": f"Bearer {settings.supabase_service_role_key}",
        "Content-Type": content_type,
        "x-upsert": "true",
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.put(url, content=content, headers=headers)

    if response.status_code >= 400:
        raise StorageError(
            f"Supabase Storage upload failed ({response.status_code}): {response.text[:200]}"
        )

    return f"{bucket}/{path.lstrip('/')}"
