import json

import httpx

from app.ai.providers.openai_adapter import _split_user_prompt
from app.ai.types import CheckStatus, ProviderHealth, ProviderName, ProviderRequest, ProviderResponse
from app.config import Settings


class AnthropicProvider:
    name = ProviderName.ANTHROPIC

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def _headers(self) -> dict[str, str]:
        return {
            "x-api-key": self.settings.anthropic_api_key or "",
            "anthropic-version": self.settings.anthropic_version,
            "content-type": "application/json",
        }

    def _missing_config_detail(self) -> str | None:
        missing = []
        if not self.settings.anthropic_api_key:
            missing.append("ANTHROPIC_API_KEY")
        if not self.settings.anthropic_model:
            missing.append("ANTHROPIC_MODEL")
        if missing:
            return f"Missing required Anthropic config: {', '.join(missing)}."
        return None

    async def healthcheck(self, probe: bool = False) -> ProviderHealth:
        missing_config = self._missing_config_detail()
        configured = missing_config is None
        metadata = {
            "base_url": self.settings.anthropic_base_url,
            "model": self.settings.anthropic_model,
        }

        if not configured:
            return ProviderHealth(
                provider=self.name,
                status=CheckStatus.MISSING_CONFIG,
                configured=False,
                reachable=None,
                detail=missing_config or "Anthropic configuration is incomplete.",
                metadata=metadata,
            )

        if not probe:
            return ProviderHealth(
                provider=self.name,
                status=CheckStatus.SKIPPED,
                configured=True,
                reachable=None,
                detail="Provider is configured; external probes are disabled.",
                metadata=metadata,
            )

        try:
            async with httpx.AsyncClient(timeout=self.settings.ai_provider_timeout_seconds) as client:
                response = await client.get(
                    f"{self.settings.anthropic_base_url.rstrip('/')}/v1/models",
                    headers=self._headers(),
                )
                response.raise_for_status()
        except Exception as exc:  # pragma: no cover - network path
            return ProviderHealth(
                provider=self.name,
                status=CheckStatus.ERROR,
                configured=True,
                reachable=False,
                detail=f"Anthropic reachability probe failed: {exc}",
                metadata=metadata,
            )

        return ProviderHealth(
            provider=self.name,
            status=CheckStatus.OK,
            configured=True,
            reachable=True,
            detail="Anthropic provider reachable.",
            metadata=metadata,
        )

    async def generate_json(self, request: ProviderRequest) -> ProviderResponse:
        cache_enabled = self.settings.ai_prompt_cache_enabled

        if cache_enabled:
            # Anthropic prompt caching: system prompt becomes a typed
            # block array with cache_control: ephemeral on the static
            # part. User message splits into a cached static prefix
            # block + an uncached volatile INPUT block. The upstream
            # API serves the cached prefix at ~90% discount on cache
            # hit. Cache TTL is 5 minutes by default.
            system_blocks: list[dict[str, object]] = [
                {
                    "type": "text",
                    "text": request.system_prompt,
                    "cache_control": {"type": "ephemeral"},
                }
            ]
            static_prefix, dynamic_input = _split_user_prompt(request.user_prompt)
            user_blocks: list[dict[str, object]] = [
                {
                    "type": "text",
                    "text": static_prefix,
                    "cache_control": {"type": "ephemeral"},
                }
            ]
            if dynamic_input:
                user_blocks.append({"type": "text", "text": dynamic_input})
            messages = [{"role": "user", "content": user_blocks}]
        else:
            system_blocks = request.system_prompt
            messages = [{"role": "user", "content": request.user_prompt}]

        payload = {
            "model": request.model,
            "system": system_blocks,
            "max_tokens": request.max_output_tokens,
            "temperature": request.temperature,
            "messages": messages,
            "tools": [
                {
                    "name": "output_schema",
                    "description": f"Return a {request.output_schema_name} object that matches the provided JSON schema.",
                    "input_schema": request.output_schema,
                }
            ],
            "tool_choice": {"type": "tool", "name": "output_schema"},
        }

        async with httpx.AsyncClient(timeout=self.settings.ai_provider_timeout_seconds) as client:
            response = await client.post(
                f"{self.settings.anthropic_base_url.rstrip('/')}/v1/messages",
                headers=self._headers(),
                json=payload,
            )
            response.raise_for_status()

        data = response.json()
        content_blocks = data.get("content") or []

        for block in content_blocks:
            if block.get("type") == "tool_use":
                return ProviderResponse(
                    provider=self.name,
                    model=request.model,
                    content=json.dumps(block.get("input") or {}, ensure_ascii=True),
                    raw_response=data,
                )

        text_content = "".join(
            block.get("text", "")
            for block in content_blocks
            if isinstance(block, dict) and block.get("type") == "text"
        )
        if not text_content.strip():
            raise RuntimeError("Anthropic returned neither tool input nor text content.")

        return ProviderResponse(
            provider=self.name,
            model=request.model,
            content=text_content,
            raw_response=data,
        )
