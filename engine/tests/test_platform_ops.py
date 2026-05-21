"""Pure-helper coverage for the platform-operator console.

The async aggregation paths (build_pilot_overview / build_pilot_detail)
need a real Postgres session — they fan out across organizations,
profiles, audit_log and the domain tables. This file pins the
deterministic helpers: engagement bucketing, week-over-week trend,
None-safe recency, the card assembler, and the operator allow-list gate.
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

from app.config import Settings
from app.services.platform_ops import (
    _build_card,
    activity_trend,
    engagement_status,
    latest,
    tenant_kind_of,
)

NOW = datetime(2026, 5, 21, 12, 0, 0, tzinfo=UTC)


# --- engagement_status -------------------------------------------------------

def test_engagement_never_when_no_contact() -> None:
    assert engagement_status(None, NOW) == "never"


def test_engagement_active_within_three_days() -> None:
    assert engagement_status(NOW - timedelta(days=2), NOW) == "active"


def test_engagement_active_at_three_day_boundary() -> None:
    assert engagement_status(NOW - timedelta(days=3), NOW) == "active"


def test_engagement_idle_between_three_and_fourteen_days() -> None:
    assert engagement_status(NOW - timedelta(days=10), NOW) == "idle"


def test_engagement_idle_at_fourteen_day_boundary() -> None:
    assert engagement_status(NOW - timedelta(days=14), NOW) == "idle"


def test_engagement_dormant_beyond_fourteen_days() -> None:
    assert engagement_status(NOW - timedelta(days=30), NOW) == "dormant"


def test_engagement_future_timestamp_reads_active() -> None:
    """Clock skew shouldn't bucket a tenant as dormant."""
    assert engagement_status(NOW + timedelta(hours=2), NOW) == "active"


# --- activity_trend ----------------------------------------------------------

def test_trend_new_when_no_prior_baseline_but_active() -> None:
    assert activity_trend(current=12, previous=0) == "new"


def test_trend_flat_when_no_baseline_and_no_activity() -> None:
    assert activity_trend(current=0, previous=0) == "flat"


def test_trend_rising_above_fifteen_percent() -> None:
    assert activity_trend(current=120, previous=100) == "rising"


def test_trend_falling_below_minus_fifteen_percent() -> None:
    assert activity_trend(current=80, previous=100) == "falling"


def test_trend_flat_within_noise_band() -> None:
    assert activity_trend(current=105, previous=100) == "flat"
    assert activity_trend(current=90, previous=100) == "flat"


def test_trend_boundary_exactly_fifteen_percent_is_rising() -> None:
    assert activity_trend(current=115, previous=100) == "rising"


# --- latest ------------------------------------------------------------------

def test_latest_returns_none_for_all_none() -> None:
    assert latest(None, None) is None


def test_latest_ignores_none_and_picks_most_recent() -> None:
    older = NOW - timedelta(days=5)
    newer = NOW - timedelta(days=1)
    assert latest(older, None, newer) == newer


def test_latest_single_value() -> None:
    assert latest(NOW) == NOW


# --- _build_card -------------------------------------------------------------

def _org() -> SimpleNamespace:
    return SimpleNamespace(
        id="9c222222-0000-0000-0000-000000000000",
        name="Sonali Bank PLC",
        org_type="bank",
        plan_id="professional",
        created_at=NOW - timedelta(days=40),
    )


def test_build_card_engagement_uses_most_recent_signal() -> None:
    """Login is stale but an audit action is recent → active."""
    card = _build_card(
        _org(),
        now=NOW,
        seats=5,
        logins=[NOW - timedelta(days=20)],
        activity={
            "actions_7d": 30,
            "actions_prev_7d": 10,
            "actions_30d": 90,
            "last_activity_at": NOW - timedelta(days=1),
            "active_users_7d": 3,
        },
        strs=4,
        alerts=12,
        cases=2,
        scans=1,
    )
    assert card["engagement"] == "active"
    assert card["trend"] == "rising"
    assert card["seats_logged_in"] == 1
    assert card["org_id"] == "9c222222-0000-0000-0000-000000000000"


def test_build_card_never_engaged_tenant() -> None:
    card = _build_card(
        _org(),
        now=NOW,
        seats=5,
        logins=[None, None],
        activity={},
        strs=0,
        alerts=0,
        cases=0,
        scans=0,
    )
    assert card["engagement"] == "never"
    assert card["seats_logged_in"] == 0
    assert card["last_login_at"] is None
    assert card["last_activity_at"] is None
    assert card["trend"] == "flat"
    assert card["actions_7d"] == 0


def test_build_card_dormant_when_only_old_login() -> None:
    card = _build_card(
        _org(),
        now=NOW,
        seats=3,
        logins=[NOW - timedelta(days=25)],
        activity={},
        strs=0,
        alerts=0,
        cases=0,
        scans=0,
    )
    assert card["engagement"] == "dormant"
    assert card["seats_logged_in"] == 1


def test_build_card_defaults_missing_plan_to_starter() -> None:
    org = _org()
    org.plan_id = None
    card = _build_card(
        org, now=NOW, seats=0, logins=[], activity={},
        strs=0, alerts=0, cases=0, scans=0,
    )
    assert card["plan_id"] == "starter"


# --- operator allow-list gate ------------------------------------------------

def test_operator_emails_parsed_and_normalised() -> None:
    s = Settings(kestrel_platform_operators=" Founder@Enso.com , ops@enso.com ")
    assert s.platform_operator_emails() == {"founder@enso.com", "ops@enso.com"}


def test_is_platform_operator_match_is_case_insensitive() -> None:
    s = Settings(kestrel_platform_operators="founder@enso.com")
    assert s.is_platform_operator("FOUNDER@enso.com") is True


def test_is_platform_operator_rejects_non_member() -> None:
    s = Settings(kestrel_platform_operators="founder@enso.com")
    assert s.is_platform_operator("camlco@sonali.example") is False


def test_is_platform_operator_fail_closed_when_list_empty() -> None:
    s = Settings(kestrel_platform_operators="")
    assert s.is_platform_operator("founder@enso.com") is False


def test_is_platform_operator_handles_none_email() -> None:
    s = Settings(kestrel_platform_operators="founder@enso.com")
    assert s.is_platform_operator(None) is False


# --- operator role resolution ------------------------------------------------

def test_operator_role_none_for_non_operator() -> None:
    s = Settings(kestrel_platform_operators="ops@enso.com")
    assert s.platform_operator_role("stranger@bank.com") is None


def test_operator_role_defaults_to_owner_without_map() -> None:
    s = Settings(kestrel_platform_operators="ops@enso.com")
    assert s.platform_operator_role("ops@enso.com") == "owner"


def test_operator_role_uses_explicit_map() -> None:
    s = Settings(
        kestrel_platform_operators="ops@enso.com,cs@enso.com",
        kestrel_platform_operator_roles='{"cs@enso.com": "operations"}',
    )
    assert s.platform_operator_role("cs@enso.com") == "operations"


def test_operator_role_unmapped_operator_falls_back_to_owner() -> None:
    s = Settings(
        kestrel_platform_operators="ops@enso.com,cs@enso.com",
        kestrel_platform_operator_roles='{"cs@enso.com": "operations"}',
    )
    assert s.platform_operator_role("ops@enso.com") == "owner"


def test_operator_role_malformed_json_fails_safe_to_owner() -> None:
    """A broken role map must never lock the founder out."""
    s = Settings(
        kestrel_platform_operators="ops@enso.com",
        kestrel_platform_operator_roles="{not valid json",
    )
    assert s.platform_operator_role("ops@enso.com") == "owner"


def test_operator_role_match_is_case_insensitive() -> None:
    s = Settings(
        kestrel_platform_operators="cs@enso.com",
        kestrel_platform_operator_roles='{"cs@enso.com": "operations"}',
    )
    assert s.platform_operator_role("CS@Enso.com") == "operations"


# --- tenant_kind_of ----------------------------------------------------------

def test_tenant_kind_reads_pilot() -> None:
    org = SimpleNamespace(settings={"tenant_kind": "pilot"})
    assert tenant_kind_of(org) == "pilot"


def test_tenant_kind_defaults_to_demo_when_unset() -> None:
    assert tenant_kind_of(SimpleNamespace(settings={})) == "demo"
    assert tenant_kind_of(SimpleNamespace(settings=None)) == "demo"


def test_tenant_kind_defaults_to_demo_for_invalid_value() -> None:
    """An unclassified or junk value must never read as a real pilot."""
    org = SimpleNamespace(settings={"tenant_kind": "production"})
    assert tenant_kind_of(org) == "demo"


def test_tenant_kind_live_is_honored() -> None:
    org = SimpleNamespace(settings={"tenant_kind": "live"})
    assert tenant_kind_of(org) == "live"
