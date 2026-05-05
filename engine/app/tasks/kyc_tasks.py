"""Periodic KYC re-screening task (V2 phase 5.4).

Daily Beat-driven sweep at 03:00 BDT (after the 02:30 watchlist refresh).
For each org, picks every approved/review customer whose
``last_rescreened_at`` is missing or older than the configured window,
re-runs sanctions screening, and persists the fresh ``screening_results``.

When a re-screen surfaces a primary-customer hit at score >= 0.9 that
wasn't in the previous results, the task emits an alert
(``source_type='kyc_rescreen'``) and creates a case for analyst review.
This is the "watchlist X was added on Wednesday → customer Y onboarded
in February now matches it" loop.
"""
from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import select

from app.database import SessionLocal
from app.models.alert import Alert
from app.models.audit import AuditLog
from app.models.case import Case
from app.models.customer import Customer
from app.services.kyc import (
    BeneficialOwner,
    CustomerOnboardRequest,
    _compose_risk_score,
    _decide_risk,
    _matches_to_payload,
    _screen_customer_and_owners,
)
from app.tasks.celery_app import celery_app

logger = logging.getLogger("kestrel.tasks.kyc")

_RESCREEN_AGE_DAYS = 7
_NEW_HIT_SCORE_THRESHOLD = 0.9


@celery_app.task(name="app.tasks.kyc_tasks.rescreen_active_customers")
def rescreen_active_customers() -> dict[str, Any]:
    """Beat-driven entrypoint."""
    summary = asyncio.run(_run())
    if summary.get("escalations", 0) > 0:
        logger.warning("kyc.rescreen.escalations", extra={"summary": summary})
    elif summary.get("rescreened", 0) > 0:
        logger.info("kyc.rescreen.batch", extra={"summary": summary})
    return summary


async def _run() -> dict[str, Any]:
    cutoff = datetime.now(UTC) - timedelta(days=_RESCREEN_AGE_DAYS)
    rescreened = 0
    escalations = 0
    failures = 0

    async with SessionLocal() as session:
        result = await session.execute(
            select(Customer)
            .where(Customer.kyc_status.in_(["approved", "review"]))
            .where(
                (Customer.last_rescreened_at.is_(None))
                | (Customer.last_rescreened_at < cutoff)
            )
            .limit(500)
        )
        candidates = list(result.scalars().all())

        for customer in candidates:
            try:
                escalated = await _rescreen_one(session, customer)
                rescreened += 1
                if escalated:
                    escalations += 1
            except Exception as exc:  # noqa: BLE001 — defensive batch loop
                failures += 1
                logger.warning(
                    "kyc.rescreen.failed",
                    extra={
                        "customer_id": str(customer.id),
                        "error_type": type(exc).__name__,
                    },
                )
        await session.commit()

    return {
        "status": "completed",
        "ran_at": datetime.now(UTC).isoformat(),
        "candidates": len(candidates),
        "rescreened": rescreened,
        "escalations": escalations,
        "failures": failures,
    }


async def _rescreen_one(session, customer: Customer) -> bool:
    """Re-run screening for one customer. Returns True if a new hit escalated."""
    request = CustomerOnboardRequest(
        customer_external_id=customer.customer_external_id,
        customer_type=customer.customer_type,
        full_name=customer.full_name,
        nid=customer.nid,
        passport=customer.passport,
        date_of_birth=customer.date_of_birth,
        nationality=customer.nationality,
        beneficial_owners=[
            BeneficialOwner(
                full_name=str(bo.get("full_name") or ""),
                nid=bo.get("nid"),
                passport=bo.get("passport"),
                date_of_birth=bo.get("date_of_birth"),
                nationality=bo.get("nationality"),
                ownership_pct=bo.get("ownership_pct"),
            )
            for bo in (customer.beneficial_owners or [])
            if isinstance(bo, dict) and bo.get("full_name")
        ],
    )
    primary, bo_results = await _screen_customer_and_owners(session, request=request)

    previous_top = _previous_top_primary_score(customer.screening_results)
    new_top = max((m.match_score for m in primary), default=0.0)
    new_hit = new_top >= _NEW_HIT_SCORE_THRESHOLD and new_top > previous_top

    has_direct_hit = new_top >= _NEW_HIT_SCORE_THRESHOLD
    score = _compose_risk_score(primary_matches=primary, bo_matches_by_name=bo_results)
    risk_level, kyc_status = _decide_risk(score=score, has_direct_hit=has_direct_hit)

    customer.risk_score = score
    customer.risk_level = risk_level
    if kyc_status == "declined" or customer.kyc_status == "pending":
        customer.kyc_status = kyc_status
    customer.screening_results = {
        "screened_at": datetime.now(UTC).isoformat(),
        "primary": _matches_to_payload(primary),
        "beneficial_owners": {
            name: _matches_to_payload(matches) for name, matches in bo_results.items()
        },
    }
    customer.last_rescreened_at = datetime.now(UTC)

    if new_hit:
        await _emit_escalation(
            session,
            customer=customer,
            primary_top_score=new_top,
            primary_match=primary[0] if primary else None,
        )
    return new_hit


def _previous_top_primary_score(screening_results: Any) -> float:
    """Pull the previously highest primary-match score from stored JSON."""
    if not isinstance(screening_results, dict):
        return 0.0
    primary = screening_results.get("primary")
    if not isinstance(primary, list) or not primary:
        return 0.0
    best = 0.0
    for item in primary:
        if not isinstance(item, dict):
            continue
        try:
            score = float(item.get("match_score") or 0)
        except (TypeError, ValueError):
            continue
        if score > best:
            best = score
    return best


async def _emit_escalation(
    session,
    *,
    customer: Customer,
    primary_top_score: float,
    primary_match: Any,
) -> None:
    """Emit an alert + case when a re-screen surfaces a new high-confidence hit."""
    alert = Alert(
        id=uuid.uuid4(),
        org_id=customer.org_id,
        source_type="kyc_rescreen",
        source_id=customer.id,
        entity_id=None,
        title=f"KYC re-screen hit: {customer.full_name}",
        description=(
            f"Periodic re-screen surfaced a new sanctions / PEP match for "
            f"customer {customer.full_name} "
            f"(external_id={customer.customer_external_id}) at score {primary_top_score:.2f}."
        ),
        alert_type="kyc_rescreen",
        risk_score=int(min(100, round(primary_top_score * 100))),
        severity="high" if primary_top_score < 0.95 else "critical",
        status="open",
        reasons=[
            {
                "rule": "kyc_rescreen",
                "score": int(round(primary_top_score * 100)),
                "explanation": (
                    f"Customer {customer.full_name} now matches "
                    f"{getattr(primary_match, 'list_source', 'a watchlist')} entry "
                    f"'{getattr(primary_match, 'matched_name', 'unknown')}' "
                    f"after a periodic re-screen."
                ),
            }
        ],
    )
    session.add(alert)

    case = Case(
        id=uuid.uuid4(),
        org_id=customer.org_id,
        title=f"KYC re-screen escalation: {customer.full_name}",
        summary=alert.description,
        category="kyc",
        severity=alert.severity,
        status="open",
        linked_alert_ids=[alert.id],
        timeline=[
            {
                "event": "kyc_rescreen.escalation",
                "ts": datetime.now(UTC).isoformat(),
                "customer_id": str(customer.id),
                "customer_external_id": customer.customer_external_id,
                "primary_top_score": primary_top_score,
                "list_source": getattr(primary_match, "list_source", None),
                "matched_name": getattr(primary_match, "matched_name", None),
            }
        ],
        variant="escalated",
    )
    session.add(case)

    session.add(
        AuditLog(
            org_id=customer.org_id,
            user_id=None,
            action="kyc.rescreen.escalation",
            resource_type="customer",
            resource_id=customer.id,
            details={
                "alert_id": str(alert.id),
                "case_id": str(case.id),
                "primary_top_score": primary_top_score,
            },
        )
    )
    await session.flush()
