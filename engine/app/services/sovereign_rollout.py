"""Runtime rollout config (V3 phase 5.2).

The static defaults in ``app.ai.thresholds`` are baked into the build.
This service overlays a DB-backed override so the V3 P5 rollback Beat
task can shrink a task's rollout without a redeploy.

Read path is hot — every AI call hits ``effective_config`` indirectly
via the routing layer — so we cache for 60 seconds in process. Cache
invalidates on any write (``set_effective_config``) and re-reads from
Postgres.

Resolution order for ``effective_config``:

  1. DB row in ``sovereign_rollout`` keyed on ``task_name``
  2. Static default from ``thresholds.TASK_CONFIDENCE_THRESHOLDS`` /
     ``TASK_ROLLOUT_PCT``
  3. Hard fallback (1.01 + 0%)

Anywhere that needs the runtime values should call this module rather
than reading the static dicts directly.
"""
from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.thresholds import (
    TASK_CONFIDENCE_THRESHOLDS,
    TASK_ROLLOUT_PCT,
)
from app.ai.types import AITaskName
from app.database import SessionLocal
from app.models.sovereign import SovereignRollout

logger = logging.getLogger("kestrel.sovereign.rollout")

_CACHE_TTL_SECONDS = 60.0


@dataclass(slots=True, frozen=True)
class EffectiveConfig:
    task: AITaskName
    threshold: float
    rollout_pct: int
    source: str  # "db" | "static" | "fallback"
    updated_at: datetime | None = None
    reason: str | None = None


class _Cache:
    def __init__(self) -> None:
        self._values: dict[str, EffectiveConfig] = {}
        self._loaded_at: float = 0.0
        self._lock = asyncio.Lock()

    def is_stale(self) -> bool:
        return (time.monotonic() - self._loaded_at) >= _CACHE_TTL_SECONDS

    def invalidate(self) -> None:
        self._values = {}
        self._loaded_at = 0.0

    def replace(self, values: dict[str, EffectiveConfig]) -> None:
        self._values = values
        self._loaded_at = time.monotonic()

    def get(self, task: AITaskName) -> EffectiveConfig | None:
        return self._values.get(str(task))


_cache = _Cache()


def _static_for(task: AITaskName) -> EffectiveConfig:
    threshold = TASK_CONFIDENCE_THRESHOLDS.get(task, 1.01)
    rollout = max(0, min(100, TASK_ROLLOUT_PCT.get(task, 0)))
    return EffectiveConfig(
        task=task,
        threshold=float(threshold),
        rollout_pct=int(rollout),
        source="static",
    )


async def _load_from_db() -> dict[str, EffectiveConfig]:
    out: dict[str, EffectiveConfig] = {}
    try:
        async with SessionLocal() as session:
            rows = (await session.execute(select(SovereignRollout))).scalars().all()
    except Exception as exc:  # noqa: BLE001 — defensive: never let routing crash
        logger.warning(
            "sovereign.rollout.load_failed",
            extra={"error_type": type(exc).__name__},
        )
        return {}
    for row in rows:
        try:
            task = AITaskName(row.task_name)
        except ValueError:
            # Stale row for a removed task; ignore.
            continue
        out[str(task)] = EffectiveConfig(
            task=task,
            threshold=float(row.threshold) if row.threshold is not None else 1.01,
            rollout_pct=int(row.rollout_pct or 0),
            source="db",
            updated_at=row.updated_at,
            reason=row.reason,
        )
    return out


async def get_effective_config(task: AITaskName) -> EffectiveConfig:
    """Return the live (threshold, rollout_pct) pair for ``task``.

    DB row wins; static default is the fallback. Cached for 60 seconds.
    Safe to call in a hot path — single async DB lookup amortised over
    every call within the TTL window."""
    if _cache.is_stale():
        async with _cache._lock:
            if _cache.is_stale():
                _cache.replace(await _load_from_db())

    cached = _cache.get(task)
    if cached is not None:
        return cached
    return _static_for(task)


async def effective_threshold_for(task: AITaskName) -> float:
    return (await get_effective_config(task)).threshold


async def effective_rollout_pct_for(task: AITaskName) -> int:
    return (await get_effective_config(task)).rollout_pct


async def set_effective_config(
    *,
    task: AITaskName,
    threshold: float | None = None,
    rollout_pct: int | None = None,
    reason: str | None = None,
    updated_by: str | None = None,
) -> EffectiveConfig:
    """Upsert the runtime override for ``task``. Invalidates the cache.

    When called with only one of ``threshold`` or ``rollout_pct``, the
    other field defaults to the current value (DB or static)."""
    current = await get_effective_config(task)
    new_threshold = float(threshold if threshold is not None else current.threshold)
    new_rollout = int(rollout_pct if rollout_pct is not None else current.rollout_pct)
    new_rollout = max(0, min(100, new_rollout))

    payload = {
        "task_name": str(task),
        "threshold": new_threshold,
        "rollout_pct": new_rollout,
        "reason": reason,
        "updated_by": updated_by,
        "updated_at": datetime.now(UTC),
    }
    async with SessionLocal() as session:
        async with session.begin():
            stmt = (
                pg_insert(SovereignRollout.__table__)
                .values(payload)
                .on_conflict_do_update(
                    index_elements=["task_name"],
                    set_={
                        "threshold": new_threshold,
                        "rollout_pct": new_rollout,
                        "reason": reason,
                        "updated_by": updated_by,
                        "updated_at": datetime.now(UTC),
                    },
                )
            )
            await session.execute(stmt)
    _cache.invalidate()
    logger.info(
        "sovereign.rollout.updated",
        extra={
            "task": str(task),
            "threshold": new_threshold,
            "rollout_pct": new_rollout,
            "updated_by": updated_by,
            "reason": reason,
        },
    )
    return EffectiveConfig(
        task=task,
        threshold=new_threshold,
        rollout_pct=new_rollout,
        source="db",
        updated_at=datetime.now(UTC),
        reason=reason,
    )


def invalidate_cache() -> None:
    """Test hook — drops the in-process cache so the next read hits DB."""
    _cache.invalidate()


def coin_flip(rollout_pct: int, *, rng=None) -> bool:
    """Return True when the call should route via sovereign.

    Per V3 P5.2: 10% rollout means ~10% of calls. We use a uniform
    [0, 100) draw so the rollout is statistical, not deterministic."""
    import random

    rollout_pct = max(0, min(100, int(rollout_pct or 0)))
    if rollout_pct <= 0:
        return False
    if rollout_pct >= 100:
        return True
    rng = rng or random
    return rng.random() * 100.0 < float(rollout_pct)


def list_static_defaults() -> list[dict[str, Any]]:
    """Return the static defaults so the admin UI can show what's
    baked in vs what's overridden in the DB."""
    return [
        {
            "task": str(task),
            "default_threshold": float(TASK_CONFIDENCE_THRESHOLDS.get(task, 1.01)),
            "default_rollout_pct": int(TASK_ROLLOUT_PCT.get(task, 0)),
        }
        for task in AITaskName
    ]
