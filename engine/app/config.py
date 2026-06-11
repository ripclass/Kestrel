import json
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
    # Expected `aud` claim on Supabase access tokens. Empty string disables
    # the audience check (escape hatch for non-Supabase token issuers).
    supabase_jwt_aud: str = "authenticated"

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
    # Prompt caching: when true, adapters mark stable prompt prefixes
    # (system_prompt + TASK + GUIDANCE + OUTPUT_SCHEMA) with provider
    # cache_control hints so the upstream API can re-use the cached
    # prefix at ~90% discount. Volatile per-call INPUT stays uncached.
    # Disable via env var if a provider misbehaves.
    ai_prompt_cache_enabled: bool = True
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

    # V3 phase 7: audit-log retention.
    audit_log_retention_days: int = 365
    kestrel_audit_archive_bucket: str | None = None

    # Platform-operator console: comma-separated allow-list of Enso operator
    # emails. The cross-tenant operator surface (`/platform/*`) is gated on
    # membership. Empty => no one has access (fail-closed). This is an
    # Enso-internal gate — distinct from the per-tenant `bank`/`regulator`
    # role model — so BFIU and bank customers never see pilot telemetry.
    kestrel_platform_operators: str = ""
    # Optional per-operator role map (JSON: {"email": "role"}). Roles gate
    # which operator-console modules each Enso team member sees — see
    # docs/internal/operations-readiness.md §6. Any allow-listed operator not
    # named here defaults to `owner` (today the founder is the only operator).
    kestrel_platform_operator_roles: str = ""

    def is_onprem(self) -> bool:
        return self.kestrel_deployment_mode.lower() == "onprem"

    def platform_operator_emails(self) -> set[str]:
        """Lower-cased, whitespace-trimmed operator email allow-list."""
        return {
            item.strip().lower()
            for item in self.kestrel_platform_operators.split(",")
            if item.strip()
        }

    def is_platform_operator(self, email: str | None) -> bool:
        if not email:
            return False
        return email.strip().lower() in self.platform_operator_emails()

    def platform_operator_role(self, email: str | None) -> str | None:
        """Resolve an operator's console role.

        Returns the mapped role from ``kestrel_platform_operator_roles`` if
        present; otherwise ``owner`` for any allow-listed operator without an
        explicit mapping; ``None`` for non-operators. Fail-safe: a malformed
        role JSON degrades to "every operator is owner" rather than locking
        the founder out.
        """
        if not self.is_platform_operator(email):
            return None
        assert email is not None
        normalized = email.strip().lower()
        raw = (self.kestrel_platform_operator_roles or "").strip()
        if raw:
            try:
                mapping = json.loads(raw)
                if isinstance(mapping, dict):
                    role = mapping.get(normalized)
                    if isinstance(role, str) and role.strip():
                        return role.strip().lower()
            except (ValueError, TypeError):
                pass
        return "owner"

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
        # Fail closed: demo identities require the explicit env opt-in.
        # Missing Supabase config must surface as 503 on the auth path,
        # never as an open API serving a synthesized regulator user.
        return self.kestrel_enable_demo_mode


@lru_cache
def get_settings() -> Settings:
    return Settings()
