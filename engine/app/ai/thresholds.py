"""Per-task confidence thresholds (V3 phase 2.3).

The sovereign-first / Claude-fallback routing pattern in
``app.ai.service.AIOrchestrator.invoke`` consults this registry to
decide whether a provider response is "good enough" to return, or
whether the orchestrator should fall through to the next route in the
chain.

In V3 phase 2 every threshold defaults to ``1.01`` — slightly above
the 0–1 confidence range — so no real provider response can ever clear
it. The chain continues to the next route as it did pre-V3, which means
behaviour is unchanged. The pattern is in place; the conditional just
doesn't fire.

When V3 phase 4 ships the first sovereign adapter, ops lower the
threshold for the tasks where the sovereign model has cleared its
quality gates (typically alert_explanation first at 0.75, then
str_narrative at 0.85, etc., per the V3 prompt's task 2.3 example).
The registry is the single edit point — no orchestrator changes.

The bottom of the chain (heuristic provider, or the only configured
provider) is always accepted regardless of threshold to avoid total
failure when no provider clears the bar.
"""
from __future__ import annotations

from app.ai.types import AITaskName

# Effective infinity. Real confidences are 0–1, so this is unreachable.
_INF = 1.01


# Per-task thresholds. Adjust per task as the sovereign model proves
# itself in production traffic; lower numbers = more sovereign traffic.
TASK_CONFIDENCE_THRESHOLDS: dict[AITaskName, float] = {
    AITaskName.ALERT_EXPLANATION: _INF,
    AITaskName.STR_NARRATIVE: _INF,
    AITaskName.ENTITY_EXTRACTION: _INF,
    AITaskName.EXECUTIVE_BRIEFING: _INF,
    AITaskName.TYPOLOGY_SUGGESTION: _INF,
    AITaskName.CASE_SUMMARY: _INF,
    AITaskName.INVESTIGATION_AGENT_HOP: _INF,
}

# Per-task gradual rollout %. 0 = no sovereign traffic for this task even
# if the threshold is satisfied (kill switch). 100 = every call to this
# task tries sovereign first. Used by V3 phase 5's gradual-rollout
# traffic-split logic; harmless until then because no sovereign route
# is registered.
TASK_ROLLOUT_PCT: dict[AITaskName, int] = {
    AITaskName.ALERT_EXPLANATION: 0,
    AITaskName.STR_NARRATIVE: 0,
    AITaskName.ENTITY_EXTRACTION: 0,
    AITaskName.EXECUTIVE_BRIEFING: 0,
    AITaskName.TYPOLOGY_SUGGESTION: 0,
    AITaskName.CASE_SUMMARY: 0,
    AITaskName.INVESTIGATION_AGENT_HOP: 0,
}


def threshold_for(task: AITaskName, default: float = _INF) -> float:
    """Return the minimum confidence required for the orchestrator to
    accept a provider response on ``task``. Falls back to the global
    default when the task is unknown."""
    return TASK_CONFIDENCE_THRESHOLDS.get(task, default)


def rollout_pct_for(task: AITaskName) -> int:
    """Return the per-task sovereign rollout % (0–100). 0 means
    sovereign is never tried even if registered."""
    return max(0, min(100, TASK_ROLLOUT_PCT.get(task, 0)))


def is_sovereign_eligible(task: AITaskName) -> bool:
    """Convenience: rollout > 0. Used by ``resolve_task_routes`` to
    decide whether to prepend the sovereign route at all for this call.
    The 1.01 default threshold means even if sovereign IS prepended, its
    response can't clear the bar today — but the gating happens in two
    places (rollout + threshold) so flipping either to a real value
    unlocks the path."""
    return rollout_pct_for(task) > 0
