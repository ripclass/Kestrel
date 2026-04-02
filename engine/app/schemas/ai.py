from typing import Generic, TypeVar

from pydantic import BaseModel, Field


class AIInvocationAttempt(BaseModel):
    provider: str
    model: str
    success: bool
    error: str | None = None


class AIInvocationMeta(BaseModel):
    task: str
    provider: str
    model: str
    prompt_version: str
    redaction_mode: str
    fallback_used: bool
    audit_logged: bool
    attempts: list[AIInvocationAttempt]


class ExtractedEntity(BaseModel):
    entity_type: str
    value: str
    confidence: float = Field(ge=0, le=1)


class EntityExtractionRequest(BaseModel):
    raw_text: str


class EntityExtractionResult(BaseModel):
    entities: list[ExtractedEntity]


class STRNarrativeRequest(BaseModel):
    subject_name: str | None = None
    subject_account: str | None = None
    subject_phone: str | None = None
    subject_wallet: str | None = None
    subject_nid: str | None = None
    total_amount: float | None = None
    category: str | None = None
    trigger_facts: list[str] = Field(default_factory=list)


class STRNarrativeResult(BaseModel):
    narrative: str
    missing_fields: list[str] = Field(default_factory=list)
    category_suggestion: str
    severity_suggestion: str


class AlertExplanationResult(BaseModel):
    summary: str
    why_it_matters: str
    recommended_actions: list[str] = Field(default_factory=list)


class CaseSummaryResult(BaseModel):
    executive_summary: str
    key_findings: list[str] = Field(default_factory=list)
    recommended_actions: list[str] = Field(default_factory=list)


class TypologySuggestionRequest(BaseModel):
    indicators: list[str] = Field(default_factory=list)
    evidence_summary: str | None = None


class TypologySuggestionResult(BaseModel):
    typology_name: str
    confidence: float = Field(ge=0, le=1)
    indicators: list[str] = Field(default_factory=list)
    rationale: str


class ExecutiveBriefingRequest(BaseModel):
    headline_seed: str | None = None
    summary_seed: str | None = None
    priorities: list[str] = Field(default_factory=list)
    risk_watchlist: list[str] = Field(default_factory=list)


class ExecutiveBriefingResult(BaseModel):
    headline: str
    summary: str
    priorities: list[str] = Field(default_factory=list)
    risk_watchlist: list[str] = Field(default_factory=list)


ResultT = TypeVar("ResultT", bound=BaseModel)


class AIResultEnvelope(BaseModel, Generic[ResultT]):
    meta: AIInvocationMeta
    result: ResultT
