from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "Kestrel Engine"
    app_version: str = "0.1.0"
    environment: str = "development"
    engine_port: int = 8000

    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/postgres"
    redis_url: str = "redis://localhost:6379/0"

    supabase_url: str | None = None
    supabase_anon_key: str | None = None
    supabase_service_role_key: str | None = None
    supabase_jwt_secret: str | None = None

    storage_bucket_uploads: str = "kestrel-uploads"
    storage_bucket_exports: str = "kestrel-exports"

    goaml_sync_enabled: bool = False
    goaml_base_url: str | None = None
    goaml_api_key: str | None = None

    kestrel_demo_persona: str = "bfiu_analyst"


@lru_cache
def get_settings() -> Settings:
    return Settings()
