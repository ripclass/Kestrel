from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

ENGINE_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_ENV_FILES = (
    str(REPO_ROOT / ".env"),
    str(REPO_ROOT / ".env.local"),
    str(ENGINE_ROOT / ".env"),
    str(ENGINE_ROOT / ".env.local"),
)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=DEFAULT_ENV_FILES,
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "Kestrel Engine"
    app_version: str = "0.1.0"
    environment: str = "development"
    engine_port: int = 8000
    allowed_origins: str = "http://localhost:3000"

    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/postgres"
    redis_url: str = "redis://localhost:6379/0"

    supabase_url: str | None = None
    supabase_anon_key: str | None = None
    supabase_service_role_key: str | None = None
    supabase_jwt_secret: str | None = None
    supabase_jwks_url: str | None = None

    storage_bucket_uploads: str = "kestrel-uploads"
    storage_bucket_exports: str = "kestrel-exports"

    kestrel_enable_demo_mode: bool = False
    goaml_sync_enabled: bool = False
    goaml_base_url: str | None = None
    goaml_api_key: str | None = None

    kestrel_demo_persona: str = "bfiu_analyst"
    ai_enable_external_probes: bool = False
    ai_provider_timeout_seconds: float = 5.0
    ai_redaction_mode: str = "redact"
    ai_fallback_enabled: bool = True
    openai_api_key: str | None = None
    openai_base_url: str = "https://api.openai.com/v1"
    openai_organization: str | None = None
    openai_model: str | None = None
    anthropic_api_key: str | None = None
    anthropic_base_url: str = "https://api.anthropic.com"
    anthropic_version: str = "2023-06-01"
    anthropic_model: str | None = None

    complyadvantage_api_key: str | None = None
    complyadvantage_base_url: str = "https://api.complyadvantage.com"

    # V3 phase 2: sovereign Bangladesh-trained model. No-op until V3 P4
    # lands the first adapter. When configured, the routing layer
    # prepends a sovereign route at index 0 of every task chain.
    ai_sovereign_url: str | None = None
    ai_sovereign_api_key: str | None = None
    ai_sovereign_model: str | None = None
    ai_sovereign_threshold_default: float = 1.01

    # V3 phase 6: on-prem deployment mode. "cloud" is the default Render
    # deployment; "onprem" hardens the engine for air-gapped customer
    # environments — disables outbound AI providers (OpenAI/Anthropic),
    # disables live watchlist ingestion, defaults telemetry off.
    kestrel_deployment_mode: str = "cloud"
    kestrel_license_file: str | None = None
    kestrel_telemetry_enabled: bool = False
    kestrel_telemetry_url: str | None = None

    def is_onprem(self) -> bool:
        return self.kestrel_deployment_mode.lower() == "onprem"

    def cors_origin_list(self) -> list[str]:
        return [item.strip() for item in self.allowed_origins.split(",") if item.strip()]

    def has_any_supabase_auth_config(self) -> bool:
        return any(
            [
                self.supabase_url,
                self.supabase_anon_key,
                self.supabase_service_role_key,
                self.supabase_jwt_secret,
            ]
        )

    def has_complete_supabase_auth_config(self) -> bool:
        return bool(self.supabase_jwt_secret or self.supabase_url)

    def resolved_supabase_jwks_url(self) -> str | None:
        if self.supabase_jwks_url:
            return self.supabase_jwks_url
        if not self.supabase_url:
            return None
        return f"{self.supabase_url.rstrip('/')}/auth/v1/.well-known/jwks.json"

    def resolved_supabase_issuer(self) -> str | None:
        if not self.supabase_url:
            return None
        return f"{self.supabase_url.rstrip('/')}/auth/v1"

    def has_complete_storage_config(self) -> bool:
        return bool(
            self.supabase_url
            and self.supabase_service_role_key
            and self.storage_bucket_uploads
            and self.storage_bucket_exports
        )

    def demo_mode_enabled(self) -> bool:
        if self.kestrel_enable_demo_mode:
            return True
        return not self.has_any_supabase_auth_config()


@lru_cache
def get_settings() -> Settings:
    return Settings()
