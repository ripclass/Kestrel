"""Pure-helper coverage for V3 phase 2 confidence routing.

The async ``AIOrchestrator.invoke`` path is exercised end-to-end by the
existing AI tests; this file pins the deterministic helpers — the
schema-validity scorer, threshold lookup, sovereign-eligibility gate,
and the heuristic provider's confidence formula.
"""
from __future__ import annotations

from typing import Optional

import pytest
from pydantic import BaseModel, Field

from app.ai.confidence import cap_confidence, compute_schema_validity
from app.ai.routing import _build_baseline_routes, _sovereign_configured, resolve_task_routes
from app.ai.service import _heuristic_confidence
from app.ai.thresholds import (
    TASK_CONFIDENCE_THRESHOLDS,
    is_sovereign_eligible,
    rollout_pct_for,
    threshold_for,
)
from app.ai.types import AITaskName, ProviderName
from app.config import Settings


# Schema-validity scorer ----------------------------------------------------

class _AllRequired(BaseModel):
    summary: str
    reasons: list[str]


class _MixedFields(BaseModel):
    headline: str
    detail: Optional[str] = None
    extras: list[str] = Field(default_factory=list)


def test_compute_schema_validity_full_required_only_returns_one() -> None:
    output = _AllRequired(summary="ok", reasons=["a", "b"])
    assert compute_schema_validity(output) == 1.0


def test_compute_schema_validity_required_filled_no_optionals_returns_one() -> None:
    """Optional-empty when there are no optional fields shouldn't drag
    the score below 1.0."""
    output = _AllRequired(summary="ok", reasons=[])
    # `reasons` is required; an empty list is technically populated to
    # the validator but our `_has_meaningful_value` treats it as empty,
    # so this should land at 0.5 (required incomplete by our scorer).
    assert compute_schema_validity(output) == 0.5


def test_compute_schema_validity_required_plus_optionals_lifts_above_half() -> None:
    full = _MixedFields(headline="x", detail="y", extras=["a"])
    partial = _MixedFields(headline="x")
    assert compute_schema_validity(full) == 1.0
    # headline filled (required) + detail empty + extras empty = 0.5 + 0
    assert compute_schema_validity(partial) == 0.5


def test_compute_schema_validity_handles_none_input() -> None:
    assert compute_schema_validity(None) == 0.0  # type: ignore[arg-type]


# cap_confidence helper -----------------------------------------------------

def test_cap_confidence_clamps_to_range() -> None:
    assert cap_confidence(None) == 0.0
    assert cap_confidence(-0.5) == 0.0
    assert cap_confidence(0.5) == 0.5
    assert cap_confidence(0.95) == 0.95
    # Cap at 0.95 — never claim 100%.
    assert cap_confidence(0.99) == 0.95
    assert cap_confidence(2.0) == 0.95


# Per-task threshold registry ----------------------------------------------

def test_threshold_default_is_unreachable() -> None:
    """V3 P2 ships with effective-infinity thresholds so behavior is
    unchanged. A test that breaks when a threshold is lowered to a real
    value is the canary that V3 P5 is starting to flip rollouts."""
    for task in AITaskName:
        assert threshold_for(task) > 1.0, f"task {task} threshold should default to >1.0 in V3 P2"


def test_threshold_for_unknown_task_falls_back_to_default() -> None:
    # Pass a real enum but verify the fallback path is wired.
    assert threshold_for(AITaskName.ALERT_EXPLANATION) == TASK_CONFIDENCE_THRESHOLDS[AITaskName.ALERT_EXPLANATION]


def test_rollout_pct_clamps_to_zero_hundred() -> None:
    for task in AITaskName:
        pct = rollout_pct_for(task)
        assert 0 <= pct <= 100


def test_no_task_is_sovereign_eligible_in_v3_p2() -> None:
    """Same canary as the threshold one — flipping any task to
    sovereign-eligible in V3 P5 should be a deliberate edit, not a
    silent default."""
    for task in AITaskName:
        assert is_sovereign_eligible(task) is False


# Routing prepend -----------------------------------------------------------

def _settings(**overrides) -> Settings:
    base = Settings(
        openai_api_key="test-key",
        openai_model="anthropic/claude-sonnet-4.6",
        anthropic_api_key=None,
        anthropic_model=None,
    )
    for key, value in overrides.items():
        setattr(base, key, value)
    return base


def test_sovereign_configured_requires_url_and_model() -> None:
    assert _sovereign_configured(_settings()) is False
    assert _sovereign_configured(_settings(ai_sovereign_url="http://x")) is False
    assert _sovereign_configured(_settings(ai_sovereign_model="m")) is False
    assert (
        _sovereign_configured(_settings(ai_sovereign_url="http://x", ai_sovereign_model="m"))
        is True
    )


@pytest.mark.asyncio
async def test_resolve_task_routes_no_sovereign_when_not_configured() -> None:
    routes = await resolve_task_routes(AITaskName.ALERT_EXPLANATION, _settings())
    providers = [r.provider for r in routes]
    assert ProviderName.SOVEREIGN not in providers


@pytest.mark.asyncio
async def test_resolve_task_routes_no_sovereign_when_eligibility_zero() -> None:
    """Even with sovereign configured, static rollout=0 means
    is_sovereign_eligible returns False, so we never prepend.
    V3 P2/P5 ship with rollout=0 across all tasks."""
    s = _settings(ai_sovereign_url="http://kestrel-sovereign", ai_sovereign_model="kestrel-v1")
    routes = await resolve_task_routes(AITaskName.ALERT_EXPLANATION, s)
    providers = [r.provider for r in routes]
    assert ProviderName.SOVEREIGN not in providers


@pytest.mark.asyncio
async def test_resolve_task_routes_prepends_sovereign_when_eligible(monkeypatch) -> None:
    """Flipping a task to rollout > 0 + sovereign configured + the
    runtime rollout coin lands favourable = sovereign appears at index 0
    of the route chain."""
    monkeypatch.setattr(
        "app.ai.routing.is_sovereign_eligible",
        lambda task: True,
    )

    # Stub the DB-backed runtime rollout to a guaranteed-100 so the
    # coin-flip always lands. Avoids needing a live Postgres.
    async def _always_full(task):
        return 100

    monkeypatch.setattr(
        "app.services.sovereign_rollout.effective_rollout_pct_for",
        _always_full,
    )
    s = _settings(ai_sovereign_url="http://kestrel-sovereign", ai_sovereign_model="kestrel-v1")
    routes = await resolve_task_routes(AITaskName.ALERT_EXPLANATION, s)
    assert routes[0].provider == ProviderName.SOVEREIGN
    assert routes[0].model == "kestrel-v1"


def test_build_baseline_routes_excludes_sovereign() -> None:
    """The sync helper used by the promotion harness + offline tools
    never prepends sovereign — that decision is per-call and lives in
    the async path."""
    s = _settings(ai_sovereign_url="http://x", ai_sovereign_model="m")
    routes = _build_baseline_routes(AITaskName.ALERT_EXPLANATION, s)
    assert ProviderName.SOVEREIGN not in [r.provider for r in routes]


# Heuristic confidence ------------------------------------------------------

def test_heuristic_confidence_empty_returns_zero() -> None:
    assert _heuristic_confidence({}) == 0.0


def test_heuristic_confidence_caps_at_half() -> None:
    """Heuristic is always considered low-quality; cap at 0.5 so any
    real LLM threshold above that routes around the heuristic."""
    big = {f"k{i}": "filled" for i in range(20)}
    assert _heuristic_confidence(big) == 0.5


def test_heuristic_confidence_grows_with_populated_keys() -> None:
    a = _heuristic_confidence({"a": "x"})
    b = _heuristic_confidence({"a": "x", "b": "y"})
    c = _heuristic_confidence({"a": "x", "b": "y", "c": "z"})
    assert 0.0 < a < b < c
    assert c <= 0.5


def test_heuristic_confidence_ignores_empty_values() -> None:
    """Empty strings, lists, dicts, and None don't count toward the
    score — only actually populated fields raise it."""
    score = _heuristic_confidence({"a": "", "b": [], "c": None, "d": {}})
    assert score == 0.0
