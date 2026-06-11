"""V3 P7.1 — Stripe billing integration (framework).

Subscription state lives in Stripe; Kestrel mirrors the slice it needs
(plan_id, subscription_status, grace period) onto the `organizations`
row when a webhook arrives. We DO NOT proactively call Stripe — the
engine is reactive: a webhook lands, we validate the signature, we
update the row, we ack. This keeps the on-prem deployment story clean
(an air-gapped customer can disable Stripe entirely without breaking
the rest of the billing surface).

Webhook signature verification is done by hand against
``STRIPE_WEBHOOK_SECRET`` — the same Stripe-Signature scheme described
at https://docs.stripe.com/webhooks/signatures. We deliberately don't
import the ``stripe`` Python package because:

1. We don't make outbound calls; the SDK is heavy for our use.
2. The signature scheme is small and stable; reimplementing keeps the
   on-prem image lighter.

When the customer support team needs to make outbound calls (e.g. to
issue a refund), they use the Stripe Dashboard directly. The engine's
job is to keep the local tenant row consistent with Stripe.

Subscription event mapping:

    customer.subscription.created   -> mirror status + price -> plan_id
    customer.subscription.updated   -> same; plan_id may change on upgrade
    customer.subscription.deleted   -> downgrade to starter; clear sub id
    invoice.payment_succeeded       -> clear plan_grace_until
    invoice.payment_failed          -> set plan_grace_until = now + 7d
    customer.subscription.trial_will_end -> log only; UI surfaces it

Failed-payment behaviour: on `invoice.payment_failed`, the engine sets
``plan_grace_until = now + 7 days``. While the grace window is open,
the tenant keeps full feature access — billing.has_feature is still
honoured against `plan_id`, not the subscription status. After the
grace window closes (the next failed invoice or a Beat sweep), the
tenant downgrades to ``starter``.
"""
from __future__ import annotations

import hashlib
import hmac
import logging
import time
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.org import Organization
from app.services.billing import PLANS

logger = logging.getLogger("kestrel.stripe")

GRACE_PERIOD_DAYS = 7
SIGNATURE_TOLERANCE_SECONDS = 300


# Default mapping; production sets this from env (STRIPE_PRICE_ID_STARTER
# / _PROFESSIONAL / _ENTERPRISE) so the same code points at test-mode
# prices in staging and live prices in prod.
def default_price_to_plan(*, starter: str | None, professional: str | None, enterprise: str | None) -> dict[str, str]:
    out: dict[str, str] = {}
    if starter:
        out[starter] = "starter"
    if professional:
        out[professional] = "professional"
    if enterprise:
        out[enterprise] = "enterprise"
    return out


def resolve_plan_for_price(price_id: str, mapping: dict[str, str]) -> str:
    """Look up plan_id by Stripe price_id, falling back to starter."""
    plan_id = mapping.get(price_id, "starter")
    if plan_id not in PLANS:
        logger.warning("stripe.unknown_plan_in_mapping", extra={"price_id": price_id, "plan_id": plan_id})
        return "starter"
    return plan_id


# --- Signature verification --------------------------------------------------

@dataclass(frozen=True, slots=True)
class SignatureCheck:
    valid: bool
    reason: str | None = None


def verify_signature(
    *,
    payload: bytes,
    header: str | None,
    secret: str | None,
    now: float | None = None,
    tolerance_seconds: int = SIGNATURE_TOLERANCE_SECONDS,
) -> SignatureCheck:
    """Validate a Stripe-Signature header.

    Format: ``t=1234567890,v1=hexhmac,v0=hexhmac`` — verify each v1
    digest against HMAC-SHA256 of ``"{t}.{payload.decode()}"`` keyed
    on ``secret``. Reject if the timestamp is outside the tolerance
    window in either direction — a far-future timestamp would otherwise
    make a captured signature replayable indefinitely.
    """
    if not secret:
        return SignatureCheck(valid=False, reason="webhook_secret_not_configured")
    if not header:
        return SignatureCheck(valid=False, reason="signature_header_missing")
    parts = {k: v for k, v in (item.split("=", 1) for item in header.split(",") if "=" in item)}
    timestamp_raw = parts.get("t")
    if not timestamp_raw:
        return SignatureCheck(valid=False, reason="timestamp_missing")
    try:
        timestamp = int(timestamp_raw)
    except ValueError:
        return SignatureCheck(valid=False, reason="timestamp_malformed")
    if abs((now or time.time()) - timestamp) > tolerance_seconds:
        return SignatureCheck(valid=False, reason="timestamp_outside_tolerance")
    expected = hmac.new(
        secret.encode("utf-8"),
        msg=f"{timestamp}.".encode() + payload,
        digestmod=hashlib.sha256,
    ).hexdigest()
    candidates = [v for k, v in parts.items() if k.startswith("v1")]
    if not candidates:
        return SignatureCheck(valid=False, reason="no_v1_signature")
    for candidate in candidates:
        if hmac.compare_digest(expected, candidate):
            return SignatureCheck(valid=True)
    return SignatureCheck(valid=False, reason="signature_mismatch")


# --- Event handlers ----------------------------------------------------------

@dataclass(slots=True)
class HandledEvent:
    event_type: str
    org_id: str | None
    plan_id: str | None
    subscription_status: str | None
    grace_until: datetime | None
    summary: str


def _resolve_plan(price_id: str, mapping: dict[str, str]) -> str:
    return resolve_plan_for_price(price_id, mapping)


def _grace_window(*, now: datetime | None = None) -> datetime:
    return (now or datetime.now(UTC)) + timedelta(days=GRACE_PERIOD_DAYS)


async def _find_org_by_customer(session: AsyncSession, customer_id: str) -> Organization | None:
    stmt = select(Organization).where(Organization.stripe_customer_id == customer_id)
    return (await session.execute(stmt)).scalar_one_or_none()


async def _find_org_by_subscription(session: AsyncSession, subscription_id: str) -> Organization | None:
    stmt = select(Organization).where(Organization.stripe_subscription_id == subscription_id)
    return (await session.execute(stmt)).scalar_one_or_none()


async def handle_subscription_event(
    session: AsyncSession,
    *,
    event_type: str,
    payload: dict[str, Any],
    price_to_plan: dict[str, str],
    now: datetime | None = None,
) -> HandledEvent:
    """Dispatch a parsed Stripe event to the right Organization mutation.

    Returns a HandledEvent so the webhook router can log a structured
    summary. Unknown / unmapped events become a no-op with a log line.
    """
    obj = payload.get("data", {}).get("object", {}) or {}
    customer_id = obj.get("customer")
    subscription_id = obj.get("subscription") or obj.get("id")
    items = (obj.get("items") or {}).get("data") or []
    price_id = items[0].get("price", {}).get("id") if items else None

    org: Organization | None = None
    if subscription_id and event_type.startswith("customer.subscription."):
        org = await _find_org_by_subscription(session, subscription_id)
    if org is None and customer_id:
        org = await _find_org_by_customer(session, customer_id)
    if org is None:
        logger.warning(
            "stripe.event.no_match",
            extra={"event_type": event_type, "customer_id": customer_id, "subscription_id": subscription_id},
        )
        return HandledEvent(
            event_type=event_type,
            org_id=None,
            plan_id=None,
            subscription_status=None,
            grace_until=None,
            summary="no_matching_organization",
        )

    summary = "noop"
    plan_id_after = org.plan_id
    grace_after = org.plan_grace_until

    if event_type in ("customer.subscription.created", "customer.subscription.updated"):
        if price_id:
            org.stripe_price_id = price_id
            plan_id_after = _resolve_plan(price_id, price_to_plan)
            org.plan_id = plan_id_after
        new_status = obj.get("status")
        if new_status:
            org.stripe_subscription_status = new_status
        if subscription_id:
            org.stripe_subscription_id = subscription_id
        org.plan_set_at = datetime.now(UTC)
        try:
            org.plan_set_by = uuid.UUID("00000000-0000-0000-0000-000000000000")  # system marker
        except ValueError:
            org.plan_set_by = None
        summary = "subscription_synced"
    elif event_type == "customer.subscription.deleted":
        org.stripe_subscription_status = "canceled"
        plan_id_after = "starter"
        org.plan_id = plan_id_after
        org.plan_grace_until = None
        grace_after = None
        org.plan_set_at = datetime.now(UTC)
        summary = "subscription_canceled_downgraded_to_starter"
    elif event_type == "invoice.payment_failed":
        grace_after = _grace_window(now=now)
        org.plan_grace_until = grace_after
        org.stripe_subscription_status = "past_due"
        summary = "payment_failed_grace_set"
    elif event_type == "invoice.payment_succeeded":
        org.plan_grace_until = None
        grace_after = None
        if org.stripe_subscription_status == "past_due":
            org.stripe_subscription_status = "active"
        summary = "payment_succeeded_grace_cleared"
    elif event_type == "customer.subscription.trial_will_end":
        summary = "trial_will_end_logged"
    else:
        summary = "unhandled_event_type"

    await session.commit()
    return HandledEvent(
        event_type=event_type,
        org_id=str(org.id),
        plan_id=plan_id_after,
        subscription_status=org.stripe_subscription_status,
        grace_until=grace_after,
        summary=summary,
    )


def evaluate_grace_expiry(
    *,
    plan_id: str,
    subscription_status: str | None,
    grace_until: datetime | None,
    now: datetime | None = None,
) -> str:
    """Pure helper: should the tenant be downgraded NOW?

    Returns the plan_id the tenant should land on. The grace window is
    permissive — only an expired window with no matching active payment
    triggers a downgrade. Sweepable from a Beat task; not currently
    scheduled because invoice.payment_failed → followed-by → succeeded
    re-clears the grace inline.
    """
    if grace_until is None:
        return plan_id
    if (now or datetime.now(UTC)) <= grace_until:
        return plan_id
    if subscription_status in ("active", "trialing"):
        return plan_id
    return "starter"
