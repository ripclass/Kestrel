"""Per-task provider routing.

V3 phase 2 introduces the sovereign-first / Claude-fallback pattern:
when ``ai_sovereign_url`` + ``ai_sovereign_model`` are configured AND
the per-task ``rollout_pct_for(task) > 0``, a sovereign route is
prepended at index 0 of the chain. The orchestrator's confidence
threshold gate (``threshold_for(task)``) decides whether the sovereign
response ships or falls through to Claude.

In V3 phase 2 no sovereign endpoint is configured, so this prepend is
a no-op — every task still routes through OpenAI / Anthropic / Heuristic
exactly as it did pre-V3. The pattern is in place; behavior is unchanged.
"""
from __future__ import annotations

from app.ai.thresholds import is_sovereign_eligible
from app.ai.types import AITaskName, ProviderName, TaskRoute
from app.config import Settings


TASK_PROVIDER_ORDER: dict[AITaskName, list[ProviderName]] = {
    AITaskName.ENTITY_EXTRACTION: [ProviderName.OPENAI, ProviderName.ANTHROPIC],
    AITaskName.STR_NARRATIVE: [ProviderName.OPENAI, ProviderName.ANTHROPIC],
    AITaskName.ALERT_EXPLANATION: [ProviderName.ANTHROPIC, ProviderName.OPENAI],
    AITaskName.CASE_SUMMARY: [ProviderName.ANTHROPIC, ProviderName.OPENAI],
    AITaskName.TYPOLOGY_SUGGESTION: [ProviderName.OPENAI, ProviderName.ANTHROPIC],
    AITaskName.EXECUTIVE_BRIEFING: [ProviderName.ANTHROPIC, ProviderName.OPENAI],
}


def _sovereign_configured(settings: Settings) -> bool:
    return bool(settings.ai_sovereign_url and settings.ai_sovereign_model)


def resolve_task_routes(task: AITaskName, settings: Settings) -> list[TaskRoute]:
    routes: list[TaskRoute] = []

    # V3 phase 2: prepend sovereign at index 0 when configured AND
    # eligible for this task. ``is_sovereign_eligible`` defaults to
    # False everywhere in V3 P2; flipping a task's rollout > 0 in
    # ``app.ai.thresholds`` is the single edit point to enable it.
    if _sovereign_configured(settings) and is_sovereign_eligible(task):
        routes.append(
            TaskRoute(
                provider=ProviderName.SOVEREIGN,
                model=settings.ai_sovereign_model or "sovereign-v1",
            )
        )

    provider_order = TASK_PROVIDER_ORDER[task]
    for provider in provider_order:
        if provider == ProviderName.OPENAI and settings.openai_api_key and settings.openai_model:
            routes.append(TaskRoute(provider=provider, model=settings.openai_model))
        if provider == ProviderName.ANTHROPIC and settings.anthropic_api_key and settings.anthropic_model:
            routes.append(TaskRoute(provider=provider, model=settings.anthropic_model))

    if settings.ai_fallback_enabled and (settings.demo_mode_enabled() or not routes):
        routes.append(TaskRoute(provider=ProviderName.HEURISTIC, model="heuristic-v1"))

    return routes
