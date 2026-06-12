"""Safety-gate coverage for watchlist delisting reconciliation.

The reconciliation SQL needs a real DB, but the load-bearing safety decision
(do NOT mass-remove off a truncated/failed feed) is a pure function. These
pin it — a regression here could silently wipe real sanctions entries when an
upstream download comes back short.
"""
from __future__ import annotations

from app.tasks.screening_tasks import _RECONCILE_MIN_RATIO, _should_reconcile


def test_empty_feed_never_reconciles() -> None:
    # A source that parsed zero rows (fetch/parse failure) must not remove anything.
    assert _should_reconcile(parsed_count=0, existing_active_live=19000) is False


def test_first_load_reconciles_as_noop() -> None:
    # Nothing active yet → reconciliation is a harmless no-op.
    assert _should_reconcile(parsed_count=19000, existing_active_live=0) is True


def test_full_size_feed_reconciles() -> None:
    assert _should_reconcile(parsed_count=19000, existing_active_live=19135) is True


def test_slightly_smaller_feed_above_floor_reconciles() -> None:
    # 60 >= 50% of 100 → ok.
    assert _should_reconcile(parsed_count=60, existing_active_live=100) is True


def test_truncated_feed_below_floor_is_blocked() -> None:
    # 40 < 50% of 100 → suspicious shrink → block reconciliation.
    assert _should_reconcile(parsed_count=40, existing_active_live=100) is False


def test_half_size_ofac_feed_blocked() -> None:
    # A real-world disaster shape: OFAC normally ~19k, feed came back ~5k.
    assert _should_reconcile(parsed_count=5000, existing_active_live=19135) is False


def test_ratio_is_one_half() -> None:
    assert _RECONCILE_MIN_RATIO == 0.5


def test_exactly_at_floor_reconciles() -> None:
    assert _should_reconcile(parsed_count=50, existing_active_live=100) is True
