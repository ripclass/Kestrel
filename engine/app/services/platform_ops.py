"""Platform-operator service — cross-tenant pilot-health aggregation.

Enso-internal. Answers two operator questions during the pilot wave:
"are the banks actually using Kestrel?" and "which ones are stalling?".

Read-only. Runs on the plain ``SessionLocal`` (engine connects as
``postgres`` / BYPASSRLS) so it can see every tenant — the cross-tenant
visibility this surface needs is exactly what RLS denies normal callers,
which is why ``app.auth.require_platform_operator`` gates the routes.

Engagement signal = the most recent of (last Supabase login, last
``audit_log`` action). ``audit_log`` is the load-bearing signal — it
records real work (STR drafted, alert reviewed, case opened); logins
alone only say someone showed up.
"""
from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import distinct, func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.alert import Alert
from app.models.audit import AuditLog
from app.models.case import Case
from app.models.detection_run import DetectionRun
from app.models.org import Organization
from app.models.profile import Profile
from app.models.str_report import STRReport

logger = logging.getLogger("kestrel.platform_ops")


# --- pure helpers (unit-tested in test_platform_ops.py) ----------------------

def _now() -> datetime:
    return datetime.now(UTC)


def engagement_status(last_seen: datetime | None, now: datetime) -> str:
    """Bucket a tenant/user by recency of last meaningful contact.

    active  — seen within 3 days
    idle    — seen within 14 days
    dormant — seen, but longer ago than that
    never   — no login and no recorded action, ever
    """
    if last_seen is None:
        return "never"
    age_days = (now - last_seen).total_seconds() / 86400.0
    if age_days <= 3:
        return "active"
    if age_days <= 14:
        return "idle"
    return "dormant"


def activity_trend(current: int, previous: int) -> str:
    """Compare this week's action count against the prior week.

    Uses a ±15% band so normal week-to-week noise reads as ``flat``.
    A tenant with no prior-week baseline that did something this week
    is ``new`` rather than a misleading 'rising'.
    """
    if previous <= 0:
        return "new" if current > 0 else "flat"
    delta = (current - previous) / previous
    if delta >= 0.15:
        return "rising"
    if delta <= -0.15:
        return "falling"
    return "flat"


def latest(*candidates: datetime | None) -> datetime | None:
    """Most recent of a set of optional datetimes (None-safe)."""
    seen = [c for c in candidates if c is not None]
    return max(seen) if seen else None


def _iso(value: datetime | None) -> str | None:
    return value.isoformat() if value else None


def _as_str(value: Any) -> str:
    return str(value) if value is not None else ""


# --- login data (cross-schema, defensive) ------------------------------------

async def _login_rows(session: AsyncSession) -> list[tuple[str, str, datetime | None]]:
    """`(org_id, user_id, last_sign_in_at)` for every provisioned profile.

    Reads ``auth.users`` — accessible because the engine connects as
    ``postgres``. If that ever fails (permissions, schema drift) the
    surface degrades to audit-log-only engagement rather than 500-ing.
    """
    try:
        result = await session.execute(
            text(
                """
                select p.org_id::text as org_id,
                       p.id::text as user_id,
                       u.last_sign_in_at as last_sign_in_at
                from profiles p
                left join auth.users u on u.id = p.id
                """
            )
        )
    except Exception:  # noqa: BLE001 — degrade gracefully, never crash the console
        logger.warning("platform_ops: auth.users unreadable; login data omitted", exc_info=True)
        return []
    return [(row[0], row[1], row[2]) for row in result.all()]


# --- aggregation -------------------------------------------------------------

async def _domain_counts(session: AsyncSession, model: Any) -> dict[str, int]:
    """`{org_id: count}` for any model carrying an ``org_id`` column."""
    result = await session.execute(
        select(model.org_id, func.count()).group_by(model.org_id)
    )
    return {_as_str(row[0]): int(row[1]) for row in result.all() if row[0] is not None}


async def _audit_activity(
    session: AsyncSession, now: datetime
) -> dict[str, dict[str, Any]]:
    """Per-org audit-log activity: action counts in 3 windows, last action,
    distinct active users this week."""
    d7 = now - timedelta(days=7)
    d14 = now - timedelta(days=14)
    d30 = now - timedelta(days=30)
    result = await session.execute(
        select(
            AuditLog.org_id,
            func.count().filter(AuditLog.created_at >= d7),
            func.count().filter(AuditLog.created_at >= d14, AuditLog.created_at < d7),
            func.count().filter(AuditLog.created_at >= d30),
            func.max(AuditLog.created_at),
            func.count(distinct(AuditLog.user_id)).filter(AuditLog.created_at >= d7),
        ).group_by(AuditLog.org_id)
    )
    out: dict[str, dict[str, Any]] = {}
    for row in result.all():
        if row[0] is None:
            continue
        out[_as_str(row[0])] = {
            "actions_7d": int(row[1] or 0),
            "actions_prev_7d": int(row[2] or 0),
            "actions_30d": int(row[3] or 0),
            "last_activity_at": row[4],
            "active_users_7d": int(row[5] or 0),
        }
    return out


def _build_card(
    org: Any,
    *,
    now: datetime,
    seats: int,
    logins: list[datetime | None],
    activity: dict[str, Any],
    strs: int,
    alerts: int,
    cases: int,
    scans: int,
) -> dict[str, Any]:
    real_logins = [dt for dt in logins if dt is not None]
    last_login = max(real_logins) if real_logins else None
    last_activity = activity.get("last_activity_at")
    last_seen = latest(last_login, last_activity)
    actions_7d = activity.get("actions_7d", 0)
    actions_prev_7d = activity.get("actions_prev_7d", 0)
    return {
        "org_id": str(org.id),
        "org_name": org.name,
        "org_type": org.org_type,
        "plan_id": org.plan_id or "starter",
        "created_at": _iso(getattr(org, "created_at", None)),
        "seats": seats,
        "seats_logged_in": len(real_logins),
        "last_login_at": _iso(last_login),
        "last_activity_at": _iso(last_activity),
        "engagement": engagement_status(last_seen, now),
        "actions_7d": actions_7d,
        "actions_prev_7d": actions_prev_7d,
        "actions_30d": activity.get("actions_30d", 0),
        "trend": activity_trend(actions_7d, actions_prev_7d),
        "active_users_7d": activity.get("active_users_7d", 0),
        "strs": strs,
        "alerts": alerts,
        "cases": cases,
        "scans": scans,
    }


async def build_pilot_overview(session: AsyncSession) -> dict[str, Any]:
    now = _now()

    orgs = (
        await session.execute(
            select(
                Organization.id,
                Organization.name,
                Organization.org_type,
                Organization.plan_id,
                Organization.created_at,
            )
        )
    ).all()

    seats_result = await session.execute(
        select(Profile.org_id, func.count()).group_by(Profile.org_id)
    )
    seats_by_org = {_as_str(r[0]): int(r[1]) for r in seats_result.all()}

    logins_by_org: dict[str, list[datetime | None]] = {}
    for org_id, _user_id, last_sign_in in await _login_rows(session):
        logins_by_org.setdefault(org_id, []).append(last_sign_in)

    activity_by_org = await _audit_activity(session, now)
    strs_by_org = await _domain_counts(session, STRReport)
    alerts_by_org = await _domain_counts(session, Alert)
    cases_by_org = await _domain_counts(session, Case)
    scans_by_org = await _domain_counts(session, DetectionRun)

    cards: list[dict[str, Any]] = []
    for org in orgs:
        oid = str(org.id)
        cards.append(
            _build_card(
                org,
                now=now,
                seats=seats_by_org.get(oid, 0),
                logins=logins_by_org.get(oid, []),
                activity=activity_by_org.get(oid, {}),
                strs=strs_by_org.get(oid, 0),
                alerts=alerts_by_org.get(oid, 0),
                cases=cases_by_org.get(oid, 0),
                scans=scans_by_org.get(oid, 0),
            )
        )

    # Most-recently-active first; tenants that have never been seen sort last.
    cards.sort(key=lambda c: c["last_activity_at"] or "", reverse=True)

    summary = {
        "tenants_total": len(cards),
        "tenants_bank": sum(1 for c in cards if c["org_type"] == "bank"),
        "tenants_active_7d": sum(1 for c in cards if c["actions_7d"] > 0),
        "seats_total": sum(c["seats"] for c in cards),
        "seats_logged_in": sum(c["seats_logged_in"] for c in cards),
        "actions_7d": sum(c["actions_7d"] for c in cards),
        "strs_total": sum(c["strs"] for c in cards),
        "alerts_total": sum(c["alerts"] for c in cards),
        "cases_total": sum(c["cases"] for c in cards),
        "generated_at": now.isoformat(),
    }
    return {"summary": summary, "pilots": cards}


async def build_pilot_detail(session: AsyncSession, *, org_id: str) -> dict[str, Any]:
    """Drill-down for one tenant: the same card, plus per-user activity, a
    recent-action feed, and a 30-day action breakdown by resource type."""
    try:
        org_uuid = uuid.UUID(str(org_id))
    except (TypeError, ValueError) as exc:
        raise ValueError("Invalid organization id") from exc

    now = _now()
    org = await session.get(Organization, org_uuid)
    if org is None:
        raise LookupError(f"Organization {org_id} not found")

    seats_result = await session.execute(
        select(func.count()).select_from(Profile).where(Profile.org_id == org_uuid)
    )
    seats = int(seats_result.scalar_one() or 0)

    org_logins = [
        last_sign_in
        for oid, _uid, last_sign_in in await _login_rows(session)
        if oid == str(org_uuid)
    ]
    activity = (await _audit_activity(session, now)).get(str(org_uuid), {})

    async def _count(model: Any) -> int:
        res = await session.execute(
            select(func.count()).select_from(model).where(model.org_id == org_uuid)
        )
        return int(res.scalar_one() or 0)

    card = _build_card(
        org,
        now=now,
        seats=seats,
        logins=org_logins,
        activity=activity,
        strs=await _count(STRReport),
        alerts=await _count(Alert),
        cases=await _count(Case),
        scans=await _count(DetectionRun),
    )

    users = await _user_activity(session, org_uuid=org_uuid, now=now)
    recent_actions = await _recent_actions(session, org_uuid=org_uuid)
    action_breakdown = await _action_breakdown(session, org_uuid=org_uuid, now=now)

    return {
        "card": card,
        "users": users,
        "recent_actions": recent_actions,
        "action_breakdown": action_breakdown,
    }


async def _user_activity(
    session: AsyncSession, *, org_uuid: uuid.UUID, now: datetime
) -> list[dict[str, Any]]:
    d7 = now - timedelta(days=7)
    d30 = now - timedelta(days=30)

    profiles = (
        await session.execute(
            select(
                Profile.id,
                Profile.full_name,
                Profile.role,
                Profile.persona,
                Profile.designation,
            ).where(Profile.org_id == org_uuid)
        )
    ).all()

    per_user = await session.execute(
        select(
            AuditLog.user_id,
            func.count().filter(AuditLog.created_at >= d7),
            func.count().filter(AuditLog.created_at >= d30),
            func.max(AuditLog.created_at),
        )
        .where(AuditLog.org_id == org_uuid)
        .group_by(AuditLog.user_id)
    )
    activity_by_user = {
        _as_str(r[0]): {
            "actions_7d": int(r[1] or 0),
            "actions_30d": int(r[2] or 0),
            "last_activity_at": r[3],
        }
        for r in per_user.all()
        if r[0] is not None
    }

    login_by_user = {
        uid: last_sign_in
        for oid, uid, last_sign_in in await _login_rows(session)
        if oid == str(org_uuid)
    }

    users: list[dict[str, Any]] = []
    for prof in profiles:
        uid = str(prof.id)
        act = activity_by_user.get(uid, {})
        last_login = login_by_user.get(uid)
        last_activity = act.get("last_activity_at")
        last_seen = latest(last_login, last_activity)
        users.append(
            {
                "user_id": uid,
                "full_name": prof.full_name,
                "role": prof.role,
                "persona": prof.persona,
                "designation": prof.designation,
                "last_login_at": _iso(last_login),
                "last_activity_at": _iso(last_activity),
                "actions_7d": act.get("actions_7d", 0),
                "actions_30d": act.get("actions_30d", 0),
                "engagement": engagement_status(last_seen, now),
            }
        )
    users.sort(key=lambda u: u["last_activity_at"] or "", reverse=True)
    return users


async def _recent_actions(
    session: AsyncSession, *, org_uuid: uuid.UUID, limit: int = 25
) -> list[dict[str, Any]]:
    result = await session.execute(
        select(
            AuditLog.created_at,
            AuditLog.action,
            AuditLog.resource_type,
            AuditLog.user_id,
        )
        .where(AuditLog.org_id == org_uuid)
        .order_by(AuditLog.created_at.desc())
        .limit(max(1, min(int(limit), 100)))
    )
    return [
        {
            "created_at": _iso(r[0]),
            "action": r[1],
            "resource_type": r[2],
            "user_id": _as_str(r[3]) or None,
        }
        for r in result.all()
    ]


async def _action_breakdown(
    session: AsyncSession, *, org_uuid: uuid.UUID, now: datetime
) -> dict[str, int]:
    d30 = now - timedelta(days=30)
    result = await session.execute(
        select(AuditLog.resource_type, func.count())
        .where(AuditLog.org_id == org_uuid, AuditLog.created_at >= d30)
        .group_by(AuditLog.resource_type)
    )
    return {
        (r[0] or "other"): int(r[1])
        for r in result.all()
    }
