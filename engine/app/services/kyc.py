"""KYC / CDD customer-onboarding service (V2 phase 5).

Six exposed operations:

  - ``onboard_customer``   create + screen the customer, return decision
  - ``list_customers``     filtered list (own-org or regulator)
  - ``get_customer``       single row with screening_results
  - ``update_customer``    PATCH for safe metadata fields
  - ``review_customer``    CAMLCO sets kyc_status + reviewed_at + reviewed_by
  - ``rescreen_customer``  re-runs sanctions; called inline + by Beat task

Inline screening reuses ``services.screening.screen_entity`` (Phase 4) on
the customer + each beneficial owner. The composed customer-level
``risk_score`` drives ``risk_level`` and ``kyc_status``:

    score < 30          -> low      / approved
    30 <= score < 60    -> medium   / approved (with watchlist note)
    60 <= score < 80    -> high     / review
    score >= 80         -> declined / declined

A direct sanctions hit on the primary customer at any score immediately
forces ``risk_level=declined`` + ``kyc_status=declined`` regardless of
the composed score, since onboarding a sanctions-listed party is itself
a regulatory violation.
"""
from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import AuthenticatedUser
from app.models.audit import AuditLog
from app.models.customer import Customer
from app.services.screening import (
    ScreeningMatch,
    ScreeningRequest,
    parse_screening_date,
    screen_entity,
)

logger = logging.getLogger("kestrel.kyc")


_DIRECT_SANCTIONS_THRESHOLD = 0.7
_RISK_BAND_LOW_MAX = 30
_RISK_BAND_MEDIUM_MAX = 60
_RISK_BAND_HIGH_MAX = 80


@dataclass(slots=True)
class BeneficialOwner:
    full_name: str
    nid: str | None = None
    passport: str | None = None
    date_of_birth: Any = None
    nationality: str | None = None
    ownership_pct: float | None = None


@dataclass(slots=True)
class CustomerOnboardRequest:
    customer_external_id: str
    customer_type: str  # individual | business
    full_name: str
    nid: str | None = None
    passport: str | None = None
    date_of_birth: Any = None
    nationality: str | None = None
    phone: str | None = None
    email: str | None = None
    address: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)
    beneficial_owners: list[BeneficialOwner] = field(default_factory=list)


def _decide_risk(*, score: int, has_direct_hit: bool) -> tuple[str, str]:
    """Map a 0–100 composed score into (risk_level, kyc_status)."""
    if has_direct_hit:
        return "declined", "declined"
    if score < _RISK_BAND_LOW_MAX:
        return "low", "approved"
    if score < _RISK_BAND_MEDIUM_MAX:
        return "medium", "approved"
    if score < _RISK_BAND_HIGH_MAX:
        return "high", "review"
    return "declined", "declined"


def _matches_to_payload(matches: list[ScreeningMatch]) -> list[dict[str, Any]]:
    """Serialise ScreeningMatch rows for storage in screening_results jsonb."""
    return [
        {
            "list_source": m.list_source,
            "list_version": m.list_version,
            "entry_id": m.entry_id,
            "entry_type": m.entry_type,
            "matched_name": m.matched_name,
            "match_score": m.match_score,
            "match_reasons": list(m.match_reasons),
            "matched_aliases": list(m.matched_aliases),
        }
        for m in matches
    ]


def _compose_risk_score(
    *,
    primary_matches: list[ScreeningMatch],
    bo_matches_by_name: dict[str, list[ScreeningMatch]],
) -> int:
    """Customer-level 0–100 score.

    Anchors: a primary-customer hit at >= 0.9 is 95+ on its own. A 0.7-0.9
    primary hit lands 70–80. Each beneficial-owner hit adds a smaller
    contribution (a flagged BO doesn't disqualify the entity, but it
    elevates the risk band).
    """
    score = 0
    if primary_matches:
        top = max(m.match_score for m in primary_matches)
        if top >= 0.9:
            score += 95
        elif top >= 0.8:
            score += 80
        elif top >= _DIRECT_SANCTIONS_THRESHOLD:
            score += 65
        else:
            score += int(top * 50)
    bo_with_hits = sum(1 for matches in bo_matches_by_name.values() if matches)
    if bo_with_hits:
        score += min(30, 10 * bo_with_hits)
    return min(100, score)


async def _screen_one(
    session: AsyncSession,
    *,
    name: str,
    dob: Any,
    nationality: str | None,
    nid: str | None,
    passport: str | None,
) -> list[ScreeningMatch]:
    if not name or not name.strip():
        return []
    return await screen_entity(
        session,
        request=ScreeningRequest(
            name=name,
            date_of_birth=parse_screening_date(dob),
            nationality=nationality,
            nid=nid,
            passport=passport,
            minimum_match_score=_DIRECT_SANCTIONS_THRESHOLD,
        ),
    )


async def _screen_customer_and_owners(
    session: AsyncSession,
    *,
    request: CustomerOnboardRequest,
) -> tuple[list[ScreeningMatch], dict[str, list[ScreeningMatch]]]:
    primary = await _screen_one(
        session,
        name=request.full_name,
        dob=request.date_of_birth,
        nationality=request.nationality,
        nid=request.nid,
        passport=request.passport,
    )
    bo_results: dict[str, list[ScreeningMatch]] = {}
    for bo in request.beneficial_owners:
        bo_results[bo.full_name] = await _screen_one(
            session,
            name=bo.full_name,
            dob=bo.date_of_birth,
            nationality=bo.nationality,
            nid=bo.nid,
            passport=bo.passport,
        )
    return primary, bo_results


def _customer_to_view(customer: Customer) -> dict[str, Any]:
    return {
        "id": str(customer.id),
        "org_id": str(customer.org_id),
        "customer_external_id": customer.customer_external_id,
        "customer_type": customer.customer_type,
        "full_name": customer.full_name,
        "nid": customer.nid,
        "passport": customer.passport,
        "date_of_birth": customer.date_of_birth.isoformat() if customer.date_of_birth else None,
        "nationality": customer.nationality,
        "phone": customer.phone,
        "email": customer.email,
        "address": customer.address or {},
        "metadata": customer.metadata_json or {},
        "beneficial_owners": list(customer.beneficial_owners or []),
        "risk_score": customer.risk_score,
        "risk_level": customer.risk_level,
        "kyc_status": customer.kyc_status,
        "screening_results": customer.screening_results or {},
        "onboarded_at": customer.onboarded_at.isoformat() if customer.onboarded_at else None,
        "reviewed_at": customer.reviewed_at.isoformat() if customer.reviewed_at else None,
        "reviewed_by": str(customer.reviewed_by) if customer.reviewed_by else None,
        "last_rescreened_at": customer.last_rescreened_at.isoformat() if customer.last_rescreened_at else None,
    }


async def onboard_customer(
    session: AsyncSession,
    *,
    user: AuthenticatedUser,
    request: CustomerOnboardRequest,
) -> dict[str, Any]:
    """Create + screen + persist + audit."""
    if (user.org_type or "").lower() == "regulator":
        # Regulators don't onboard customers per V2 spec — banks do.
        raise PermissionError("Regulator-org users cannot onboard customers.")

    primary_matches, bo_matches_by_name = await _screen_customer_and_owners(
        session, request=request
    )
    has_direct_hit = any(m.match_score >= 0.9 for m in primary_matches)
    score = _compose_risk_score(
        primary_matches=primary_matches,
        bo_matches_by_name=bo_matches_by_name,
    )
    risk_level, kyc_status = _decide_risk(score=score, has_direct_hit=has_direct_hit)

    screening_results = {
        "screened_at": datetime.now(UTC).isoformat(),
        "primary": _matches_to_payload(primary_matches),
        "beneficial_owners": {
            name: _matches_to_payload(matches)
            for name, matches in bo_matches_by_name.items()
        },
    }

    customer = Customer(
        id=uuid.uuid4(),
        org_id=uuid.UUID(str(user.org_id)),
        customer_external_id=request.customer_external_id,
        customer_type=request.customer_type,
        full_name=request.full_name,
        nid=request.nid,
        passport=request.passport,
        date_of_birth=parse_screening_date(request.date_of_birth),
        nationality=request.nationality,
        phone=request.phone,
        email=request.email,
        address=request.address or {},
        metadata_json=request.metadata or {},
        beneficial_owners=[
            {
                "full_name": bo.full_name,
                "nid": bo.nid,
                "passport": bo.passport,
                "date_of_birth": bo.date_of_birth.isoformat() if hasattr(bo.date_of_birth, "isoformat") else bo.date_of_birth,
                "nationality": bo.nationality,
                "ownership_pct": bo.ownership_pct,
            }
            for bo in request.beneficial_owners
        ],
        risk_score=score,
        risk_level=risk_level,
        kyc_status=kyc_status,
        screening_results=screening_results,
        last_rescreened_at=datetime.now(UTC),
    )
    session.add(customer)

    session.add(
        AuditLog(
            org_id=uuid.UUID(str(user.org_id)),
            user_id=None,
            action="kyc.onboard",
            resource_type="customer",
            resource_id=customer.id,
            details={
                "customer_external_id": request.customer_external_id,
                "customer_type": request.customer_type,
                "risk_score": score,
                "risk_level": risk_level,
                "kyc_status": kyc_status,
                "primary_match_count": len(primary_matches),
                "beneficial_owner_match_count": sum(
                    len(matches) for matches in bo_matches_by_name.values()
                ),
            },
        )
    )
    await session.flush()
    await session.commit()

    logger.info(
        "kyc.onboard",
        extra={
            "customer_id": str(customer.id),
            "org_id": str(user.org_id),
            "kyc_status": kyc_status,
            "risk_level": risk_level,
            "risk_score": score,
        },
    )
    return _customer_to_view(customer)


async def list_customers(
    session: AsyncSession,
    *,
    user: AuthenticatedUser,
    risk_level: str | None = None,
    kyc_status: str | None = None,
    limit: int = 100,
) -> list[dict[str, Any]]:
    capped = max(1, min(int(limit or 100), 500))
    stmt = select(Customer).order_by(desc(Customer.onboarded_at)).limit(capped)
    if (user.org_type or "").lower() != "regulator":
        stmt = stmt.where(Customer.org_id == uuid.UUID(str(user.org_id)))
    if risk_level:
        stmt = stmt.where(Customer.risk_level == risk_level)
    if kyc_status:
        stmt = stmt.where(Customer.kyc_status == kyc_status)
    result = await session.execute(stmt)
    return [_customer_to_view(c) for c in result.scalars().all()]


async def get_customer(
    session: AsyncSession,
    *,
    user: AuthenticatedUser,
    customer_id: uuid.UUID,
) -> dict[str, Any]:
    customer = await session.get(Customer, customer_id)
    if customer is None:
        raise LookupError(f"Customer {customer_id} not found")
    if (
        str(customer.org_id) != str(user.org_id)
        and (user.org_type or "").lower() != "regulator"
    ):
        raise PermissionError("Cannot read another org's customer.")
    return _customer_to_view(customer)


async def update_customer(
    session: AsyncSession,
    *,
    user: AuthenticatedUser,
    customer_id: uuid.UUID,
    patch: dict[str, Any],
) -> dict[str, Any]:
    customer = await session.get(Customer, customer_id)
    if customer is None:
        raise LookupError(f"Customer {customer_id} not found")
    if str(customer.org_id) != str(user.org_id):
        raise PermissionError("Cannot update another org's customer.")

    safe_fields = {"phone", "email", "address", "metadata", "beneficial_owners"}
    applied: dict[str, Any] = {}
    for key, value in patch.items():
        if key not in safe_fields:
            continue
        if key == "metadata":
            customer.metadata_json = value or {}
        elif key == "address":
            customer.address = value or {}
        elif key == "beneficial_owners":
            customer.beneficial_owners = list(value or [])
        else:
            setattr(customer, key, value)
        applied[key] = value

    session.add(
        AuditLog(
            org_id=uuid.UUID(str(user.org_id)),
            user_id=None,
            action="kyc.update",
            resource_type="customer",
            resource_id=customer.id,
            details={"fields": list(applied.keys())},
        )
    )
    await session.commit()
    return _customer_to_view(customer)


async def review_customer(
    session: AsyncSession,
    *,
    user: AuthenticatedUser,
    customer_id: uuid.UUID,
    decision: str,
    note: str | None = None,
) -> dict[str, Any]:
    """CAMLCO review action — flips kyc_status to approved/declined."""
    if decision not in {"approved", "declined", "review"}:
        raise ValueError(f"Unsupported review decision '{decision}'")
    customer = await session.get(Customer, customer_id)
    if customer is None:
        raise LookupError(f"Customer {customer_id} not found")
    if str(customer.org_id) != str(user.org_id):
        raise PermissionError("Cannot review another org's customer.")

    customer.kyc_status = decision
    customer.reviewed_at = datetime.now(UTC)
    try:
        customer.reviewed_by = uuid.UUID(str(user.user_id))
    except (TypeError, ValueError):
        customer.reviewed_by = None

    session.add(
        AuditLog(
            org_id=uuid.UUID(str(user.org_id)),
            user_id=None,
            action="kyc.review",
            resource_type="customer",
            resource_id=customer.id,
            details={"decision": decision, "note": note} if note else {"decision": decision},
        )
    )
    await session.commit()
    return _customer_to_view(customer)


async def rescreen_customer(
    session: AsyncSession,
    *,
    user: AuthenticatedUser,
    customer_id: uuid.UUID,
) -> dict[str, Any]:
    customer = await session.get(Customer, customer_id)
    if customer is None:
        raise LookupError(f"Customer {customer_id} not found")
    if (
        str(customer.org_id) != str(user.org_id)
        and (user.org_type or "").lower() != "regulator"
    ):
        raise PermissionError("Cannot rescreen another org's customer.")

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
    has_direct_hit = any(m.match_score >= 0.9 for m in primary)
    score = _compose_risk_score(primary_matches=primary, bo_matches_by_name=bo_results)
    risk_level, kyc_status = _decide_risk(score=score, has_direct_hit=has_direct_hit)

    customer.risk_score = score
    customer.risk_level = risk_level
    # Don't auto-flip kyc_status if the customer was previously manually
    # reviewed — let the operator re-review. New automated decline still
    # forces decline.
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

    session.add(
        AuditLog(
            org_id=uuid.UUID(str(user.org_id)),
            user_id=None,
            action="kyc.rescreen",
            resource_type="customer",
            resource_id=customer.id,
            details={
                "risk_score": score,
                "risk_level": risk_level,
                "kyc_status": customer.kyc_status,
                "primary_match_count": len(primary),
            },
        )
    )
    await session.commit()
    return _customer_to_view(customer)
