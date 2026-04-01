from app.config import get_settings

settings = get_settings()


def sync_status() -> dict[str, object]:
    return {
        "enabled": settings.goaml_sync_enabled,
        "base_url": settings.goaml_base_url,
        "mode": "stub",
    }
