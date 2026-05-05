"""Pure-helper coverage for the investigation agent (V3 phase 3).

The async ``run_investigation`` path is async + DB-touching; this file
pins the deterministic helpers — the heuristic decider's plan, the
context summariser's bounding, the synthesised hypothesis + suggested
actions, and the red-team adversarial scenarios.
"""
from __future__ import annotations

import uuid

import pytest

from app.agents.investigation_agent import (
    ALLOWED_TOOLS,
    MAX_HOPS,
    MAX_WALL_CLOCK_SECONDS,
    AgentEvidenceItem,
    AgentHopDecision,
    _heuristic_decider,
    _summarise_for_context,
    _synthesise_actions,
    _synthesise_confidence,
    _synthesise_hypothesis,
)
from app.agents.tools import TOOL_REGISTRY


# Whitelist invariants -----------------------------------------------------

def test_allowed_tools_matches_registry() -> None:
    """The agent's tool whitelist + the registry must agree, or the
    loop tries to dispatch a tool the registry doesn't have."""
    assert ALLOWED_TOOLS == set(TOOL_REGISTRY.keys())


def test_allowed_tools_has_all_six_v3_tools() -> None:
    expected = {
        "resolve_entity",
        "neighbours",
        "recent_alerts",
        "recent_strs",
        "screen_entity",
        "build_narrative",
    }
    assert ALLOWED_TOOLS == expected


def test_max_hops_is_eight() -> None:
    assert MAX_HOPS == 8


def test_wall_clock_cap_is_sixty() -> None:
    assert MAX_WALL_CLOCK_SECONDS == 60.0


# Context summariser ------------------------------------------------------

def test_summarise_for_context_truncates_long_strings() -> None:
    long_text = "x" * 1000
    result = _summarise_for_context({"narrative": long_text}, max_chars=200)
    assert len(result["narrative"]) <= 250  # 200 + ellipsis
    assert result["narrative"].endswith("…")


def test_summarise_for_context_truncates_long_lists() -> None:
    big = list(range(100))
    result = _summarise_for_context({"items": big})
    assert len(result["items"]) == 11  # 10 items + truncation marker
    assert result["items"][-1] == "… (truncated)"


def test_summarise_for_context_passes_through_short_payloads() -> None:
    payload = {"a": "short", "b": [1, 2, 3]}
    assert _summarise_for_context(payload) == payload


# Heuristic decider plan --------------------------------------------------

@pytest.mark.asyncio
async def test_heuristic_decider_walks_plan_in_order() -> None:
    decide = _heuristic_decider()
    context = {
        "analyst_prompt": "investigate this entity",
        "entity_id": str(uuid.uuid4()),
        "hops_used": 0,
        "hops_remaining": 8,
        "evidence_so_far": [
            {"hop": 0, "tool": "resolve_entity", "result_summary": {"display_name": "Mohammad Karim"}}
        ],
    }
    decision = await decide(context)
    assert decision.tool_name == "neighbours"
    assert decision.done is False


@pytest.mark.asyncio
async def test_heuristic_decider_skips_already_used_tools() -> None:
    decide = _heuristic_decider()
    context = {
        "analyst_prompt": "investigate",
        "entity_id": str(uuid.uuid4()),
        "evidence_so_far": [
            {"hop": 0, "tool": "resolve_entity", "result_summary": {"display_name": "X"}},
            {"hop": 1, "tool": "neighbours", "result_summary": {"neighbours": []}},
            {"hop": 2, "tool": "recent_alerts", "result_summary": {"alerts": []}},
        ],
    }
    decision = await decide(context)
    assert decision.tool_name == "recent_strs"


@pytest.mark.asyncio
async def test_heuristic_decider_skips_screen_when_no_name() -> None:
    """Without a display_name OR display_value on the seed,
    screen_entity has no target — the heuristic decider should skip it
    rather than dispatch a tool that would refuse the call."""
    decide = _heuristic_decider()
    context = {
        "analyst_prompt": "investigate",
        "entity_id": str(uuid.uuid4()),
        "evidence_so_far": [
            {"hop": 0, "tool": "resolve_entity", "result_summary": {}},
            {"hop": 1, "tool": "neighbours", "result_summary": {"neighbours": []}},
            {"hop": 2, "tool": "recent_alerts", "result_summary": {"alerts": []}},
            {"hop": 3, "tool": "recent_strs", "result_summary": {"strs": []}},
        ],
    }
    decision = await decide(context)
    assert decision.tool_name == "build_narrative"


@pytest.mark.asyncio
async def test_heuristic_decider_finalises_when_plan_exhausted() -> None:
    decide = _heuristic_decider()
    context = {
        "analyst_prompt": "investigate",
        "entity_id": str(uuid.uuid4()),
        "evidence_so_far": [
            {"hop": 0, "tool": "resolve_entity", "result_summary": {"display_name": "X"}},
            {"hop": 1, "tool": "neighbours", "result_summary": {"neighbours": []}},
            {"hop": 2, "tool": "recent_alerts", "result_summary": {"alerts": []}},
            {"hop": 3, "tool": "recent_strs", "result_summary": {"strs": []}},
            {"hop": 4, "tool": "screen_entity", "result_summary": {"matches": []}},
            {"hop": 5, "tool": "build_narrative", "result_summary": {"narrative_seed": "x"}},
        ],
    }
    decision = await decide(context)
    assert decision.done is True
    assert decision.final_hypothesis is not None


# Hypothesis synthesiser --------------------------------------------------

def test_synthesise_hypothesis_no_evidence() -> None:
    assert _synthesise_hypothesis({"evidence_so_far": []}) == "No evidence collected — open a manual review."


def test_synthesise_hypothesis_aggregates_evidence_counts() -> None:
    context = {
        "evidence_so_far": [
            {"tool": "neighbours", "result_summary": {"neighbours": [1, 2, 3]}},
            {"tool": "recent_alerts", "result_summary": {"alerts": [1, 2]}},
        ]
    }
    h = _synthesise_hypothesis(context)
    assert "3 connected entities" in h
    assert "2 recent alerts" in h


# Confidence synthesiser --------------------------------------------------

def test_synthesise_confidence_lifts_on_sanctions_hit() -> None:
    context = {
        "evidence_so_far": [
            {"tool": "screen_entity", "result_summary": {"matches": [{"list_source": "OFAC"}]}},
        ]
    }
    assert _synthesise_confidence(context) >= 0.85


def test_synthesise_confidence_floor_with_empty_evidence() -> None:
    """A clean dossier still produces a non-zero confidence so the
    final result is actionable, but stays below the 'review' band."""
    assert _synthesise_confidence({"evidence_so_far": []}) == 0.4


def test_synthesise_confidence_capped_at_nine_tenths() -> None:
    """The synthesiser must never claim 1.0 — that's the threshold a
    real sovereign adapter must clear."""
    context = {
        "evidence_so_far": [
            {"tool": "screen_entity", "result_summary": {"matches": [{}, {}, {}]}},
            {"tool": "recent_alerts", "result_summary": {"alerts": [1, 2, 3]}},
            {"tool": "recent_strs", "result_summary": {"strs": [1, 2]}},
            {"tool": "neighbours", "result_summary": {"neighbours": [1, 2, 3, 4, 5]}},
        ]
    }
    assert _synthesise_confidence(context) <= 0.9


# Suggested actions -------------------------------------------------------

def test_synthesise_actions_recommends_str_on_screen_hit() -> None:
    context = {
        "evidence_so_far": [
            {"tool": "screen_entity", "result_summary": {"matches": [{"list_source": "OFAC"}]}},
        ]
    }
    actions = _synthesise_actions(context)
    assert "draft_str" in actions
    assert "open_case" in actions


def test_synthesise_actions_supplements_when_prior_strs() -> None:
    context = {
        "evidence_so_far": [
            {"tool": "screen_entity", "result_summary": {"matches": []}},
            {"tool": "recent_strs", "result_summary": {"strs": [{"id": "abc"}]}},
        ]
    }
    actions = _synthesise_actions(context)
    assert "request_str_supplement" in actions


def test_synthesise_actions_monitor_when_clean() -> None:
    context = {
        "evidence_so_far": [
            {"tool": "screen_entity", "result_summary": {"matches": []}},
            {"tool": "recent_strs", "result_summary": {"strs": []}},
        ]
    }
    assert _synthesise_actions(context) == ["monitor"]


# Hop decision schema -----------------------------------------------------

def test_agent_hop_decision_round_trips() -> None:
    decision = AgentHopDecision(
        reasoning="initial",
        done=False,
        tool_name="neighbours",
        tool_args={"entity_id": "x"},
    )
    dumped = decision.model_dump()
    assert dumped["tool_name"] == "neighbours"
    assert dumped["done"] is False


def test_agent_evidence_item_carries_required_fields() -> None:
    item = AgentEvidenceItem(
        hop=2,
        tool="neighbours",
        args={"entity_id": "x"},
        result={"neighbours": []},
    )
    assert item.hop == 2
    assert item.error is None
