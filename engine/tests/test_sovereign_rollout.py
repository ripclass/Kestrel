"""Pure-helper coverage for V3 phase 5.

Async DB paths (get_effective_config / set_effective_config) need a
real Postgres session; this file pins the deterministic helpers — the
coin-flip RNG semantics, the static-default fallback, the rollback
math, and the promotion-harness gate evaluators.
"""
from __future__ import annotations

import random
from types import SimpleNamespace

import pytest

from app.ai.types import AITaskName
from app.services.sovereign_rollout import (
    EffectiveConfig,
    _static_for,
    coin_flip,
    invalidate_cache,
    list_static_defaults,
)
from app.tasks.sovereign_health_tasks import (
    DEGRADATION_MARGIN,
    MIN_ROWS_PER_PROVIDER,
    ROLLOUT_REDUCTION_STEP,
    compute_provider_correction_rates,
)


# Coin-flip semantics ------------------------------------------------------

def test_coin_flip_zero_pct_never_routes() -> None:
    rng = random.Random(0)
    for _ in range(100):
        assert coin_flip(0, rng=rng) is False


def test_coin_flip_hundred_pct_always_routes() -> None:
    rng = random.Random(0)
    for _ in range(100):
        assert coin_flip(100, rng=rng) is True


def test_coin_flip_clamps_negative_to_zero() -> None:
    assert coin_flip(-5) is False


def test_coin_flip_clamps_above_hundred_to_hundred() -> None:
    assert coin_flip(150) is True


def test_coin_flip_statistical_with_seed() -> None:
    """Deterministic RNG → reproducible split. ~10% rollout should land
    near 100/1000 trials with a fixed seed."""
    rng = random.Random(42)
    hits = sum(coin_flip(10, rng=rng) for _ in range(1000))
    # Bound generously — exact count depends on PRNG sequence but a 10%
    # rollout over 1000 calls should never land at 0 or near 1000.
    assert 50 <= hits <= 200


def test_coin_flip_handles_none_input() -> None:
    """Defensive: a None rollout (which can happen if the DB row is
    missing a value) routes to False, never crashes."""
    assert coin_flip(None) is False  # type: ignore[arg-type]


# Static fallback ---------------------------------------------------------

def test_static_for_returns_known_defaults() -> None:
    config = _static_for(AITaskName.ALERT_EXPLANATION)
    # V3 P2 ships with 1.01 + 0% on every task.
    assert config.threshold == 1.01
    assert config.rollout_pct == 0
    assert config.source == "static"


def test_static_for_clamps_rollout_pct_in_range() -> None:
    """Defence: even if someone mis-edits TASK_ROLLOUT_PCT to 250, the
    static_for helper clamps to 100."""
    from app.ai import thresholds

    original = thresholds.TASK_ROLLOUT_PCT.get(AITaskName.STR_NARRATIVE, 0)
    thresholds.TASK_ROLLOUT_PCT[AITaskName.STR_NARRATIVE] = 250
    try:
        config = _static_for(AITaskName.STR_NARRATIVE)
        assert config.rollout_pct == 100
    finally:
        thresholds.TASK_ROLLOUT_PCT[AITaskName.STR_NARRATIVE] = original


def test_list_static_defaults_covers_every_task() -> None:
    defaults = list_static_defaults()
    declared = {str(t) for t in AITaskName}
    surfaced = {row["task"] for row in defaults}
    assert surfaced == declared


def test_invalidate_cache_resets_state() -> None:
    invalidate_cache()
    # After invalidation the next read hits DB; we don't have one in
    # tests so we just verify the helper is callable + idempotent.
    invalidate_cache()


# Rollback math -----------------------------------------------------------

def _row(provider: str, has_correction: bool) -> SimpleNamespace:
    return SimpleNamespace(
        provider=provider,
        analyst_correction={"x": 1} if has_correction else None,
    )


def test_compute_correction_rates_separates_sovereign_from_baseline() -> None:
    rows = [
        _row("sovereign", True),
        _row("sovereign", False),
        _row("openai", True),
        _row("anthropic", False),
        _row("openai", False),
    ]
    rates = compute_provider_correction_rates(rows)
    assert rates["sovereign"]["samples"] == 2
    assert rates["sovereign"]["corrections"] == 1
    assert rates["sovereign"]["correction_rate"] == 0.5
    assert rates["baseline"]["samples"] == 3
    assert rates["baseline"]["corrections"] == 1
    assert rates["baseline"]["correction_rate"] == round(1 / 3, 4)


def test_compute_correction_rates_empty_input() -> None:
    rates = compute_provider_correction_rates([])
    assert rates["sovereign"]["samples"] == 0
    assert rates["sovereign"]["correction_rate"] is None
    assert rates["baseline"]["correction_rate"] is None


def test_compute_correction_rates_collapses_unknown_providers_to_baseline() -> None:
    """The chain may grow over time (GoogleAI, Cohere, etc.). Anything
    that's not exactly 'sovereign' belongs in the baseline bucket so
    the comparison stays meaningful."""
    rows = [_row("future-provider", True), _row("future-provider", False)]
    rates = compute_provider_correction_rates(rows)
    assert rates["baseline"]["samples"] == 2
    assert rates["sovereign"]["samples"] == 0


def test_degradation_constants_are_safe_defaults() -> None:
    """Pin the V3 P5 spec: 15% margin, 25-step reduction, 30 minimum
    samples per provider before reacting."""
    assert DEGRADATION_MARGIN == 0.15
    assert ROLLOUT_REDUCTION_STEP == 25
    assert MIN_ROWS_PER_PROVIDER == 30


# EffectiveConfig --------------------------------------------------------

def test_effective_config_dataclass_defaults() -> None:
    cfg = EffectiveConfig(
        task=AITaskName.ALERT_EXPLANATION,
        threshold=0.75,
        rollout_pct=10,
        source="db",
    )
    assert cfg.updated_at is None
    assert cfg.reason is None


def test_effective_config_is_frozen() -> None:
    cfg = EffectiveConfig(
        task=AITaskName.ALERT_EXPLANATION,
        threshold=1.01,
        rollout_pct=0,
        source="static",
    )
    with pytest.raises(Exception):
        cfg.threshold = 0.5  # type: ignore[misc]
