"""V3 P7.2 — monthly metered-write helpers."""
from __future__ import annotations

from datetime import UTC, date, datetime, timezone

from app.services.metering import (
    DHAKA_OFFSET,
    CapStatus,
    _compute_cap_status,
    current_period_start,
)


def test_period_start_uses_dhaka_calendar() -> None:
    # Dhaka is UTC+6; UTC 2026-05-31 19:30 is Dhaka 2026-06-01 01:30.
    on_boundary_utc = datetime(2026, 5, 31, 19, 30, tzinfo=UTC)
    assert current_period_start(on_boundary_utc) == date(2026, 6, 1)


def test_period_start_at_mid_month() -> None:
    mid = datetime(2026, 5, 15, 10, 0, tzinfo=UTC)
    assert current_period_start(mid) == date(2026, 5, 1)


def test_period_start_promotes_naive_datetime_to_utc() -> None:
    naive = datetime(2026, 5, 15, 10, 0)
    assert current_period_start(naive) == date(2026, 5, 1)


def test_period_start_january_first_dhaka() -> None:
    # UTC 2025-12-31 18:30 = Dhaka 2026-01-01 00:30.
    boundary = datetime(2025, 12, 31, 18, 30, tzinfo=UTC)
    assert current_period_start(boundary) == date(2026, 1, 1)


def test_dhaka_offset_is_six_hours() -> None:
    assert DHAKA_OFFSET.total_seconds() == 6 * 3600
    # Explicit cross-check that the helper is using the same offset.
    now = datetime(2026, 5, 15, 10, 0, tzinfo=UTC)
    expected = now.astimezone(timezone(DHAKA_OFFSET))
    assert expected.hour == 16


def test_cap_status_with_no_cap_is_unbounded() -> None:
    status = _compute_cap_status(plan_id="professional", cap=None, used=10_000)
    assert status.cap is None
    assert status.remaining is None
    assert status.over_cap is False


def test_cap_status_under_cap() -> None:
    status = _compute_cap_status(plan_id="starter", cap=500_000, used=100_000)
    assert status.cap == 500_000
    assert status.remaining == 400_000
    assert status.over_cap is False


def test_cap_status_at_cap_is_over() -> None:
    """At-cap is considered over-cap so the tenant gets 402 BEFORE the
    increment runs (i.e. the cap value is the maximum count, not the
    minimum-rejected count)."""
    status = _compute_cap_status(plan_id="starter", cap=500_000, used=500_000)
    assert status.over_cap is True
    assert status.remaining == 0


def test_cap_status_above_cap() -> None:
    status = _compute_cap_status(plan_id="starter", cap=500_000, used=500_001)
    assert status.over_cap is True
    assert status.remaining == 0


def test_cap_status_summary_shape() -> None:
    status = CapStatus(
        plan_id="starter", cap=500_000, used=12_345, remaining=487_655, over_cap=False
    )
    summary = status.to_summary()
    assert summary == {
        "plan_id": "starter",
        "monthly_transaction_cap": 500_000,
        "used": 12_345,
        "remaining": 487_655,
        "over_cap": False,
    }
