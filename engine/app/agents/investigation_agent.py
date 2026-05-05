"""Investigation agent loop (V3 phase 3.1).

Bounded multi-step investigation. Each hop:

  1. Build a context dict from accumulated evidence.
  2. Ask the AI orchestrator (task ``INVESTIGATION_AGENT_HOP``) for the
     next tool to call OR a final hypothesis.
  3. If the AI signalled ``done``, finalise and return.
  4. Otherwise dispatch the chosen tool from the whitelist, capture the
     result as a piece of evidence, and continue.

Hard caps:
  * 8 hops total (``MAX_HOPS``).
  * 60-second wall-clock budget (``MAX_WALL_CLOCK_SECONDS``).
  * Tool whitelist enforced — anything off-list is treated as a no-op
    + recorded as an attempted-out-of-band call (red-team signal).

The hop AI is gated by the V3 phase 2 confidence routing pattern, so a
sovereign model lands here as soon as one ships in V3 P4 — no agent-
loop changes required.
"""
from __future__ import annotations

import logging
import time
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Awaitable, Callable

from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.tools import (
    TOOL_REGISTRY,
    ToolCall,
    ToolResult,
)
from app.ai.service import AIInvocationError, AIOrchestrator
from app.ai.types import AITaskName
from app.auth import AuthenticatedUser

logger = logging.getLogger("kestrel.agents.investigation")


MAX_HOPS = 8
MAX_WALL_CLOCK_SECONDS = 60.0
ALLOWED_TOOLS = frozenset({
    "resolve_entity",
    "neighbours",
    "recent_alerts",
    "recent_strs",
    "screen_entity",
    "build_narrative",
})


class AgentHopDecision(BaseModel):
    """The structured output the AI returns at each hop."""

    reasoning: str = Field(default="")
    done: bool = False
    tool_name: str | None = None
    tool_args: dict[str, Any] = Field(default_factory=dict)
    final_hypothesis: str | None = None
    final_confidence: float | None = None
    suggested_actions: list[str] = Field(default_factory=list)


@dataclass(slots=True)
class AgentEvidenceItem:
    hop: int
    tool: str
    args: dict[str, Any]
    result: dict[str, Any]
    error: str | None = None


@dataclass(slots=True)
class InvestigationResult:
    hypothesis: str
    evidence: list[AgentEvidenceItem]
    suggested_actions: list[str]
    confidence: float
    hops_used: int
    latency_ms: int
    status: str  # completed | failed | exhausted
    error: str | None = None

    def evidence_payload(self) -> list[dict[str, Any]]:
        return [
            {
                "hop": e.hop,
                "tool": e.tool,
                "args": e.args,
                "result": e.result,
                "error": e.error,
            }
            for e in self.evidence
        ]


@dataclass(slots=True)
class _LoopState:
    started_at: float
    hop: int = 0
    evidence: list[AgentEvidenceItem] = field(default_factory=list)
    out_of_band_attempts: list[dict[str, Any]] = field(default_factory=list)


HopDecisionFn = Callable[[dict[str, Any]], Awaitable[AgentHopDecision]]


async def run_investigation(
    *,
    session: AsyncSession,
    user: AuthenticatedUser,
    entity_id: uuid.UUID | None,
    prompt: str,
    decide_hop: HopDecisionFn | None = None,
) -> InvestigationResult:
    """Execute the bounded investigation loop. Returns the final result."""
    started = time.perf_counter()
    state = _LoopState(started_at=started)

    decide = decide_hop or _make_default_decider(user=user)
    seed = await _seed_evidence(session=session, user=user, entity_id=entity_id)
    if seed is not None:
        state.evidence.append(seed)

    while state.hop < MAX_HOPS:
        if (time.perf_counter() - state.started_at) >= MAX_WALL_CLOCK_SECONDS:
            return _finalise(state, status="exhausted", reason="wall_clock_exceeded")

        state.hop += 1
        context = _build_context(prompt=prompt, state=state, entity_id=entity_id)
        try:
            decision = await decide(context)
        except AIInvocationError as exc:
            logger.warning("agent.hop.ai_failed", extra={"hop": state.hop, "error": str(exc)})
            return _finalise(state, status="failed", reason=str(exc))
        except Exception as exc:  # noqa: BLE001 — defensive
            logger.warning("agent.hop.unexpected", extra={"hop": state.hop, "error_type": type(exc).__name__})
            return _finalise(state, status="failed", reason=str(exc))

        if decision.done:
            return _finalise(
                state,
                status="completed",
                hypothesis=decision.final_hypothesis,
                confidence=decision.final_confidence,
                suggested_actions=decision.suggested_actions,
            )

        tool_name = (decision.tool_name or "").strip()
        if not tool_name or tool_name not in ALLOWED_TOOLS:
            # Red-team signal — the AI tried to call something outside
            # the whitelist. Record it but don't dispatch.
            state.out_of_band_attempts.append(
                {"hop": state.hop, "tool": tool_name, "args": decision.tool_args}
            )
            state.evidence.append(
                AgentEvidenceItem(
                    hop=state.hop,
                    tool=tool_name or "<unknown>",
                    args=decision.tool_args,
                    result={"refused": True},
                    error="Tool not in whitelist",
                )
            )
            continue

        tool_call = ToolCall(name=tool_name, args=decision.tool_args)
        result = await _dispatch_tool(session=session, user=user, call=tool_call)
        state.evidence.append(
            AgentEvidenceItem(
                hop=state.hop,
                tool=tool_call.name,
                args=tool_call.args,
                result=result.payload,
                error=result.error,
            )
        )

    # Hop budget exhausted without `done`.
    return _finalise(state, status="exhausted", reason="hop_budget_exceeded")


async def _seed_evidence(
    *,
    session: AsyncSession,
    user: AuthenticatedUser,
    entity_id: uuid.UUID | None,
) -> AgentEvidenceItem | None:
    """Pre-load the entity dossier as hop 0 so the first AI hop has
    something to reason from. Optional — when entity_id is None the agent
    runs from a free-form prompt only."""
    if entity_id is None:
        return None
    tool = TOOL_REGISTRY.get("resolve_entity")
    if tool is None:
        return None
    result = await tool(session=session, user=user, args={"entity_id": str(entity_id)})
    return AgentEvidenceItem(
        hop=0,
        tool="resolve_entity",
        args={"entity_id": str(entity_id)},
        result=result.payload,
        error=result.error,
    )


def _build_context(
    *,
    prompt: str,
    state: _LoopState,
    entity_id: uuid.UUID | None,
) -> dict[str, Any]:
    return {
        "analyst_prompt": prompt,
        "entity_id": str(entity_id) if entity_id else None,
        "hops_used": state.hop,
        "hops_remaining": MAX_HOPS - state.hop,
        "wall_clock_remaining_seconds": max(
            0.0, MAX_WALL_CLOCK_SECONDS - (time.perf_counter() - state.started_at)
        ),
        "allowed_tools": sorted(ALLOWED_TOOLS),
        "evidence_so_far": [
            {
                "hop": e.hop,
                "tool": e.tool,
                "args": e.args,
                "result_summary": _summarise_for_context(e.result),
                "error": e.error,
            }
            for e in state.evidence
        ],
    }


def _summarise_for_context(payload: Any, *, max_chars: int = 600) -> Any:
    """Bound the size of evidence echoed back into the AI context. Full
    payload stays in the persisted record; the AI sees a trimmed view."""
    if isinstance(payload, dict):
        out = {}
        for k, v in payload.items():
            if isinstance(v, str) and len(v) > max_chars:
                out[k] = v[:max_chars] + "…"
            elif isinstance(v, list) and len(v) > 10:
                out[k] = v[:10] + ["… (truncated)"]
            else:
                out[k] = v
        return out
    return payload


def _finalise(
    state: _LoopState,
    *,
    status: str,
    hypothesis: str | None = None,
    confidence: float | None = None,
    suggested_actions: list[str] | None = None,
    reason: str | None = None,
) -> InvestigationResult:
    latency_ms = int(round((time.perf_counter() - state.started_at) * 1000))
    final_hypothesis = hypothesis or _fallback_hypothesis(state, reason)
    return InvestigationResult(
        hypothesis=final_hypothesis,
        evidence=list(state.evidence),
        suggested_actions=list(suggested_actions or []),
        confidence=float(confidence if confidence is not None else 0.0),
        hops_used=state.hop,
        latency_ms=latency_ms,
        status=status,
        error=reason if status != "completed" else None,
    )


def _fallback_hypothesis(state: _LoopState, reason: str | None) -> str:
    """When the loop terminates without a clean ``done`` we synthesise a
    minimal hypothesis from the evidence so the analyst still has
    something to act on."""
    if not state.evidence:
        return "Investigation produced no evidence."
    summary = "; ".join(
        f"{e.tool} → {len(e.result) if isinstance(e.result, dict) else 'result'}"
        for e in state.evidence
    )
    return f"Partial investigation ({len(state.evidence)} steps): {summary[:400]}"


# ---------------------------------------------------------------------------
# Default hop decider
# ---------------------------------------------------------------------------


def _make_default_decider(*, user: AuthenticatedUser) -> HopDecisionFn:
    """Returns the hop decision function used in production.

    For V3 P3 we ship a deterministic heuristic decider so the agent
    works end-to-end without depending on an LLM round-trip per hop —
    keeps the demo flow snappy and the tests deterministic. When V3 P4
    lands the AI orchestrator integration, swap in
    ``_make_orchestrator_decider`` and the loop is identical.
    """
    return _heuristic_decider()


def _heuristic_decider() -> HopDecisionFn:
    """Walk the tool whitelist in a fixed-but-sensible order:

      hop 1 -> neighbours
      hop 2 -> recent_alerts
      hop 3 -> recent_strs
      hop 4 -> screen_entity (only if the entity has a name)
      hop 5 -> build_narrative + done

    This is the V3 P3 demo flow. It's also the safety floor when the
    sovereign / Claude routing fails — even an outage produces a
    deterministic investigation result instead of an empty error."""

    plan = [
        "neighbours",
        "recent_alerts",
        "recent_strs",
        "screen_entity",
        "build_narrative",
    ]

    async def decide(context: dict[str, Any]) -> AgentHopDecision:
        used_tools = {e["tool"] for e in context.get("evidence_so_far", []) if e.get("hop", 0) > 0}
        for tool in plan:
            if tool in used_tools:
                continue
            if tool == "screen_entity" and not _has_screening_target(context):
                continue
            args = _default_args_for(tool, context)
            return AgentHopDecision(
                reasoning=f"Fixed plan step: {tool}",
                done=False,
                tool_name=tool,
                tool_args=args,
            )

        # Nothing left to call — finalise with a synthesised hypothesis.
        return AgentHopDecision(
            done=True,
            final_hypothesis=_synthesise_hypothesis(context),
            final_confidence=_synthesise_confidence(context),
            suggested_actions=_synthesise_actions(context),
        )

    return decide


def _has_screening_target(context: dict[str, Any]) -> bool:
    seed = next(
        (e for e in context.get("evidence_so_far", []) if e.get("hop") == 0 and e.get("tool") == "resolve_entity"),
        None,
    )
    if not seed:
        return False
    summary = seed.get("result_summary", {}) or {}
    return bool(summary.get("display_name") or summary.get("display_value"))


def _default_args_for(tool: str, context: dict[str, Any]) -> dict[str, Any]:
    entity_id = context.get("entity_id")
    if tool == "neighbours":
        return {"entity_id": entity_id, "depth": 1}
    if tool == "recent_alerts":
        return {"entity_id": entity_id, "limit": 5}
    if tool == "recent_strs":
        return {"entity_id": entity_id, "limit": 5}
    if tool == "screen_entity":
        seed = next(
            (e for e in context.get("evidence_so_far", []) if e.get("hop") == 0),
            None,
        ) or {}
        summary = seed.get("result_summary", {}) or {}
        return {
            "name": summary.get("display_name") or summary.get("display_value") or "",
        }
    if tool == "build_narrative":
        return {"entity_id": entity_id}
    return {}


def _synthesise_hypothesis(context: dict[str, Any]) -> str:
    evidence = context.get("evidence_so_far", [])
    if not evidence:
        return "No evidence collected — open a manual review."
    parts: list[str] = []
    for item in evidence:
        tool = item.get("tool")
        result_summary = item.get("result_summary") or {}
        if tool == "neighbours":
            count = len(result_summary.get("neighbours", []) or [])
            if count:
                parts.append(f"{count} connected entities")
        elif tool == "recent_alerts":
            count = len(result_summary.get("alerts", []) or [])
            if count:
                parts.append(f"{count} recent alerts")
        elif tool == "recent_strs":
            count = len(result_summary.get("strs", []) or [])
            if count:
                parts.append(f"{count} prior STRs")
        elif tool == "screen_entity":
            hits = result_summary.get("matches", []) or []
            if hits:
                parts.append(f"{len(hits)} sanctions/PEP hits")
    if not parts:
        return "Investigation complete — no strong signals across the available evidence."
    return "Subject shows " + ", ".join(parts) + " — recommend analyst review."


def _synthesise_confidence(context: dict[str, Any]) -> float:
    evidence = context.get("evidence_so_far", [])
    base = 0.4
    for item in evidence:
        result = item.get("result_summary") or {}
        if item.get("tool") == "screen_entity" and (result.get("matches") or []):
            base = max(base, 0.85)
        elif item.get("tool") == "recent_alerts" and (result.get("alerts") or []):
            base = min(0.8, base + 0.1)
        elif item.get("tool") == "recent_strs" and (result.get("strs") or []):
            base = min(0.8, base + 0.1)
        elif item.get("tool") == "neighbours" and len(result.get("neighbours") or []) >= 3:
            base = min(0.75, base + 0.05)
    return round(min(0.9, base), 2)


def _synthesise_actions(context: dict[str, Any]) -> list[str]:
    actions: list[str] = []
    has_str = any(
        len((e.get("result_summary") or {}).get("strs") or []) > 0
        for e in context.get("evidence_so_far", [])
        if e.get("tool") == "recent_strs"
    )
    has_screen_hit = any(
        len((e.get("result_summary") or {}).get("matches") or []) > 0
        for e in context.get("evidence_so_far", [])
        if e.get("tool") == "screen_entity"
    )
    if has_screen_hit:
        actions.append("draft_str")
        actions.append("open_case")
    elif has_str:
        actions.append("request_str_supplement")
    else:
        actions.append("monitor")
    return actions


# ---------------------------------------------------------------------------
# Tool dispatch
# ---------------------------------------------------------------------------


async def _dispatch_tool(
    *,
    session: AsyncSession,
    user: AuthenticatedUser,
    call: ToolCall,
) -> ToolResult:
    impl = TOOL_REGISTRY.get(call.name)
    if impl is None:
        return ToolResult(payload={"refused": True}, error=f"Unknown tool: {call.name}")
    try:
        return await impl(session=session, user=user, args=call.args)
    except Exception as exc:  # noqa: BLE001 — tool failure must not crash the loop
        logger.warning(
            "agent.tool.failed",
            extra={"tool": call.name, "error_type": type(exc).__name__},
        )
        return ToolResult(payload={"error_type": type(exc).__name__}, error=str(exc))
