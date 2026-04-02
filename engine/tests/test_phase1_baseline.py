import asyncio

from app.ai.registry import collect_provider_health
from app.config import Settings
from app.schemas.system import ServiceCheck
from app.services.readiness import readiness_status


def build_settings(**overrides) -> Settings:
    base = {
        "app_name": "Kestrel Engine",
        "app_version": "0.1.0",
        "environment": "test",
        "engine_port": 8000,
        "allowed_origins": "http://localhost:3000",
        "database_url": "postgresql+asyncpg://postgres:postgres@localhost:5432/postgres",
        "redis_url": "redis://localhost:6379/0",
        "storage_bucket_uploads": "kestrel-uploads",
        "storage_bucket_exports": "kestrel-exports",
        "kestrel_enable_demo_mode": False,
        "kestrel_demo_persona": "bfiu_analyst",
        "ai_enable_external_probes": False,
        "ai_provider_timeout_seconds": 5.0,
        "ai_redaction_mode": "redact",
        "openai_base_url": "https://api.openai.com/v1",
        "anthropic_base_url": "https://api.anthropic.com",
        "anthropic_version": "2023-06-01",
    }
    base.update(overrides)
    return Settings.model_validate(base)


def test_demo_mode_defaults_only_when_no_supabase_auth_config() -> None:
    no_auth = build_settings()
    assert no_auth.demo_mode_enabled() is True

    partial_auth = build_settings(supabase_url="https://example.supabase.co")
    assert partial_auth.demo_mode_enabled() is False

    explicit_demo = build_settings(
        supabase_url="https://example.supabase.co",
        kestrel_enable_demo_mode=True,
    )
    assert explicit_demo.demo_mode_enabled() is True


def test_provider_health_reports_missing_config_without_keys() -> None:
    health = asyncio.run(collect_provider_health(build_settings()))
    assert [item.provider for item in health] == ["openai", "anthropic"]
    assert all(item.status == "missing_config" for item in health)


def test_provider_health_marks_configured_providers_as_skipped_when_probes_disabled() -> None:
    settings = build_settings(
        openai_api_key="test-openai",
        openai_model="gpt-test",
        anthropic_api_key="test-anthropic",
        anthropic_model="claude-test",
    )
    health = asyncio.run(collect_provider_health(settings))
    assert all(item.status == "skipped" for item in health)
    assert all(item.configured is True for item in health)


def test_readiness_status_requires_all_required_checks_to_be_ok() -> None:
    ready = readiness_status(
        [
            ServiceCheck(name="database", status="ok", required=True, detail="ok"),
            ServiceCheck(name="auth", status="ok", required=True, detail="ok"),
            ServiceCheck(name="ai:openai", status="missing_config", required=False, detail="optional"),
        ]
    )
    not_ready = readiness_status(
        [
            ServiceCheck(name="database", status="ok", required=True, detail="ok"),
            ServiceCheck(name="auth", status="missing_config", required=True, detail="not configured"),
        ]
    )

    assert ready == "ready"
    assert not_ready == "not_ready"
