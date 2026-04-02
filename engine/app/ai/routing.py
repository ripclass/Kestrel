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


def resolve_task_routes(task: AITaskName, settings: Settings) -> list[TaskRoute]:
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
