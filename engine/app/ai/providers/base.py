from typing import Protocol

from app.ai.types import ProviderHealth, ProviderRequest, ProviderResponse


class LLMProvider(Protocol):
    name: str

    async def healthcheck(self, probe: bool = False) -> ProviderHealth:
        ...

    async def generate_json(self, request: ProviderRequest) -> ProviderResponse:
        ...
