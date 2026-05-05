import json
import time
import uuid as _uuid
from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel

from app.ai.audit import record_ai_invocation
from app.ai.confidence import cap_confidence, compute_schema_validity
from app.ai.evaluations import validate_structured_output
from app.ai.prompts import get_prompt_definition
from app.ai.providers import AnthropicProvider, OpenAIProvider
from app.ai.providers.base import LLMProvider
from app.ai.redaction import redact_payload
from app.ai.routing import resolve_task_routes
from app.ai.thresholds import threshold_for
from app.ai.types import (
    AITaskName,
    PromptDefinition,
    ProviderAttempt,
    ProviderName,
    ProviderRequest,
    ProviderResponse,
    RedactionMode,
)
from app.auth import AuthenticatedUser
from app.config import Settings, get_settings


class AIInvocationError(RuntimeError):
    pass


class HeuristicProvider:
    name = ProviderName.HEURISTIC

    async def healthcheck(self, probe: bool = False):  # pragma: no cover - health not used in tests
        raise NotImplementedError

    async def generate_json(self, request: ProviderRequest) -> ProviderResponse:
        payload = json.loads(request.user_prompt.split("INPUT:\n", maxsplit=1)[1])
        content = build_heuristic_output(request.task, payload)
        # Heuristic confidence reflects template completeness — see V3
        # phase 2.2. The orchestrator treats this as advisory; the
        # heuristic provider is also the bottom-of-chain catch-all so
        # confidence below the task threshold doesn't reject the response
        # when no other provider succeeded.
        confidence = _heuristic_confidence(content)
        return ProviderResponse(
            provider=self.name,
            model=request.model,
            content=json.dumps(content, ensure_ascii=True),
            raw_response={"provider": "heuristic"},
            confidence=confidence,
        )


def _heuristic_confidence(content: dict[str, Any]) -> float:
    """Coarse template-completeness score for heuristic output.

    A heuristic generation is by definition lower-confidence than a real
    LLM call. We cap at 0.5 so the orchestrator routes around the
    heuristic whenever a real provider clears its threshold."""
    if not content:
        return 0.0
    populated = sum(1 for v in content.values() if v not in (None, "", [], {}))
    if populated == 0:
        return 0.0
    return min(0.5, 0.1 + 0.1 * populated)


def build_heuristic_output(task: AITaskName, payload: dict[str, Any]) -> dict[str, Any]:
    if task == AITaskName.STR_NARRATIVE:
        facts = payload.get("trigger_facts", [])
        subject_name = payload.get("subject_name") or "The subject"
        amount = payload.get("total_amount")
        try:
            amount_text = f"{float(amount):,.0f}" if amount is not None else "an unspecified amount"
        except (TypeError, ValueError):
            amount_text = "an unspecified amount"
        return {
            "narrative": f"{subject_name} was flagged after {len(facts)} suspicious indicators were observed involving approximately BDT {amount_text}.",
            "missing_fields": [field for field in ["subject_nid", "subject_wallet"] if not payload.get(field)],
            "category_suggestion": payload.get("category") or "fraud",
            "severity_suggestion": "high",
        }
    if task == AITaskName.CASE_SUMMARY:
        notes = payload.get("notes", [])
        return {
            "executive_summary": payload.get("summary") or payload.get("title") or "Case summary generated from structured evidence.",
            "key_findings": [
                f"Linked entities: {len(payload.get('linked_entity_ids', []))}",
                f"Evidence notes: {len(notes)}",
            ],
            "recommended_actions": [
                "Validate beneficiary KYC details.",
                "Review cross-bank overlaps before escalation.",
            ],
        }
    if task == AITaskName.ALERT_EXPLANATION:
        reasons = payload.get("reasons", [])
        return {
            "summary": payload.get("description") or "Alert indicates suspicious activity requiring analyst review.",
            "why_it_matters": f"{len(reasons)} evidence-backed reasons were recorded for this alert.",
            "recommended_actions": [
                "Confirm linked counterparties.",
                "Escalate if cross-bank exposure is still active.",
            ],
        }
    if task == AITaskName.ENTITY_EXTRACTION:
        text = payload.get("raw_text", "")
        extracted = []
        if "01" in text:
            extracted.append({"entity_type": "phone", "value": "[REDACTED_PHONE]", "confidence": 0.62})
        if "account" in text.lower():
            extracted.append({"entity_type": "account", "value": "[REDACTED_ACCOUNT]", "confidence": 0.58})
        return {"entities": extracted}
    if task == AITaskName.TYPOLOGY_SUGGESTION:
        return {
            "typology_name": "Rapid cashout network",
            "confidence": 0.71,
            "indicators": payload.get("indicators", [])[:4],
            "rationale": "Repeated rapid movement and linked counterparties suggest a coordinated cashout pattern.",
        }
    if task == AITaskName.EXECUTIVE_BRIEFING:
        return {
            "headline": payload.get("headline_seed") or "National threat posture update",
            "summary": payload.get("summary_seed") or "Multiple cross-bank signals require continued monitoring.",
            "priorities": payload.get("priorities", [])[:3],
            "risk_watchlist": payload.get("risk_watchlist", [])[:3],
        }
    raise AIInvocationError(f"Unsupported heuristic task: {task}")


def extract_json_payload(content: str) -> dict[str, Any]:
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        start = content.find("{")
        end = content.rfind("}")
        if start == -1 or end == -1 or end <= start:
            raise
        return json.loads(content[start : end + 1])


def build_provider_request(
    *,
    task: AITaskName,
    model: str,
    prompt: PromptDefinition,
    redacted_payload: object,
    output_model: type[BaseModel],
) -> ProviderRequest:
    return ProviderRequest(
        task=task,
        model=model,
        system_prompt=prompt.system_prompt,
        user_prompt=(
            f"TASK:\n{task}\n\nGUIDANCE:\n{prompt.guidance}\n\n"
            f"OUTPUT_SCHEMA:\n{json.dumps(output_model.model_json_schema(), ensure_ascii=True)}\n\n"
            f"INPUT:\n{json.dumps(redacted_payload, ensure_ascii=True)}"
        ),
        output_schema_name=output_model.__name__,
        output_schema=output_model.model_json_schema(),
    )


@dataclass(slots=True)
class AIInvocationResult:
    task: AITaskName
    provider: ProviderName
    model: str
    prompt_version: str
    redaction_mode: RedactionMode
    fallback_used: bool
    audit_logged: bool
    attempts: list[ProviderAttempt]
    output: BaseModel
    # V3 phase 1: log_id surfaces back to the caller so a subsequent
    # analyst correction can be tied to the originating AI invocation.
    outcome_log_id: _uuid.UUID | None = None
    latency_ms: int | None = None


class AIOrchestrator:
    def __init__(
        self,
        settings: Settings | None = None,
        providers: dict[ProviderName, LLMProvider] | None = None,
        audit_logger=record_ai_invocation,
    ) -> None:
        self.settings = settings or get_settings()
        self.providers: dict[ProviderName, LLMProvider] = providers or {
            ProviderName.OPENAI: OpenAIProvider(self.settings),
            ProviderName.ANTHROPIC: AnthropicProvider(self.settings),
            ProviderName.HEURISTIC: HeuristicProvider(),
        }
        self.audit_logger = audit_logger

    async def invoke(
        self,
        *,
        task: AITaskName,
        payload: dict[str, Any],
        output_model: type[BaseModel],
        user: AuthenticatedUser,
        ip: str | None = None,
    ) -> AIInvocationResult:
        prompt = get_prompt_definition(task)
        redaction_mode = RedactionMode(self.settings.ai_redaction_mode)
        redacted_payload = redact_payload(payload, redaction_mode)
        routes = resolve_task_routes(task, self.settings)

        if not routes:
            raise AIInvocationError("No AI providers are configured for this task.")

        attempts: list[ProviderAttempt] = []
        last_error = "No provider attempts were executed."

        for index, route in enumerate(routes):
            provider = self.providers[route.provider]
            request = build_provider_request(
                task=task,
                model=route.model,
                prompt=prompt,
                redacted_payload=redacted_payload,
                output_model=output_model,
            )
            started_at = time.perf_counter()
            try:
                response = await provider.generate_json(request)
                latency_ms = int(round((time.perf_counter() - started_at) * 1000))
                candidate = extract_json_payload(response.content)
                valid, error = validate_structured_output(output_model, candidate)
                if not valid:
                    attempts.append(
                        ProviderAttempt(
                            provider=route.provider,
                            model=route.model,
                            success=False,
                            error=error,
                        )
                    )
                    last_error = error or "Structured output validation failed."
                    continue

                structured_output = output_model.model_validate(candidate)

                # V3 phase 2: confidence routing. The provider may have
                # supplied a confidence (sovereign log-probs, heuristic
                # template-completeness); otherwise fall back to a
                # schema-validity score.
                raw_confidence = getattr(response, "confidence", None)
                confidence = (
                    cap_confidence(raw_confidence)
                    if raw_confidence is not None
                    else compute_schema_validity(structured_output)
                )
                threshold = threshold_for(task)
                is_last_route = index == len(routes) - 1
                clears_threshold = confidence >= threshold

                # The previous attempt (if any) is the fallback-from for
                # outcome-log purposes — that's what the V3 phase 4
                # training corpus exporter cares about.
                fallback_from_provider = (
                    str(attempts[-1].provider) if attempts else None
                )
                fallback_from_model = (
                    attempts[-1].model if attempts else None
                )

                attempts.append(
                    ProviderAttempt(
                        provider=route.provider,
                        model=route.model,
                        success=True,
                    )
                )

                if not clears_threshold and not is_last_route:
                    # Soft-reject: log as a fallback-from-this-provider
                    # signal for the V3 P4 training corpus, then continue
                    # to the next route. The bottom-of-chain provider is
                    # always accepted regardless of threshold to avoid
                    # total failure.
                    await self.audit_logger(
                        user=user,
                        task=task,
                        provider=route.provider,
                        model=route.model,
                        prompt_version=prompt.version,
                        redaction_mode=redaction_mode,
                        input_payload=redacted_payload,
                        output_payload=structured_output.model_dump(),
                        schema_name=output_model.__name__,
                        fallback_used=False,
                        attempt_count=len(attempts),
                        ip=ip,
                        latency_ms=latency_ms,
                        prompt_tokens=getattr(response, "prompt_tokens", None),
                        completion_tokens=getattr(response, "completion_tokens", None),
                        confidence=confidence,
                        fallback_from_provider=fallback_from_provider,
                        fallback_from_model=fallback_from_model,
                    )
                    last_error = (
                        f"Provider {route.provider} returned confidence {confidence:.2f} "
                        f"below task threshold {threshold:.2f}; falling through."
                    )
                    continue

                outcome_log_id = await self.audit_logger(
                    user=user,
                    task=task,
                    provider=route.provider,
                    model=route.model,
                    prompt_version=prompt.version,
                    redaction_mode=redaction_mode,
                    input_payload=redacted_payload,
                    output_payload=structured_output.model_dump(),
                    schema_name=output_model.__name__,
                    fallback_used=index > 0,
                    attempt_count=len(attempts),
                    ip=ip,
                    latency_ms=latency_ms,
                    prompt_tokens=getattr(response, "prompt_tokens", None),
                    completion_tokens=getattr(response, "completion_tokens", None),
                    confidence=confidence,
                    fallback_from_provider=fallback_from_provider,
                    fallback_from_model=fallback_from_model,
                )
                return AIInvocationResult(
                    task=task,
                    provider=route.provider,
                    model=route.model,
                    prompt_version=prompt.version,
                    redaction_mode=redaction_mode,
                    fallback_used=index > 0,
                    audit_logged=outcome_log_id is not None,
                    attempts=attempts,
                    output=structured_output,
                    outcome_log_id=outcome_log_id,
                    latency_ms=latency_ms,
                )
            except Exception as exc:
                attempts.append(
                    ProviderAttempt(
                        provider=route.provider,
                        model=route.model,
                        success=False,
                        error=str(exc),
                    )
                )
                last_error = str(exc)

        raise AIInvocationError(last_error)
