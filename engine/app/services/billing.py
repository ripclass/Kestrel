"""Pricing tier resolver (V2 phase 6.2).

Three plans defined in code; ``organizations.plan_id`` selects which one.
``organizations.plan_overrides`` lets the regulator grant per-tenant
feature bumps without changing tiers (e.g. a starter-plan bank that
needs realtime scoring during a pilot).

For v1 the plan is set manually by superadmins via the existing
``/admin/team`` surface. Stripe / metered billing is a post-pilot
concern.

Hard transaction-cap enforcement is also a post-pilot concern — for now
the helpers expose plan limits so the dashboard can warn near caps, but
the engine doesn't 402 on a starter tenant that exceeds 500k transactions
in a month. Phase 7 will add the metered-write counter and the 402
response when limits are exceeded.
"""
from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import AuthenticatedUser
from app.models.org import Organization

logger = logging.getLogger("kestrel.billing")


@dataclass(frozen=True, slots=True)
class Plan:
    """Plan definition. Unlimited caps are represented as ``None``.

    ``display_only`` plans (e.g. the regulator tier) are never auto-assigned
    by signup and never carry a public price; they exist in code purely so
    the public ``/pricing`` page can render the matching card with the
    right metadata. A tenant only ever lands on a display-only plan via
    superadmin assignment after a contract is signed.
    """

    plan_id: str
    display_name: str
    price_bdt_yearly: int | None
    seat_cap: int | None
    monthly_transaction_cap: int | None
    features: tuple[str, ...] = field(default_factory=tuple)
    on_prem_eligible: bool = False
    display_only: bool = False


PLANS: dict[str, Plan] = {
    "filing_only": Plan(
        # The "goAML replacement" tier. Banks under BFIU procurement get this
        # at no cost — they file STR / CTR / IER in goAML XML, see their own
        # submission history and inbound RFIs, and nothing else. Cross-bank
        # intelligence, AI, scoring, KYC, sanctions, agentic surfaces all
        # gate via require_feature() and return 402 PAYMENT REQUIRED. Banks
        # who want those features open a separate commercial relationship
        # on starter / professional / enterprise tier.
        plan_id="filing_only",
        display_name="Filing only",
        price_bdt_yearly=0,
        seat_cap=5,
        monthly_transaction_cap=None,
        features=("core",),
    ),
    "starter": Plan(
        plan_id="starter",
        display_name="Starter",
        price_bdt_yearly=60_00_000,  # Tk 60 lakh
        seat_cap=5,
        monthly_transaction_cap=500_000,
        features=("core", "cross_bank"),
    ),
    "professional": Plan(
        plan_id="professional",
        display_name="Professional",
        price_bdt_yearly=1_50_00_000,  # Tk 1.5 crore
        seat_cap=15,
        monthly_transaction_cap=None,
        features=("core", "cross_bank", "realtime", "sanctions", "kyc"),
    ),
    "enterprise": Plan(
        plan_id="enterprise",
        display_name="Enterprise",
        price_bdt_yearly=4_00_00_000,  # Tk 4 crore
        seat_cap=50,
        monthly_transaction_cap=None,
        features=("core", "cross_bank", "realtime", "sanctions", "kyc", "agentic", "priority_support"),
        on_prem_eligible=True,
    ),
    "regulator": Plan(
        plan_id="regulator",
        display_name="Regulator",
        price_bdt_yearly=None,  # quoted bespoke; never published
        seat_cap=None,
        monthly_transaction_cap=None,
        features=("core", "cross_bank", "realtime", "sanctions", "kyc", "agentic", "priority_support"),
        on_prem_eligible=True,
        display_only=True,
    ),
}

# All known features. Used by /admin to render override toggles.
ALL_FEATURES: tuple[str, ...] = (
    "core",
    "cross_bank",
    "realtime",
    "sanctions",
    "kyc",
    "agentic",
    "priority_support",
)


def get_plan(plan_id: str | None) -> Plan:
    """Resolve a plan_id to a Plan, falling back to starter."""
    return PLANS.get((plan_id or "").lower(), PLANS["starter"])


def has_feature(plan: Plan, feature: str, *, overrides: dict[str, Any] | None = None) -> bool:
    """True if the plan grants the feature, or if a per-tenant override
    explicitly enables it. Overrides cannot disable a plan-included feature
    (don't surprise customers by silently disabling what they paid for)."""
    if feature in plan.features:
        return True
    if overrides and overrides.get(feature) is True:
        return True
    return False


@dataclass(slots=True)
class TenantPlan:
    org_id: str
    plan: Plan
    overrides: dict[str, Any]
    plan_set_at: str | None
    plan_set_by: str | None

    def has_feature(self, feature: str) -> bool:
        return has_feature(self.plan, feature, overrides=self.overrides)


async def resolve_tenant_plan(
    session: AsyncSession,
    *,
    org_id: str | uuid.UUID,
) -> TenantPlan:
    """Read the org's current plan + overrides from Postgres."""
    try:
        parsed = uuid.UUID(str(org_id))
    except (TypeError, ValueError):
        return TenantPlan(
            org_id=str(org_id),
            plan=get_plan(None),
            overrides={},
            plan_set_at=None,
            plan_set_by=None,
        )
    result = await session.execute(
        select(
            Organization.plan_id,
            Organization.plan_overrides,
            Organization.plan_set_at,
            Organization.plan_set_by,
        ).where(Organization.id == parsed)
    )
    row = result.first()
    if row is None:
        return TenantPlan(
            org_id=str(parsed),
            plan=get_plan(None),
            overrides={},
            plan_set_at=None,
            plan_set_by=None,
        )
    plan_id, overrides, plan_set_at, plan_set_by = row
    return TenantPlan(
        org_id=str(parsed),
        plan=get_plan(plan_id),
        overrides=overrides if isinstance(overrides, dict) else {},
        plan_set_at=plan_set_at.isoformat() if plan_set_at else None,
        plan_set_by=str(plan_set_by) if plan_set_by else None,
    )


async def require_feature(
    session: AsyncSession,
    *,
    user: AuthenticatedUser,
    feature: str,
) -> TenantPlan:
    """Resolve the caller's plan and raise PermissionError if the feature
    isn't included. Routes that gate on a plan feature wrap their handler
    in this; e.g. /screening/entity calls ``require_feature(..., 'sanctions')``
    so a starter-tier bank gets a 402 with an upgrade message instead of
    silently running on a paid feature.

    Regulator-org tenants always have access — the platform operator
    bypasses billing.
    """
    if (user.org_type or "").lower() == "regulator":
        return TenantPlan(
            org_id=str(user.org_id),
            plan=get_plan("enterprise"),
            overrides={},
            plan_set_at=None,
            plan_set_by=None,
        )
    tenant = await resolve_tenant_plan(session, org_id=user.org_id)
    if not tenant.has_feature(feature):
        raise PermissionError(
            f"Feature '{feature}' is not included in the {tenant.plan.display_name} plan. "
            f"Contact procurement to upgrade."
        )
    return tenant


def plan_summary(plan: Plan) -> dict[str, Any]:
    """Serialise a plan for the admin UI."""
    return {
        "plan_id": plan.plan_id,
        "display_name": plan.display_name,
        "price_bdt_yearly": plan.price_bdt_yearly,
        "seat_cap": plan.seat_cap,
        "monthly_transaction_cap": plan.monthly_transaction_cap,
        "features": list(plan.features),
        "on_prem_eligible": plan.on_prem_eligible,
    }


def all_plans() -> list[dict[str, Any]]:
    return [plan_summary(p) for p in PLANS.values()]


async def set_tenant_plan(
    session: AsyncSession,
    *,
    user: AuthenticatedUser,
    target_org_id: uuid.UUID,
    plan_id: str,
    overrides: dict[str, Any] | None = None,
) -> TenantPlan:
    """Superadmin-only: change a tenant's plan + per-tenant overrides.

    Audit-logged. The ``plan_set_by`` / ``plan_set_at`` columns capture
    the change for procurement records.
    """
    if (user.role or "").lower() != "superadmin":
        raise PermissionError("Only superadmins can change tenant plans.")
    if plan_id not in PLANS:
        raise ValueError(f"Unknown plan_id '{plan_id}'")

    org = await session.get(Organization, target_org_id)
    if org is None:
        raise LookupError(f"Organization {target_org_id} not found")
    org.plan_id = plan_id
    org.plan_overrides = overrides or {}
    org.plan_set_at = datetime.now(UTC)
    try:
        org.plan_set_by = uuid.UUID(str(user.user_id))
    except (TypeError, ValueError):
        org.plan_set_by = None
    await session.commit()
    return await resolve_tenant_plan(session, org_id=target_org_id)
