"""V3 P7.4 — latency regression CI gate.

Times a 100-call synthetic burst against the pure-scoring composition
helpers (amount-band + channel + decide + confidence). The full
``score_transaction`` path includes DB reads against the shared
entities/matches tables that aren't in scope here — the goal is to
catch a regression in the deterministic CPU portion of the scorer
before it ships, not to model the production p99 (which the live
``/score/metrics`` endpoint already tracks).

p99 budget on the pure helpers: 5 ms. The CI workflow runs this test
in isolation; a regression that pushes p99 over budget fails the build.

Why pure helpers, not the full ``score_transaction``: making the full
path latency-tested in CI would need a Postgres dependency in the
runner. The pure-helper budget catches accidental O(n^2) regressions or
expensive-import regressions in the scorer composition; the live
metrics endpoint catches actual production regressions and is observed
by the operator.
"""
from __future__ import annotations

import time
from typing import Any

from app.services.realtime_scoring import (
    _confidence_from_signals,
    _decide,
    _score_amount,
    _score_channel,
)

BURST = 100
P99_BUDGET_MS = 5.0


def _synthetic_call() -> tuple[int, str, float]:
    """One pure-helper composition. Mirrors the in-memory shape of a
    real ``score_transaction`` call without the DB lookups."""
    reasons: list[dict[str, Any]] = []
    evidence: dict[str, Any] = {}
    amount = 1_500_000.0  # large band — drives a 20-point contribution
    channel = "MFS_BKASH"
    score = 0
    score += _score_amount(amount, reasons, evidence)
    score += _score_channel(channel, reasons, evidence)
    score = max(0, min(100, score))
    decision = _decide(score)
    confidence = _confidence_from_signals(reasons)
    return score, decision, confidence


def _percentile(values: list[float], pct: float) -> float:
    if not values:
        return 0.0
    sorted_values = sorted(values)
    rank = int(round((pct / 100.0) * (len(sorted_values) - 1)))
    return sorted_values[rank]


def test_pure_helper_burst_meets_p99_budget() -> None:
    """100 calls, p99 in milliseconds must stay under the budget.

    A regression here is the canary for "someone added an expensive
    import or a hidden O(n^2) loop in the scorer composition"."""
    durations_ms: list[float] = []
    for _ in range(BURST):
        t0 = time.perf_counter()
        score, decision, confidence = _synthetic_call()
        durations_ms.append((time.perf_counter() - t0) * 1000.0)
        # Sanity: the composition must always produce a usable shape.
        assert 0 <= score <= 100
        assert decision in ("approve", "review", "hold", "reject")
        assert 0.0 <= confidence <= 0.95

    p50 = _percentile(durations_ms, 50)
    p99 = _percentile(durations_ms, 99)
    assert p99 <= P99_BUDGET_MS, (
        f"pure-helper burst p99 {p99:.3f}ms exceeded budget {P99_BUDGET_MS}ms "
        f"(p50={p50:.3f}ms). Likely regression in the scorer composition."
    )


def test_synthetic_call_is_deterministic() -> None:
    """Same inputs → same score / decision / confidence. If this drifts,
    the latency test result becomes non-comparable across runs."""
    a = _synthetic_call()
    b = _synthetic_call()
    assert a == b


def test_decide_band_thresholds_are_stable() -> None:
    """Pin the decision bands; a regression that shifts these breaks
    every customer's integration."""
    assert _decide(0) == "approve"
    assert _decide(29) == "approve"
    assert _decide(30) == "review"
    assert _decide(59) == "review"
    assert _decide(60) == "hold"
    assert _decide(79) == "hold"
    assert _decide(80) == "reject"
    assert _decide(100) == "reject"
