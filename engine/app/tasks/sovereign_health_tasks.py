"""Sovereign health-check + rollback (V3 phase 5.3).

Every 30 minutes, scan the last N rows of ``ai_outcome_log`` per task,
compute correction rate per provider, and shrink the sovereign rollout
% on any task where sovereign trails Claude by more than the configured
margin.

Math:

    correction_rate(provider, task) =
        rows where provider matches AND analyst_correction IS NOT NULL
        / total rows where provider matches

    if correction_rate(sovereign) - correction_rate(claude) > 0.15:
        new_rollout = max(0, current_rollout - 25)
        set_effective_config(task, rollout_pct=new_rollout, reason='health_check')

Page the operator (warning log) when rollout reaches 0.

The check is conservative: needs at least ``MIN_ROWS_PER_PROVIDER``
samples on both sides before reacting, to avoid noise-driven rollback.
"""
from __future__ import annotations

import asyncio
import logging
from collections import defaultdict
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import select

from app.ai.types import AITaskName
from app.database import SessionLocal
from app.models.ai_outcome import AIOutcomeLog
from app.services.sovereign_rollout import (
    effective_rollout_pct_for,
    set_effective_config,
)
from app.tasks.celery_app import celery_app

logger = logging.getLogger("kestrel.tasks.sovereign_health")


SAMPLE_WINDOW_HOURS = 24
SAMPLE_LIMIT = 1000
MIN_ROWS_PER_PROVIDER = 30
DEGRADATION_MARGIN = 0.15
ROLLOUT_REDUCTION_STEP = 25


@celery_app.task(name="app.tasks.sovereign_health_tasks.check")
def check() -> dict[str, Any]:
    """Beat-driven entrypoint."""
    summary = asyncio.run(_run())
    if summary.get("rollbacks_applied", 0) > 0:
        logger.warning("sovereign.health.rollback", extra={"summary": summary})
    elif summary.get("tasks_evaluated", 0) > 0:
        logger.info("sovereign.health.ok", extra={"summary": summary})
    return summary


async def _run() -> dict[str, Any]:
    rows_by_task = await _fetch_recent_rows()
    evaluations: list[dict[str, Any]] = []
    rollbacks = 0
    paged = 0

    for task_name, rows in rows_by_task.items():
        try:
            task = AITaskName(task_name)
        except ValueError:
            continue
        report = compute_provider_correction_rates(rows)
        sovereign_rate = report.get("sovereign", {}).get("correction_rate")
        sovereign_n = report.get("sovereign", {}).get("samples", 0)
        # Aggregate non-sovereign providers as "baseline" — we compare
        # sovereign against the best alternative, which in practice is
        # whichever of OpenAI / Anthropic was serving traffic.
        baseline_rate = report.get("baseline", {}).get("correction_rate")
        baseline_n = report.get("baseline", {}).get("samples", 0)

        evaluation = {
            "task": str(task),
            "sovereign_samples": sovereign_n,
            "sovereign_correction_rate": sovereign_rate,
            "baseline_samples": baseline_n,
            "baseline_correction_rate": baseline_rate,
            "action": "noop",
        }

        if (
            sovereign_n >= MIN_ROWS_PER_PROVIDER
            and baseline_n >= MIN_ROWS_PER_PROVIDER
            and sovereign_rate is not None
            and baseline_rate is not None
            and (sovereign_rate - baseline_rate) > DEGRADATION_MARGIN
        ):
            current = await effective_rollout_pct_for(task)
            new_rollout = max(0, current - ROLLOUT_REDUCTION_STEP)
            await set_effective_config(
                task=task,
                rollout_pct=new_rollout,
                reason=(
                    f"health_check: sovereign correction_rate {sovereign_rate:.2f} "
                    f"vs baseline {baseline_rate:.2f} (margin {sovereign_rate - baseline_rate:.2f})"
                ),
                updated_by="sovereign_health_check",
            )
            evaluation["action"] = "rolled_back"
            evaluation["rollout_before"] = current
            evaluation["rollout_after"] = new_rollout
            rollbacks += 1
            if new_rollout == 0:
                paged += 1
                logger.warning(
                    "sovereign.health.paged_operator",
                    extra={
                        "task": str(task),
                        "sovereign_correction_rate": sovereign_rate,
                        "baseline_correction_rate": baseline_rate,
                    },
                )
        evaluations.append(evaluation)

    return {
        "ran_at": datetime.now(UTC).isoformat(),
        "tasks_evaluated": len(evaluations),
        "rollbacks_applied": rollbacks,
        "operator_pages": paged,
        "evaluations": evaluations,
    }


async def _fetch_recent_rows() -> dict[str, list[AIOutcomeLog]]:
    cutoff = datetime.now(UTC) - timedelta(hours=SAMPLE_WINDOW_HOURS)
    out: dict[str, list[AIOutcomeLog]] = defaultdict(list)
    async with SessionLocal() as session:
        stmt = (
            select(AIOutcomeLog)
            .where(AIOutcomeLog.created_at >= cutoff)
            .order_by(AIOutcomeLog.created_at.desc())
            .limit(SAMPLE_LIMIT * 8)  # 8 task buckets
        )
        rows = (await session.execute(stmt)).scalars().all()
    for row in rows:
        out[row.task_name].append(row)
    return dict(out)


def compute_provider_correction_rates(rows: list[Any]) -> dict[str, dict[str, Any]]:
    """Return {provider_label: {samples, corrections, correction_rate}}.

    Provider labels collapse the OpenAI / Anthropic / heuristic chain
    into a single ``baseline`` so the sovereign-vs-everything-else
    comparison is meaningful regardless of which fallback handled the
    call. ``sovereign`` stays its own bucket."""
    counts: dict[str, dict[str, int]] = {
        "sovereign": {"samples": 0, "corrections": 0},
        "baseline": {"samples": 0, "corrections": 0},
    }
    for row in rows:
        provider = (getattr(row, "provider", "") or "").lower()
        bucket = "sovereign" if provider == "sovereign" else "baseline"
        counts[bucket]["samples"] += 1
        if getattr(row, "analyst_correction", None) is not None:
            counts[bucket]["corrections"] += 1

    out: dict[str, dict[str, Any]] = {}
    for label, stats in counts.items():
        if stats["samples"] == 0:
            out[label] = {"samples": 0, "corrections": 0, "correction_rate": None}
        else:
            out[label] = {
                "samples": stats["samples"],
                "corrections": stats["corrections"],
                "correction_rate": round(stats["corrections"] / stats["samples"], 4),
            }
    return out
