import httpx

from app.ai.types import CheckStatus, ProviderHealth, ProviderName, ProviderRequest, ProviderResponse
from app.config import Settings


# build_provider_request always assembles user_prompt as
# "TASK:\n…\n\nGUIDANCE:\n…\n\nOUTPUT_SCHEMA:\n…\n\nINPUT:\n…".
# Caching the prefix up to and including OUTPUT_SCHEMA is the win;
# the per-call payload sits in INPUT after the last "\n\nINPUT:\n".
_INPUT_DELIMITER = "\n\nINPUT:\n"


def _split_user_prompt(user_prompt: str) -> tuple[str, str]:
    idx = user_prompt.rfind(_INPUT_DELIMITER)
    if idx == -1:
        # Defensive: if the prefix shape ever changes, fall back to
        # caching the whole prompt rather than failing the request.
        return user_prompt, ""
    static_prefix = user_prompt[: idx + len(_INPUT_DELIMITER)]
    dynamic_input = user_prompt[idx + len(_INPUT_DELIMITER) :]
    return static_prefix, dynamic_input


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

    def _build_messages(self, request: ProviderRequest) -> list[dict[str, object]]:
        """Build the chat messages array.

        When prompt caching is enabled, the system_prompt and the static
        prefix of the user_prompt (everything before INPUT) are wrapped
        in typed content blocks with cache_control: ephemeral. Anthropic
        (via OpenRouter) and supporting OpenAI models honour the marker
        and serve the cached prefix at ~90% discount; providers that
        ignore it just see plain text content blocks. The volatile
        INPUT block stays uncached.

        When caching is disabled the legacy plain-string content shape
        is used so the request looks identical to pre-caching traffic.
        """
        if not self.settings.ai_prompt_cache_enabled:
            return [
                {"role": "system", "content": request.system_prompt},
                {"role": "user", "content": request.user_prompt},
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

        return [
            {
                "role": "system",
                "content": [
                    {
                        "type": "text",
                        "text": request.system_prompt,
                        "cache_control": {"type": "ephemeral"},
                    }
                ],
            },
            {"role": "user", "content": user_blocks},
        ]

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
        messages = self._build_messages(request)
        payload = {
            "model": request.model,
            "messages": messages,
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
