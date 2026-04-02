import httpx

from app.ai.types import CheckStatus, ProviderHealth, ProviderName, ProviderRequest, ProviderResponse
from app.config import Settings


class OpenAIProvider:
    name = ProviderName.OPENAI

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.settings.openai_api_key}",
            "Content-Type": "application/json",
            **(
                {"OpenAI-Organization": self.settings.openai_organization}
                if self.settings.openai_organization
                else {}
            ),
        }

    def _missing_config_detail(self) -> str | None:
        missing = []
        if not self.settings.openai_api_key:
            missing.append("OPENAI_API_KEY")
        if not self.settings.openai_model:
            missing.append("OPENAI_MODEL")
        if missing:
            return f"Missing required OpenAI config: {', '.join(missing)}."
        return None

    async def healthcheck(self, probe: bool = False) -> ProviderHealth:
        missing_config = self._missing_config_detail()
        configured = missing_config is None
        metadata = {
            "base_url": self.settings.openai_base_url,
            "model": self.settings.openai_model,
        }

        if not configured:
            return ProviderHealth(
                provider=self.name,
                status=CheckStatus.MISSING_CONFIG,
                configured=False,
                reachable=None,
                detail=missing_config or "OpenAI configuration is incomplete.",
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
                    f"{self.settings.openai_base_url.rstrip('/')}/models",
                    headers=self._headers(),
                )
                response.raise_for_status()
        except Exception as exc:  # pragma: no cover - network path
            return ProviderHealth(
                provider=self.name,
                status=CheckStatus.ERROR,
                configured=True,
                reachable=False,
                detail=f"OpenAI reachability probe failed: {exc}",
                metadata=metadata,
            )

        return ProviderHealth(
            provider=self.name,
            status=CheckStatus.OK,
            configured=True,
            reachable=True,
            detail="OpenAI provider reachable.",
            metadata=metadata,
        )

    async def generate_json(self, request: ProviderRequest) -> ProviderResponse:
        payload = {
            "model": request.model,
            "messages": [
                {"role": "system", "content": request.system_prompt},
                {"role": "user", "content": request.user_prompt},
            ],
            "temperature": request.temperature,
            "max_completion_tokens": request.max_output_tokens,
            "tools": [
                {
                    "type": "function",
                    "function": {
                        "name": "output_schema",
                        "description": f"Return a {request.output_schema_name} object that matches the JSON schema exactly.",
                        "parameters": request.output_schema,
                        "strict": True,
                    },
                }
            ],
            "tool_choice": {
                "type": "function",
                "function": {"name": "output_schema"},
            },
        }

        async with httpx.AsyncClient(timeout=self.settings.ai_provider_timeout_seconds) as client:
            response = await client.post(
                f"{self.settings.openai_base_url.rstrip('/')}/chat/completions",
                headers=self._headers(),
                json=payload,
            )
            response.raise_for_status()

        data = response.json()
        message = ((data.get("choices") or [{}])[0]).get("message") or {}
        tool_calls = message.get("tool_calls") or []
        if tool_calls:
            arguments = (((tool_calls[0] or {}).get("function") or {}).get("arguments"))
            if not arguments:
                raise RuntimeError("OpenAI returned a tool call without function arguments.")
            content = arguments
        else:
            content = message.get("content")
            if isinstance(content, list):
                content = "".join(
                    item.get("text", "")
                    for item in content
                    if isinstance(item, dict)
                )
            if not isinstance(content, str) or not content.strip():
                raise RuntimeError("OpenAI returned neither tool output nor text content.")

        return ProviderResponse(
            provider=self.name,
            model=request.model,
            content=content,
            raw_response=data,
        )
