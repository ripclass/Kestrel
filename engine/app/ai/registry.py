from app.ai.providers.anthropic_adapter import AnthropicProvider
from app.ai.providers.openai_adapter import OpenAIProvider
from app.ai.types import ProviderHealth
from app.config import Settings, get_settings


def get_providers(settings: Settings | None = None):
    runtime_settings = settings or get_settings()
    return [
        OpenAIProvider(runtime_settings),
        AnthropicProvider(runtime_settings),
    ]


async def collect_provider_health(settings: Settings | None = None) -> list[ProviderHealth]:
    runtime_settings = settings or get_settings()
    providers = get_providers(runtime_settings)
    return [
        await provider.healthcheck(probe=runtime_settings.ai_enable_external_probes)
        for provider in providers
    ]
