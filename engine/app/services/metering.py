"""V3 P7.2 — monthly transaction-write metering + hard cap enforcement.

Each successful POST /transactions/score increments the per-org counter
on `metered_writes` for the current Asia/Dhaka calendar month. Before
incrementing, the route checks whether the caller's plan has a monthly
cap and whether the current count is already at-or-above it; if so, the
route returns 402 PAYMENT REQUIRED.

`period_start` is the first day of the Dhaka-local month at UTC 00:00.
We don't store a TZ — the date column is plain `date` and the application
layer is the only thing that picks "what month does this row represent."
Keeping it as the Dhaka first-of-month means a month boundary has one
unambiguous row per tenant; cross-region complications don't apply
because every customer runs against Dhaka time.

Design choices:

- **Cap check happens before the increment.** A bank that's already at
  cap gets rejected; the count never exceeds the cap by more than the
  number of concurrent in-flight requests at the moment they all clear
  the gate (small race; acceptable for v1).
- **Regulator orgs are exempt.** The platform operator doesn't pay
  per-transaction.
- **Plans without a `monthly_transaction_cap` (None) skip the check.**
  Professional + enterprise have no cap; only starter does (500k).
- **Writes use `INSERT ... ON CONFLICT DO UPDATE`.** Concurrent
  increments are allowed to race on `transaction_count + 1`; Postgres
  serialises the row update so the count is monotonically correct.
"""
from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import AuthenticatedUser
from app.models.metering import MeteredWrite
from app.services.billing import resolve_tenant_plan

logger = logging.getLogger("kestrel.metering")

DHAKA_OFFSET = timedelta(hours=6)  # Asia/Dhaka is UTC+6 year-round (no DST).


def current_period_start(now: datetime | None = None) -> date:
    """Return the first day of the current Asia/Dhaka calendar month.

    Tested against fixed `now` values; production calls pass None so
    the helper reads the wall clock.
    """
    if now is None:
        now = datetime.now(UTC)
    if now.tzinfo is None:
        now = now.replace(tzinfo=UTC)
    dhaka = now.astimezone(timezone(DHAKA_OFFSET))
    return date(dhaka.year, dhaka.month, 1)


@dataclass(frozen=True, slots=True)
class CapStatus:
    plan_id: str
    cap: int | None
    used: int
    remaining: int | None  # None when there is no cap
    over_cap: bool

    def to_summary(self) -> dict:
        return {
            "plan_id": self.plan_id,
            "monthly_transaction_cap": self.cap,
            "used": self.used,
            "remaining": self.remaining,
            "over_cap": self.over_cap,
        }


async def _get_count(
    session: AsyncSession, *, org_id: uuid.UUID, period: date
) -> int:
    result = await session.execute(
        select(MeteredWrite.transaction_count).where(
            MeteredWrite.org_id == org_id,
            MeteredWrite.period_start == period,
        )
    )
    row = result.first()
    return int(row[0]) if row else 0


def _compute_cap_status(*, plan_id: str, cap: int | None, used: int) -> CapStatus:
    if cap is None:
        return CapStatus(plan_id=plan_id, cap=None, used=used, remaining=None, over_cap=False)
    return CapStatus(
        plan_id=plan_id,
        cap=cap,
        used=used,
        remaining=max(0, cap - used),
        over_cap=used >= cap,
    )


async def check_monthly_cap(
    session: AsyncSession, *, user: AuthenticatedUser, now: datetime | None = None
) -> CapStatus:
    """Read the caller's current month-to-date count + plan cap.

    Returns a CapStatus; the caller decides whether to raise. Regulator
    orgs short-circuit to "unlimited."
    """
    if (user.org_type or "").lower() == "regulator":
        return CapStatus(plan_id="enterprise", cap=None, used=0, remaining=None, over_cap=False)
    try:
        org_id = uuid.UUID(str(user.org_id))
    except (TypeError, ValueError):
        # Should never happen with a valid Supabase JWT; soft-fail open
        # so a malformed user doesn't accidentally lock out paying tenants.
        return CapStatus(plan_id="starter", cap=None, used=0, remaining=None, over_cap=False)
    tenant = await resolve_tenant_plan(session, org_id=org_id)
    period = current_period_start(now)
    used = await _get_count(session, org_id=org_id, period=period)
    return _compute_cap_status(
        plan_id=tenant.plan.plan_id,
        cap=tenant.plan.monthly_transaction_cap,
        used=used,
    )


async def increment_transaction_count(
    session: AsyncSession, *, user: AuthenticatedUser, now: datetime | None = None
) -> CapStatus:
    """Atomically bump the caller's monthly counter by 1. Returns the
    post-increment CapStatus so the caller can decide what to surface
    in the response (e.g. an x-kestrel-cap-remaining header)."""
    if (user.org_type or "").lower() == "regulator":
        return CapStatus(plan_id="enterprise", cap=None, used=0, remaining=None, over_cap=False)
    try:
        org_id = uuid.UUID(str(user.org_id))
    except (TypeError, ValueError):
        return CapStatus(plan_id="starter", cap=None, used=0, remaining=None, over_cap=False)
    period = current_period_start(now)
    stmt = (
        pg_insert(MeteredWrite.__table__)
        .values(org_id=org_id, period_start=period, transaction_count=1, last_incremented_at=datetime.now(UTC))
        .on_conflict_do_update(
            index_elements=["org_id", "period_start"],
            set_={
                "transaction_count": MeteredWrite.__table__.c.transaction_count + 1,
                "last_incremented_at": datetime.now(UTC),
            },
        )
        .returning(MeteredWrite.__table__.c.transaction_count)
    )
    result = await session.execute(stmt)
    used = int(result.scalar_one())
    tenant = await resolve_tenant_plan(session, org_id=org_id)
    return _compute_cap_status(
        plan_id=tenant.plan.plan_id,
        cap=tenant.plan.monthly_transaction_cap,
        used=used,
    )


async def gate_then_increment(
    session: AsyncSession, *, user: AuthenticatedUser, now: datetime | None = None
) -> CapStatus:
    """Two-step: check cap; if over, raise PermissionError (-> 402);
    otherwise bump and return the post-increment status.

    Wrapping callers can convert PermissionError → HTTPException(402)
    consistently with the rest of the billing surface (matches the
    existing services.billing.require_feature pattern)."""
    pre = await check_monthly_cap(session, user=user, now=now)
    if pre.over_cap:
        raise PermissionError(
            f"Monthly transaction cap of {pre.cap} reached on the {pre.plan_id} plan. "
            "Upgrade to Professional or Enterprise for unlimited scoring, or wait for the next billing period."
        )
    return await increment_transaction_count(session, user=user, now=now)
