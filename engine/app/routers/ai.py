import uuid as _uuid
from typing import Annotated, Any, Literal, TypeVar

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.service import AIInvocationError, AIInvocationResult, AIOrchestrator
from app.ai.types import AITaskName
from app.auth import AuthenticatedUser, get_current_user, require_roles
from app.dependencies import get_current_session
from app.schemas.ai import (
    AIInvocationAttempt,
    AIInvocationMeta,
    AIResultEnvelope,
    AlertExplanationResult,
    CaseSummaryResult,
    EntityExtractionRequest,
    EntityExtractionResult,
    ExecutiveBriefingRequest,
    ExecutiveBriefingResult,
    STRNarrativeRequest,
    STRNarrativeResult,
    TypologySuggestionRequest,
    TypologySuggestionResult,
)
from app.services.ai_outcome import (
    build_outcome_dashboard,
    list_recent_outcomes,
    record_correction,
)
from app.services.alerts import get_alert_detail
from app.services.case_mgmt import get_case_workspace

router = APIRouter()

ResultT = TypeVar("ResultT", bound=BaseModel)


def get_ai_orchestrator() -> AIOrchestrator:
    return AIOrchestrator()


def build_envelope(invocation: AIInvocationResult, result_model: type[ResultT]) -> dict[str, object]:
    return {
        "meta": AIInvocationMeta(
            task=invocation.task,
            provider=invocation.provider,
            model=invocation.model,
            prompt_version=invocation.prompt_version,
            redaction_mode=invocation.redaction_mode,
            fallback_used=invocation.fallback_used,
            audit_logged=invocation.audit_logged,
            attempts=[
                AIInvocationAttempt(
                    provider=attempt.provider,
                    model=attempt.model,
                    success=attempt.success,
                    error=attempt.error,
                )
                for attempt in invocation.attempts
            ],
            outcome_log_id=str(invocation.outcome_log_id) if invocation.outcome_log_id else None,
            latency_ms=invocation.latency_ms,
        ),
        "result": result_model.model_validate(invocation.output.model_dump()),
    }


async def invoke_task(
    *,
    orchestrator: AIOrchestrator,
    task: AITaskName,
    payload: dict[str, object],
    output_model: type[ResultT],
    user: AuthenticatedUser,
    request: Request,
) -> AIResultEnvelope[ResultT]:
    try:
        invocation = await orchestrator.invoke(
            task=task,
            payload=payload,
            output_model=output_model,
            user=user,
            ip=request.client.host if request.client else None,
        )
    except AIInvocationError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return build_envelope(invocation, output_model)


@router.post(
    "/entity-extraction",
    response_model=AIResultEnvelope[EntityExtractionResult],
)
async def entity_extraction(
    body: EntityExtractionRequest,
    request: Request,
    user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    orchestrator: Annotated[AIOrchestrator, Depends(get_ai_orchestrator)],
) -> AIResultEnvelope[EntityExtractionResult]:
    return await invoke_task(
        orchestrator=orchestrator,
        task=AITaskName.ENTITY_EXTRACTION,
        payload=body.model_dump(),
        output_model=EntityExtractionResult,
        user=user,
        request=request,
    )


@router.post(
    "/str-narrative",
    response_model=AIResultEnvelope[STRNarrativeResult],
)
async def str_narrative(
    body: STRNarrativeRequest,
    request: Request,
    user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    orchestrator: Annotated[AIOrchestrator, Depends(get_ai_orchestrator)],
) -> AIResultEnvelope[STRNarrativeResult]:
    return await invoke_task(
        orchestrator=orchestrator,
        task=AITaskName.STR_NARRATIVE,
        payload=body.model_dump(),
        output_model=STRNarrativeResult,
        user=user,
        request=request,
    )


@router.post(
    "/typology-suggestion",
    response_model=AIResultEnvelope[TypologySuggestionResult],
)
async def typology_suggestion(
    body: TypologySuggestionRequest,
    request: Request,
    user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    orchestrator: Annotated[AIOrchestrator, Depends(get_ai_orchestrator)],
) -> AIResultEnvelope[TypologySuggestionResult]:
    return await invoke_task(
        orchestrator=orchestrator,
        task=AITaskName.TYPOLOGY_SUGGESTION,
        payload=body.model_dump(),
        output_model=TypologySuggestionResult,
        user=user,
        request=request,
    )


@router.post(
    "/executive-briefing",
    response_model=AIResultEnvelope[ExecutiveBriefingResult],
)
async def executive_briefing(
    body: ExecutiveBriefingRequest,
    request: Request,
    user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    orchestrator: Annotated[AIOrchestrator, Depends(get_ai_orchestrator)],
) -> AIResultEnvelope[ExecutiveBriefingResult]:
    return await invoke_task(
        orchestrator=orchestrator,
        task=AITaskName.EXECUTIVE_BRIEFING,
        payload=body.model_dump(),
        output_model=ExecutiveBriefingResult,
        user=user,
        request=request,
    )


@router.post(
    "/alerts/{alert_id}/explanation",
    response_model=AIResultEnvelope[AlertExplanationResult],
)
async def alert_explanation(
    alert_id: str,
    request: Request,
    user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_current_session)],
    orchestrator: Annotated[AIOrchestrator, Depends(get_ai_orchestrator)],
) -> AIResultEnvelope[AlertExplanationResult]:
    try:
        alert = await get_alert_detail(session, user=user, alert_id=alert_id)
    except HTTPException as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
    return await invoke_task(
        orchestrator=orchestrator,
        task=AITaskName.ALERT_EXPLANATION,
        payload={
            "alert_id": alert["id"],
            "title": alert["title"],
            "description": alert["description"],
            "alert_type": alert["alert_type"],
            "risk_score": alert["risk_score"],
            "severity": alert["severity"],
            "reasons": alert["reasons"],
        },
        output_model=AlertExplanationResult,
        user=user,
        request=request,
    )


@router.post(
    "/cases/{case_id}/summary",
    response_model=AIResultEnvelope[CaseSummaryResult],
)
async def case_summary(
    case_id: str,
    request: Request,
    user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_current_session)],
    orchestrator: Annotated[AIOrchestrator, Depends(get_ai_orchestrator)],
) -> AIResultEnvelope[CaseSummaryResult]:
    case = await get_case_workspace(session, user=user, case_id=case_id)
    return await invoke_task(
        orchestrator=orchestrator,
        task=AITaskName.CASE_SUMMARY,
        payload={
            "case_id": case["id"],
            "title": case["title"],
            "summary": case["summary"],
            "severity": case["severity"],
            "status": case["status"],
            "linked_entity_ids": case["linked_entity_ids"],
            "timeline": case["timeline"],
            "notes": case["notes"],
        },
        output_model=CaseSummaryResult,
        user=user,
        request=request,
    )


# --- V3 phase 1: AI outcome log endpoints --------------------------------


class OutcomeCorrectionInput(BaseModel):
    correction: dict[str, Any] | None = None
    outcome_label: Literal["true_positive", "false_positive", "accepted", "rejected", "edited"] | None = None


class OutcomeViewModel(BaseModel):
    id: str
    task_name: str
    provider: str
    model: str
    confidence: float | None = None
    outcome_label: str | None = None
    has_correction: bool
    latency_ms: int
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    fallback_from_provider: str | None = None
    request_id: str | None = None
    created_at: str | None = None
    updated_at: str | None = None


class TaskAccuracyRow(BaseModel):
    task_name: str
    total: int
    corrections: int
    correction_rate: float
    avg_latency_ms: int


class ProviderRow(BaseModel):
    provider: str
    count: int


class OutcomeDashboardResponse(BaseModel):
    window_days: int
    total_invocations: int
    total_corrections: int
    correction_rate: float
    by_task: list[TaskAccuracyRow] = Field(default_factory=list)
    by_provider: list[ProviderRow] = Field(default_factory=list)
    outcome_labels: dict[str, int] = Field(default_factory=dict)
    persona_view: Literal["bank", "regulator"]
    generated_at: str


def _parse_log_id(raw: str) -> _uuid.UUID:
    try:
        return _uuid.UUID(raw)
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid log id") from exc


@router.post("/outcomes/{log_id}/correction")
async def post_correction(
    log_id: str,
    body: OutcomeCorrectionInput,
    user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_current_session)],
) -> dict[str, bool]:
    if body.correction is None and body.outcome_label is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="At least one of `correction` or `outcome_label` is required.",
        )
    updated = await record_correction(
        log_id=_parse_log_id(log_id),
        user=user,
        correction=body.correction,
        outcome_label=body.outcome_label,
    )
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Outcome log row not found in your tenant.",
        )
    return {"updated": True}


@router.get("/outcomes/dashboard", response_model=OutcomeDashboardResponse)
async def outcomes_dashboard(
    user: Annotated[AuthenticatedUser, Depends(require_roles("manager", "admin", "superadmin", "analyst"))],
    session: Annotated[AsyncSession, Depends(get_current_session)],
    window_days: int = 30,
) -> OutcomeDashboardResponse:
    payload = await build_outcome_dashboard(session, user=user, window_days=window_days)
    return OutcomeDashboardResponse.model_validate(payload)


@router.get("/outcomes/recent", response_model=list[OutcomeViewModel])
async def outcomes_recent(
    user: Annotated[AuthenticatedUser, Depends(require_roles("manager", "admin", "superadmin", "analyst"))],
    session: Annotated[AsyncSession, Depends(get_current_session)],
    limit: int = 50,
    only_corrected: bool = False,
) -> list[OutcomeViewModel]:
    rows = await list_recent_outcomes(
        session, user=user, limit=limit, only_corrected=only_corrected
    )
    return [OutcomeViewModel.model_validate(row) for row in rows]
