import json
from enum import StrEnum

from pydantic import BaseModel, Field


class ProviderName(StrEnum):
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    HEURISTIC = "heuristic"


class CheckStatus(StrEnum):
    OK = "ok"
    SKIPPED = "skipped"
    MISSING_CONFIG = "missing_config"
    ERROR = "error"


class AITaskName(StrEnum):
    ENTITY_EXTRACTION = "entity_extraction"
    STR_NARRATIVE = "str_narrative"
    ALERT_EXPLANATION = "alert_explanation"
    CASE_SUMMARY = "case_summary"
    TYPOLOGY_SUGGESTION = "typology_suggestion"
    EXECUTIVE_BRIEFING = "executive_briefing"


class RedactionMode(StrEnum):
    NONE = "none"
    REDACT = "redact"


class ProviderHealth(BaseModel):
    provider: ProviderName
    status: CheckStatus
    configured: bool
    detail: str
    reachable: bool | None = None
    metadata: dict[str, object] = Field(default_factory=dict)


class ProviderRequest(BaseModel):
    task: AITaskName
    model: str
    system_prompt: str
    user_prompt: str
    output_schema_name: str
    output_schema: dict[str, object]
    temperature: float = 0.2
    max_output_tokens: int = 900


class ProviderResponse(BaseModel):
    provider: ProviderName
    model: str
    content: str
    raw_response: dict[str, object] = Field(default_factory=dict)


class ProviderAttempt(BaseModel):
    provider: ProviderName
    model: str
    success: bool
    error: str | None = None


class TaskRoute(BaseModel):
    provider: ProviderName
    model: str


class PromptDefinition(BaseModel):
    task: AITaskName
    version: str
    system_prompt: str
    guidance: str


def stable_json(value: object) -> str:
    return json.dumps(value, sort_keys=True, default=str, ensure_ascii=True)
