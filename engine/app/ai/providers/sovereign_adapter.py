"""Sovereign Bangladesh-trained model adapter (V3 phase 4.4).

HTTP client to a self-hosted vLLM-compatible inference endpoint. The
adapter slots into the V3 P2 routing pattern with no structural change
— when ``ai_sovereign_url`` + ``ai_sovereign_model`` are configured AND
a per-task rollout > 0, ``resolve_task_routes`` prepends a sovereign
``TaskRoute`` at index 0 of the chain.

The adapter implements the existing ``LLMProvider`` Protocol exactly so
the orchestrator dispatches to it identically to OpenAI / Anthropic.
The only adapter-specific bit is the **confidence source**: we read
token-level log-probabilities from the model and convert to a 0–1
score. Every other provider falls back to the schema-validity scorer.

For V3 P4 the actual inference stays empty — no sovereign endpoint is
configured in production. The adapter is registered in the orchestrator's
default provider dict so the moment a sovereign URL is set on Render +
a per-task threshold + rollout flip, traffic routes through here.
"""
from __future__ import annotations

import json
import logging
import math
import statistics
from typing import Any

import httpx

from app.ai.types import (
    CheckStatus,
    ProviderHealth,
    ProviderName,
    ProviderRequest,
    ProviderResponse,
)
from app.config import Settings

logger = logging.getLogger("kestrel.ai.providers.sovereign")


class SovereignProvider:
    """Implements the ``LLMProvider`` Protocol against a vLLM-compatible
    HTTP endpoint."""

    name = ProviderName.SOVEREIGN

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def _missing_config_detail(self) -> str | None:
        missing: list[str] = []
        if not self.settings.ai_sovereign_url:
            missing.append("AI_SOVEREIGN_URL")
        if not self.settings.ai_sovereign_model:
            missing.append("AI_SOVEREIGN_MODEL")
        if missing:
            return f"Missing required Sovereign config: {', '.join(missing)}."
        return None

    def _headers(self) -> dict[str, str]:
        headers: dict[str, str] = {"Content-Type": "application/json"}
        if self.settings.ai_sovereign_api_key:
            headers["Authorization"] = f"Bearer {self.settings.ai_sovereign_api_key}"
        return headers

    async def healthcheck(self, probe: bool = False) -> ProviderHealth:
        missing = self._missing_config_detail()
        metadata = {
            "base_url": self.settings.ai_sovereign_url,
            "model": self.settings.ai_sovereign_model,
        }
        if missing:
            return ProviderHealth(
                provider=self.name,
                status=CheckStatus.MISSING_CONFIG,
                configured=False,
                reachable=None,
                detail=missing,
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
                    f"{self.settings.ai_sovereign_url.rstrip('/')}/v1/models",
                    headers=self._headers(),
                )
                response.raise_for_status()
        except Exception as exc:  # pragma: no cover - network path
            return ProviderHealth(
                provider=self.name,
                status=CheckStatus.ERROR,
                configured=True,
                reachable=False,
                detail=f"Sovereign reachability probe failed: {exc}",
                metadata=metadata,
            )
        return ProviderHealth(
            provider=self.name,
            status=CheckStatus.OK,
            configured=True,
            reachable=True,
            detail="Sovereign endpoint reachable.",
            metadata=metadata,
        )

    async def generate_json(self, request: ProviderRequest) -> ProviderResponse:
        if self._missing_config_detail() is not None:
            raise RuntimeError(self._missing_config_detail() or "Sovereign not configured")

        body = self._build_request_body(request)
        url = f"{self.settings.ai_sovereign_url.rstrip('/')}/v1/chat/completions"
        async with httpx.AsyncClient(timeout=self.settings.ai_provider_timeout_seconds) as client:
            response = await client.post(url, json=body, headers=self._headers())
        response.raise_for_status()
        payload = response.json()
        content = _extract_content(payload)
        confidence = _confidence_from_logprobs(payload)
        prompt_tokens, completion_tokens = _extract_token_usage(payload)

        return ProviderResponse(
            provider=self.name,
            model=request.model,
            content=content,
            raw_response=payload,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            confidence=confidence,
        )

    def _build_request_body(self, request: ProviderRequest) -> dict[str, Any]:
        return {
            "model": request.model,
            "messages": [
                {"role": "system", "content": request.system_prompt},
                {"role": "user", "content": request.user_prompt},
            ],
            "temperature": request.temperature,
            "max_tokens": request.max_output_tokens,
            # vLLM returns top-K log-probs when this is set; we use them
            # for the confidence source.
            "logprobs": True,
            "top_logprobs": 5,
            # Hint to the model that we want JSON. vLLM honours this on
            # most modern bases; harmless if unsupported.
            "response_format": {"type": "json_object"},
        }


def _extract_content(payload: dict[str, Any]) -> str:
    """Pull the structured-JSON content out of an OpenAI-shaped response."""
    choices = payload.get("choices") or []
    if not choices:
        return ""
    first = choices[0]
    message = first.get("message") or {}
    content = message.get("content")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        # Some providers return content as a list of segments.
        return "".join(seg.get("text", "") for seg in content if isinstance(seg, dict))
    return ""


def _extract_token_usage(payload: dict[str, Any]) -> tuple[int | None, int | None]:
    usage = payload.get("usage") or {}
    pt = usage.get("prompt_tokens")
    ct = usage.get("completion_tokens")
    return (
        int(pt) if isinstance(pt, (int, float)) else None,
        int(ct) if isinstance(ct, (int, float)) else None,
    )


def _confidence_from_logprobs(payload: dict[str, Any]) -> float | None:
    """Mean exp(log-prob) across the completion tokens, clamped to
    ``[0, 0.95]``.

    A model that's confident across the response averages high
    probabilities (close to 1.0); an uncertain model has long tails of
    low-probability tokens and the mean drops. Capping at 0.95 keeps
    parity with ``cap_confidence`` in app.ai.confidence.
    """
    choices = payload.get("choices") or []
    if not choices:
        return None
    logprobs = (choices[0] or {}).get("logprobs") or {}
    content = logprobs.get("content") or []
    if not content:
        return None

    probs: list[float] = []
    for token in content:
        if not isinstance(token, dict):
            continue
        lp = token.get("logprob")
        if lp is None:
            continue
        try:
            probs.append(math.exp(float(lp)))
        except (TypeError, ValueError, OverflowError):
            continue

    if not probs:
        return None
    mean = statistics.fmean(probs)
    return round(min(0.95, max(0.0, mean)), 3)


def confidence_from_logprobs(payload: dict[str, Any]) -> float | None:
    """Public alias — the test suite imports the helper directly."""
    return _confidence_from_logprobs(payload)


def parse_chat_completion_content(payload: dict[str, Any]) -> str:
    """Public alias for tests."""
    return _extract_content(payload)
