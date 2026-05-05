"""AI outcome log surface (V3 phase 1.3).

Three reads + two writes:

  build_outcome_dashboard      — aggregated stats for /admin/ai-outcomes
  list_recent_outcomes         — recent rows for the dashboard's
                                 "most-recently-corrected" stream
  list_corrected_outcomes      — corpus preview for V3 phase 4
  record_correction            — analyst editing the AI-drafted output
  record_outcome_label         — analyst marking the AI right/wrong

The actual update path lives in ``app.ai.audit.record_outcome_correction``;
this service is the read-side aggregator + a thin convenience wrapper.
"""
from __future__ import annotations

import logging
import uuid
from collections import defaultdict
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.audit import record_outcome_correction
from app.auth import AuthenticatedUser
from app.models.ai_outcome import AIOutcomeLog

logger = logging.getLogger("kestrel.ai.outcome")


def _now() -> datetime:
    return datetime.now(UTC)


def _is_regulator(user: AuthenticatedUser) -> bool:
    return (user.org_type or "").lower() == "regulator"


def _outcome_to_view(row: AIOutcomeLog) -> dict[str, Any]:
    return {
        "id": str(row.id),
        "task_name": row.task_name,
        "provider": row.provider,
        "model": row.model,
        "confidence": float(row.confidence) if row.confidence is not None else None,
        "outcome_label": row.outcome_label,
        "has_correction": row.analyst_correction is not None,
        "latency_ms": row.latency_ms,
        "prompt_tokens": row.prompt_tokens,
        "completion_tokens": row.completion_tokens,
        "fallback_from_provider": row.fallback_from_provider,
        "request_id": row.request_id,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
    }


async def build_outcome_dashboard(
    session: AsyncSession,
    *,
    user: AuthenticatedUser,
    window_days: int = 30,
) -> dict[str, Any]:
    """Per-task correction-rate, provider distribution, latency, top-50
    most-recently-corrected. Bank persona sees own-org; regulator sees
    aggregate."""
    window = max(1, min(int(window_days or 30), 90))
    window_start = _now() - timedelta(days=window)

    base_filters = [AIOutcomeLog.created_at >= window_start]
    if not _is_regulator(user):
        try:
            org_uuid = uuid.UUID(str(user.org_id))
        except (TypeError, ValueError):
            return _empty_dashboard(window)
        base_filters.append(AIOutcomeLog.org_id == org_uuid)

    # Per-task counters: total + corrections + average latency.
    task_stmt = (
        select(
            AIOutcomeLog.task_name,
            func.count().label("total"),
            func.count(AIOutcomeLog.analyst_correction).label("corrections"),
            func.avg(AIOutcomeLog.latency_ms).label("avg_latency"),
        )
        .where(*base_filters)
        .group_by(AIOutcomeLog.task_name)
    )
    task_rows = (await session.execute(task_stmt)).all()
    by_task = [
        {
            "task_name": row[0] or "unknown",
            "total": int(row[1] or 0),
            "corrections": int(row[2] or 0),
            "correction_rate": (
                round(int(row[2] or 0) / int(row[1] or 1), 4) if int(row[1] or 0) else 0.0
            ),
            "avg_latency_ms": int(round(float(row[3] or 0))),
        }
        for row in task_rows
    ]

    # Provider distribution.
    provider_stmt = (
        select(AIOutcomeLog.provider, func.count())
        .where(*base_filters)
        .group_by(AIOutcomeLog.provider)
    )
    by_provider = [
        {"provider": row[0] or "unknown", "count": int(row[1] or 0)}
        for row in (await session.execute(provider_stmt)).all()
    ]

    # Outcome-label distribution.
    label_stmt = (
        select(AIOutcomeLog.outcome_label, func.count())
        .where(*base_filters)
        .where(AIOutcomeLog.outcome_label.is_not(None))
        .group_by(AIOutcomeLog.outcome_label)
    )
    by_label: dict[str, int] = defaultdict(int)
    for row in (await session.execute(label_stmt)).all():
        by_label[row[0] or "unknown"] = int(row[1] or 0)

    # Top scalar — total invocations + total corrections.
    total = sum(t["total"] for t in by_task)
    corrections = sum(t["corrections"] for t in by_task)
    correction_rate = round(corrections / total, 4) if total else 0.0

    return {
        "window_days": window,
        "total_invocations": total,
        "total_corrections": corrections,
        "correction_rate": correction_rate,
        "by_task": by_task,
        "by_provider": by_provider,
        "outcome_labels": dict(by_label),
        "persona_view": "regulator" if _is_regulator(user) else "bank",
        "generated_at": _now().isoformat(),
    }


def _empty_dashboard(window: int) -> dict[str, Any]:
    return {
        "window_days": window,
        "total_invocations": 0,
        "total_corrections": 0,
        "correction_rate": 0.0,
        "by_task": [],
        "by_provider": [],
        "outcome_labels": {},
        "persona_view": "bank",
        "generated_at": _now().isoformat(),
    }


async def list_recent_outcomes(
    session: AsyncSession,
    *,
    user: AuthenticatedUser,
    limit: int = 50,
    only_corrected: bool = False,
) -> list[dict[str, Any]]:
    capped = max(1, min(int(limit or 50), 200))
    stmt = select(AIOutcomeLog).order_by(desc(AIOutcomeLog.created_at)).limit(capped)
    if not _is_regulator(user):
        try:
            org_uuid = uuid.UUID(str(user.org_id))
        except (TypeError, ValueError):
            return []
        stmt = stmt.where(AIOutcomeLog.org_id == org_uuid)
    if only_corrected:
        stmt = stmt.where(AIOutcomeLog.analyst_correction.is_not(None))
    result = await session.execute(stmt)
    return [_outcome_to_view(row) for row in result.scalars().all()]


async def record_correction(
    *,
    log_id: uuid.UUID,
    user: AuthenticatedUser,
    correction: dict[str, Any] | None,
    outcome_label: str | None,
) -> bool:
    """Thin wrapper around ``audit.record_outcome_correction`` for the
    router. Kept here so the V3 sovereign-AI training surface has a
    single import target as it grows."""
    return await record_outcome_correction(
        log_id=log_id,
        user=user,
        correction=correction,
        outcome_label=outcome_label,
    )
