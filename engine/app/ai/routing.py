"""Per-task provider routing.

V3 P2 scaffolded sovereign-first / Claude-fallback. V3 P5 made the
"prepend sovereign?" decision per-call by adding a coin-flip against
``effective_rollout_pct_for(task)`` — the runtime-mutable rollout %
that lives in the ``sovereign_rollout`` table.

In V3 P2 / P3 / P4 every task's rollout was 0% so this prepend was
unconditional-skip. After V3 P5 ops can flip a task's rollout to e.g.
10 in the DB and ~10% of calls start trying the sovereign route. The
confidence threshold gate (``effective_threshold_for(task)``) then
decides whether the sovereign response ships or falls through to Claude.
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
    AITaskName.INVESTIGATION_AGENT_HOP: [ProviderName.ANTHROPIC, ProviderName.OPENAI],
}


def _sovereign_configured(settings: Settings) -> bool:
    return bool(settings.ai_sovereign_url and settings.ai_sovereign_model)


def _build_baseline_routes(task: AITaskName, settings: Settings) -> list[TaskRoute]:
    """The OpenAI / Anthropic / Heuristic chain — pre-V3-P5 behaviour."""
    routes: list[TaskRoute] = []
    provider_order = TASK_PROVIDER_ORDER[task]
    for provider in provider_order:
        if provider == ProviderName.OPENAI and settings.openai_api_key and settings.openai_model:
            routes.append(TaskRoute(provider=provider, model=settings.openai_model))
        if provider == ProviderName.ANTHROPIC and settings.anthropic_api_key and settings.anthropic_model:
            routes.append(TaskRoute(provider=provider, model=settings.anthropic_model))
    if settings.ai_fallback_enabled and (settings.demo_mode_enabled() or not routes):
        routes.append(TaskRoute(provider=ProviderName.HEURISTIC, model="heuristic-v1"))
    return routes


async def resolve_task_routes(task: AITaskName, settings: Settings) -> list[TaskRoute]:
    """Return the ordered route list for one AI invocation.

    V3 P5 made this async because the per-call sovereign decision now
    consults the DB-backed rollout config. Callers (the orchestrator,
    tests, scripts) must await."""
    # Lazy import for the DB-touching service so anything that imports
    # routing offline (tests, scripts) doesn't drag SQLAlchemy in until
    # the production path actually needs it.
    from app.services.sovereign_rollout import (
        coin_flip,
        effective_rollout_pct_for,
    )

    routes: list[TaskRoute] = []
    sovereign_eligible = _sovereign_configured(settings) and is_sovereign_eligible(task)
    if sovereign_eligible:
        # Static-default rollout > 0 means the task is "in scope" for
        # sovereign at all. The DB-backed effective rollout decides
        # how often we actually try it per call.
        try:
            rollout_pct = await effective_rollout_pct_for(task)
        except Exception:
            # Defensive — if the DB read fails for any reason, fall back
            # to the static default. Routing must never crash.
            from app.ai.thresholds import rollout_pct_for as _static_rollout
            rollout_pct = _static_rollout(task)
        if coin_flip(rollout_pct):
            routes.append(
                TaskRoute(
                    provider=ProviderName.SOVEREIGN,
                    model=settings.ai_sovereign_model or "sovereign-v1",
                )
            )

    routes.extend(_build_baseline_routes(task, settings))
    return routes


def resolve_task_routes_static(task: AITaskName, settings: Settings) -> list[TaskRoute]:
    """Sync helper for tests + scripts that don't have an event loop.

    Returns the static-default route list with NO sovereign prepend.
    The async ``resolve_task_routes`` is the production path."""
    return _build_baseline_routes(task, settings)
