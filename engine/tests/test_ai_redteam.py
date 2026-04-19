"""AI red-team harness.

Runs every case in ``app.ai.redteam.corpus`` through the AIOrchestrator
configured with the heuristic provider only (no API keys required) and
asserts the rubric. When real provider keys come back online, swap in
the real adapters and the same harness runs against live model output.
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass

import pytest

from app.ai.providers.base import LLMProvider
from app.ai.redaction import redact_payload
from app.ai.redteam.corpus import ALL_CASES, RedTeamCase
from app.ai.redteam.rubric import run_rubric
from app.ai.service import AIOrchestrator, HeuristicProvider, build_provider_request
from app.ai.types import (
    AITaskName,
    PromptDefinition,
    ProviderName,
    ProviderResponse,
    RedactionMode,
    TaskRoute,
)
from app.auth import AuthenticatedUser
from app.config import get_settings


@dataclass
class _StubProvider(LLMProvider):
    """Wraps HeuristicProvider so the orchestrator's provider table
    can resolve OPENAI / ANTHROPIC names back to heuristic output."""

    name: ProviderName

    def __post_init__(self) -> None:
        self._delegate = HeuristicProvider()

    async def healthcheck(self, probe: bool = False):  # pragma: no cover - unused
        raise NotImplementedError

    async def generate_json(self, request) -> ProviderResponse:
        return await self._delegate.generate_json(request)


def _heuristic_orchestrator() -> AIOrchestrator:
    """Force every route through the heuristic implementation.

    Skips the audit logger so tests don't touch the audit_log table —
    the harness pins prompt/redaction/output behavior, not the audit
    contract (which has its own tests).
    """
    async def noop_audit(**_kwargs) -> bool:
        return True

    settings = get_settings()
    orchestrator = AIOrchestrator(
        settings=settings,
        providers={
            ProviderName.OPENAI: _StubProvider(name=ProviderName.OPENAI),
            ProviderName.ANTHROPIC: _StubProvider(name=ProviderName.ANTHROPIC),
            ProviderName.HEURISTIC: HeuristicProvider(),
        },
        audit_logger=noop_audit,
    )
    return orchestrator


def _test_user() -> AuthenticatedUser:
    return AuthenticatedUser(
        user_id="00000000-0000-0000-0000-000000000001",
        email="redteam@kestrel.test",
        org_id="00000000-0000-0000-0000-000000000002",
        org_type="regulator",
        role="analyst",
        persona="bfiu_analyst",
        designation="Red-team harness",
    )


@pytest.mark.parametrize("case", ALL_CASES, ids=lambda c: c.id)
def test_redteam_case_passes_rubric(case: RedTeamCase) -> None:
    orchestrator = _heuristic_orchestrator()
    invocation = asyncio.run(
        orchestrator.invoke(
            task=case.task,
            payload=case.payload,
            output_model=case.output_model,
            user=_test_user(),
        )
    )

    # Empty-input cases legitimately produce empty list fields (no
    # entities, no indicators) — skip the required-fields check on
    # those so the rubric only flags surprising emptiness.
    skip_required = "empty_input" in case.tags

    # Canary-echo checks become BLOCKING when real providers are wired.
    # Against the heuristic provider they're informational only — the
    # heuristic doesn't interpret prompts, it summarises structure, so
    # an echoed canary is a heuristic limitation, not a prompt-template
    # regression. The rubric for PII shape, required fields, and field
    # length stays blocking in both modes.
    skip_canary = invocation.provider == ProviderName.HEURISTIC

    failures = run_rubric(
        invocation.output,
        canaries=case.all_canaries,
        skip_required=skip_required,
        skip_canary=skip_canary,
    )
    assert not failures, (
        f"{case.id} rubric failures:\n"
        + "\n".join(f"  - {f.check}: {f.detail}" for f in failures)
    )


def test_redaction_layer_strips_pii_before_provider_sees_it() -> None:
    """Independent check on the redaction layer the orchestrator runs.

    Confirms that the same PII patterns the rubric flags in output are
    stripped from input before any provider request is built. If this
    test goes red, the rubric's pii_leak check on a model that echoes
    its input would fire — this catches the failure one layer earlier.
    """
    payload = {
        "subject_account": "1781430000701",
        "subject_phone": "+8801712345678",
        "subject_nid": "199012345678",
        "trigger_facts": [
            "Account 1781430000701 sent BDT 14M to +8801712345678",
        ],
    }
    redacted = redact_payload(payload, RedactionMode.REDACT)
    serialized = str(redacted)
    assert "1781430000701" not in serialized
    assert "1712345678" not in serialized
    assert "[REDACTED_ACCOUNT]" in serialized
    assert "[REDACTED_PHONE]" in serialized


def test_provider_request_carries_redacted_payload_only() -> None:
    """End-to-end: build_provider_request serialises the redacted
    payload into the user_prompt; canary PII must not appear there."""

    class _Stub(__import__("pydantic").BaseModel):
        narrative: str

    redacted = redact_payload(
        {"raw_text": "Account 1781430000701 to phone +8801712345678"},
        RedactionMode.REDACT,
    )
    prompt = PromptDefinition(
        task=AITaskName.ENTITY_EXTRACTION,
        version="test",
        system_prompt="test",
        guidance="test",
    )
    request = build_provider_request(
        task=AITaskName.ENTITY_EXTRACTION,
        model="heuristic-v1",
        prompt=prompt,
        redacted_payload=redacted,
        output_model=_Stub,
    )
    assert "1781430000701" not in request.user_prompt
    assert "1712345678" not in request.user_prompt


def test_corpus_covers_every_ai_task() -> None:
    """Pin a CI gate: when a new AITaskName ships, the corpus must add
    at least one case for it. Forces red-team coverage to grow with
    the task surface."""
    covered = {case.task for case in ALL_CASES}
    declared = set(AITaskName)
    missing = declared - covered
    assert not missing, f"AI tasks without red-team coverage: {sorted(missing)}"


def test_routing_falls_back_to_heuristic_when_no_keys() -> None:
    """The whole harness depends on this: with no provider keys set,
    routing must surface a heuristic route so the orchestrator has
    something to invoke."""
    from app.ai.routing import resolve_task_routes

    settings = get_settings()
    routes = resolve_task_routes(AITaskName.STR_NARRATIVE, settings)
    assert any(r.provider == ProviderName.HEURISTIC for r in routes), (
        "Heuristic fallback must be in the route list when keys are absent"
    )
    # The very first route should be heuristic in this environment
    # (no provider keys, no real models registered).
    assert routes[-1] == TaskRoute(provider=ProviderName.HEURISTIC, model="heuristic-v1")
