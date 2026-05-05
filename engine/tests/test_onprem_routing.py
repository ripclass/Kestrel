"""V3 P6.3 — air-gapped AI routing.

Onprem mode strips OpenAI + Anthropic from the baseline route chain so
the AI orchestrator never makes outbound calls when the customer's
network policy disallows them. The sovereign route (when configured
via DB) and the heuristic floor remain available.
"""
from __future__ import annotations

from app.ai.routing import _build_baseline_routes
from app.ai.types import AITaskName, ProviderName
from app.config import Settings


def _settings(**overrides):
    base = Settings(
        openai_api_key="cloud-openai",
        openai_model="gpt-test",
        anthropic_api_key="cloud-anthropic",
        anthropic_model="claude-test",
    )
    for key, value in overrides.items():
        setattr(base, key, value)
    return base


def test_cloud_mode_keeps_openai_anthropic_in_chain() -> None:
    settings = _settings(kestrel_deployment_mode="cloud")
    routes = _build_baseline_routes(AITaskName.ALERT_EXPLANATION, settings)
    providers = [r.provider for r in routes]
    assert ProviderName.OPENAI in providers
    assert ProviderName.ANTHROPIC in providers


def test_onprem_mode_drops_openai_anthropic() -> None:
    """Air-gapped: OpenAI/Anthropic providers are never in the chain even
    when api keys are configured (defence-in-depth — env can leak)."""
    settings = _settings(kestrel_deployment_mode="onprem")
    routes = _build_baseline_routes(AITaskName.ALERT_EXPLANATION, settings)
    providers = [r.provider for r in routes]
    assert ProviderName.OPENAI not in providers
    assert ProviderName.ANTHROPIC not in providers


def test_onprem_mode_falls_back_to_heuristic() -> None:
    """Heuristic is the floor in onprem mode so a call always completes."""
    settings = _settings(kestrel_deployment_mode="onprem")
    routes = _build_baseline_routes(AITaskName.STR_NARRATIVE, settings)
    providers = [r.provider for r in routes]
    assert providers == [ProviderName.HEURISTIC]


def test_onprem_with_fallback_disabled_returns_empty_chain() -> None:
    """Operator can explicitly disable the heuristic floor; the orchestrator
    will then surface the no-route error instead of a degraded response."""
    settings = _settings(kestrel_deployment_mode="onprem", ai_fallback_enabled=False)
    routes = _build_baseline_routes(AITaskName.ALERT_EXPLANATION, settings)
    assert routes == []


def test_is_onprem_helper_is_case_insensitive() -> None:
    assert _settings(kestrel_deployment_mode="ONPREM").is_onprem() is True
    assert _settings(kestrel_deployment_mode="OnPrem").is_onprem() is True
    assert _settings(kestrel_deployment_mode="cloud").is_onprem() is False
    assert _settings(kestrel_deployment_mode="").is_onprem() is False
