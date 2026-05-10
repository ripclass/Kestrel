"""Pure-helper coverage for the billing service (V2 phase 6.2)."""
from __future__ import annotations

from app.services.billing import (
    ALL_FEATURES,
    PLANS,
    Plan,
    all_plans,
    get_plan,
    has_feature,
    plan_summary,
)


def test_four_plans_are_defined() -> None:
    # Three commercial tiers (starter/professional/enterprise) auto-assigned
    # via signup, plus a display-only `regulator` tier shipped as Tier 04 on
    # /pricing — never auto-assigned, only ever set via superadmin after a
    # national-deployment contract is signed.
    assert set(PLANS) == {"starter", "professional", "enterprise", "regulator"}


def test_starter_plan_excludes_paid_features() -> None:
    starter = get_plan("starter")
    assert starter.plan_id == "starter"
    assert "core" in starter.features
    assert "cross_bank" in starter.features
    assert "realtime" not in starter.features
    assert "sanctions" not in starter.features
    assert "kyc" not in starter.features


def test_professional_plan_includes_paid_features() -> None:
    pro = get_plan("professional")
    assert "realtime" in pro.features
    assert "sanctions" in pro.features
    assert "kyc" in pro.features
    assert "agentic" not in pro.features


def test_enterprise_plan_includes_everything_and_on_prem() -> None:
    ent = get_plan("enterprise")
    assert ent.on_prem_eligible is True
    for feature in ("core", "cross_bank", "realtime", "sanctions", "kyc"):
        assert feature in ent.features


def test_get_plan_falls_back_to_starter_for_unknown() -> None:
    assert get_plan(None).plan_id == "starter"
    assert get_plan("").plan_id == "starter"
    assert get_plan("not-a-plan").plan_id == "starter"


def test_get_plan_is_case_insensitive() -> None:
    assert get_plan("PROFESSIONAL").plan_id == "professional"


# has_feature ---------------------------------------------------------------

def test_has_feature_starter_no_realtime() -> None:
    assert has_feature(get_plan("starter"), "realtime") is False


def test_has_feature_starter_with_override_grants_realtime() -> None:
    assert has_feature(get_plan("starter"), "realtime", overrides={"realtime": True}) is True


def test_has_feature_override_does_not_disable_included_feature() -> None:
    """Overrides cannot disable what the plan grants — protect customers
    from silent feature removal."""
    pro = get_plan("professional")
    # Even if the override says false, professional still has realtime.
    assert has_feature(pro, "realtime", overrides={"realtime": False}) is True


def test_has_feature_enterprise_includes_priority_support() -> None:
    assert has_feature(get_plan("enterprise"), "priority_support") is True


# Plan pricing --------------------------------------------------------------

def test_plan_prices_are_in_bdt_paisa_free_units() -> None:
    """V2 spec: starter Tk 60 lakh, pro Tk 1.5 crore, enterprise Tk 4 crore."""
    assert PLANS["starter"].price_bdt_yearly == 60_00_000
    assert PLANS["professional"].price_bdt_yearly == 1_50_00_000
    assert PLANS["enterprise"].price_bdt_yearly == 4_00_00_000


def test_starter_has_seat_and_transaction_caps() -> None:
    starter = get_plan("starter")
    assert starter.seat_cap == 5
    assert starter.monthly_transaction_cap == 500_000


def test_professional_unlimited_transactions() -> None:
    pro = get_plan("professional")
    assert pro.monthly_transaction_cap is None
    assert pro.seat_cap == 15


# Plan summary serialisation ------------------------------------------------

def test_plan_summary_round_trips_features_to_list() -> None:
    summary = plan_summary(PLANS["enterprise"])
    assert isinstance(summary["features"], list)
    assert "core" in summary["features"]
    assert summary["on_prem_eligible"] is True


def test_all_plans_returns_four_entries() -> None:
    plans = all_plans()
    assert len(plans) == 4
    plan_ids = {p["plan_id"] for p in plans}
    assert plan_ids == {"starter", "professional", "enterprise", "regulator"}


# ALL_FEATURES is the universe of feature flags surfaced in the admin UI.
def test_all_features_includes_every_plan_feature() -> None:
    declared = set(ALL_FEATURES)
    for plan in PLANS.values():
        for feature in plan.features:
            assert feature in declared, f"feature {feature!r} missing from ALL_FEATURES"
