import asyncio

import httpx
from redis import asyncio as redis_async
from sqlalchemy import text

from app.ai.registry import collect_provider_health
from app.config import Settings, get_settings
from app.database import engine
from app.schemas.system import ReadinessResponse, ServiceCheck
from app.tasks.celery_app import celery_app


def readiness_status(checks: list[ServiceCheck]) -> str:
    required_checks = [check for check in checks if check.required]
    return "ready" if all(check.status == "ok" for check in required_checks) else "not_ready"


async def probe_database() -> ServiceCheck:
    try:
        async with engine.connect() as connection:
            await connection.execute(text("select 1"))
    except Exception as exc:  # pragma: no cover - environment-dependent
        return ServiceCheck(
            name="database",
            status="error",
            required=True,
            detail=f"Database connectivity failed: {exc}",
        )

    return ServiceCheck(
        name="database",
        status="ok",
        required=True,
        detail="Database connection succeeded.",
    )


async def probe_redis(settings: Settings) -> ServiceCheck:
    client = redis_async.from_url(settings.redis_url, decode_responses=True)
    try:
        await client.ping()
    except Exception as exc:  # pragma: no cover - environment-dependent
        return ServiceCheck(
            name="redis",
            status="error",
            required=True,
            detail=f"Redis connectivity failed: {exc}",
            metadata={"url": settings.redis_url},
        )
    finally:
        await client.aclose()

    return ServiceCheck(
        name="redis",
        status="ok",
        required=True,
        detail="Redis connection succeeded.",
        metadata={"url": settings.redis_url},
    )


async def probe_storage(settings: Settings) -> ServiceCheck:
    if not settings.has_complete_storage_config():
        return ServiceCheck(
            name="storage",
            status="missing_config",
            required=True,
            detail="Supabase storage configuration is incomplete.",
        )

    headers = {
        "apikey": settings.supabase_service_role_key,
        "Authorization": f"Bearer {settings.supabase_service_role_key}",
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                f"{settings.supabase_url.rstrip('/')}/storage/v1/bucket",
                headers=headers,
            )
            response.raise_for_status()
            payload = response.json()
    except Exception as exc:  # pragma: no cover - environment-dependent
        return ServiceCheck(
            name="storage",
            status="error",
            required=True,
            detail=f"Supabase storage probe failed: {exc}",
        )

    bucket_names = {
        item.get("name") or item.get("id")
        for item in payload
        if isinstance(item, dict)
    }
    expected_buckets = {settings.storage_bucket_uploads, settings.storage_bucket_exports}
    missing_buckets = sorted(bucket for bucket in expected_buckets if bucket not in bucket_names)

    if missing_buckets:
        return ServiceCheck(
            name="storage",
            status="error",
            required=True,
            detail="Required storage buckets are missing.",
            metadata={"missing_buckets": missing_buckets},
        )

    return ServiceCheck(
        name="storage",
        status="ok",
        required=True,
        detail="Supabase storage buckets are reachable.",
        metadata={"buckets": sorted(expected_buckets)},
    )


def probe_auth(settings: Settings) -> ServiceCheck:
    if settings.has_complete_supabase_auth_config():
        return ServiceCheck(
            name="auth",
            status="ok",
            required=True,
            detail="Supabase JWT validation is configured.",
        )

    if settings.demo_mode_enabled():
        return ServiceCheck(
            name="auth",
            status="missing_config",
            required=True,
            detail="Demo mode is active; Supabase JWT validation is not configured.",
            metadata={"demo_mode": True, "demo_persona": settings.kestrel_demo_persona},
        )

    return ServiceCheck(
        name="auth",
        status="error",
        required=True,
        detail="Supabase auth configuration is incomplete.",
    )


async def probe_worker() -> ServiceCheck:
    try:
        ping_result = await asyncio.to_thread(lambda: celery_app.control.inspect(timeout=1.0).ping())
    except Exception as exc:  # pragma: no cover - environment-dependent
        return ServiceCheck(
            name="worker",
            status="error",
            required=True,
            detail=f"Worker heartbeat probe failed: {exc}",
        )

    if not ping_result:
        return ServiceCheck(
            name="worker",
            status="error",
            required=True,
            detail="No Celery workers responded to the heartbeat probe.",
        )

    return ServiceCheck(
        name="worker",
        status="ok",
        required=True,
        detail="Celery worker heartbeat confirmed.",
        metadata={"workers": sorted(ping_result.keys())},
    )


async def probe_ai_providers(settings: Settings) -> list[ServiceCheck]:
    provider_health = await collect_provider_health(settings)
    return [
        ServiceCheck(
            name=f"ai:{provider.provider}",
            status=provider.status,
            required=False,
            detail=provider.detail,
            metadata=provider.metadata | {"configured": provider.configured, "reachable": provider.reachable},
        )
        for provider in provider_health
    ]


async def build_readiness_report(settings: Settings | None = None) -> ReadinessResponse:
    runtime_settings = settings or get_settings()
    checks = [
        probe_auth(runtime_settings),
        await probe_database(),
        await probe_redis(runtime_settings),
        await probe_storage(runtime_settings),
        await probe_worker(),
        *await probe_ai_providers(runtime_settings),
    ]

    return ReadinessResponse(
        status=readiness_status(checks),
        version=runtime_settings.app_version,
        environment=runtime_settings.environment,
        checks=checks,
    )
