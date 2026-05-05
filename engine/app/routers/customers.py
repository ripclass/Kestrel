"""KYC / CDD customer-onboarding API (V2 phase 5).

Six endpoints (mounted at /customers):

    POST   /                        -> onboard + screen + return decision
    GET    /                        -> list with filters
    GET    /{id}                    -> detail
    PATCH  /{id}                    -> safe-field update
    POST   /{id}/review             -> CAMLCO review action
    POST   /{id}/rescreen           -> re-run sanctions screening

Auth: Supabase JWT. Bank persona owns onboarding (regulator persona
cannot create customers — it's not their workflow). The list / detail /
rescreen paths allow regulator-persona reads for oversight.
"""
from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import AuthenticatedUser, get_current_user, require_roles
from app.dependencies import get_current_session
from app.schemas.customer import (
    CustomerOnboardInput,
    CustomerPatchInput,
    CustomerReviewInput,
    CustomerView,
)
from app.services.kyc import (
    BeneficialOwner,
    CustomerOnboardRequest,
    get_customer,
    list_customers,
    onboard_customer,
    rescreen_customer,
    review_customer,
    update_customer,
)

router = APIRouter()


def _parse_id(raw: str) -> uuid.UUID:
    try:
        return uuid.UUID(raw)
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid customer id") from exc


@router.post("", response_model=CustomerView)
async def onboard(
    body: CustomerOnboardInput,
    user: Annotated[AuthenticatedUser, Depends(require_roles("manager", "admin", "superadmin", "analyst"))],
    session: Annotated[AsyncSession, Depends(get_current_session)],
) -> CustomerView:
    request = CustomerOnboardRequest(
        customer_external_id=body.customer_external_id,
        customer_type=body.customer_type,
        full_name=body.full_name,
        nid=body.nid,
        passport=body.passport,
        date_of_birth=body.date_of_birth,
        nationality=body.nationality,
        phone=body.phone,
        email=body.email,
        address=body.address or {},
        metadata=body.metadata or {},
        beneficial_owners=[
            BeneficialOwner(
                full_name=bo.full_name,
                nid=bo.nid,
                passport=bo.passport,
                date_of_birth=bo.date_of_birth,
                nationality=bo.nationality,
                ownership_pct=bo.ownership_pct,
            )
            for bo in (body.beneficial_owners or [])
        ],
    )
    try:
        payload = await onboard_customer(session, user=user, request=request)
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    return CustomerView.model_validate(payload)


@router.get("", response_model=list[CustomerView])
async def list_all(
    user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_current_session)],
    risk_level: str | None = None,
    kyc_status: str | None = None,
    limit: int = 100,
) -> list[CustomerView]:
    rows = await list_customers(
        session,
        user=user,
        risk_level=risk_level,
        kyc_status=kyc_status,
        limit=limit,
    )
    return [CustomerView.model_validate(row) for row in rows]


@router.get("/{customer_id}", response_model=CustomerView)
async def detail(
    customer_id: str,
    user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_current_session)],
) -> CustomerView:
    try:
        payload = await get_customer(session, user=user, customer_id=_parse_id(customer_id))
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    return CustomerView.model_validate(payload)


@router.patch("/{customer_id}", response_model=CustomerView)
async def patch(
    customer_id: str,
    body: CustomerPatchInput,
    user: Annotated[AuthenticatedUser, Depends(require_roles("manager", "admin", "superadmin"))],
    session: Annotated[AsyncSession, Depends(get_current_session)],
) -> CustomerView:
    patch_dict = body.model_dump(exclude_unset=True, exclude_none=True)
    if "beneficial_owners" in patch_dict and patch_dict["beneficial_owners"] is not None:
        patch_dict["beneficial_owners"] = [
            bo.model_dump() if hasattr(bo, "model_dump") else bo
            for bo in patch_dict["beneficial_owners"]
        ]
    try:
        payload = await update_customer(
            session, user=user, customer_id=_parse_id(customer_id), patch=patch_dict
        )
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    return CustomerView.model_validate(payload)


@router.post("/{customer_id}/review", response_model=CustomerView)
async def review(
    customer_id: str,
    body: CustomerReviewInput,
    user: Annotated[AuthenticatedUser, Depends(require_roles("manager", "admin", "superadmin"))],
    session: Annotated[AsyncSession, Depends(get_current_session)],
) -> CustomerView:
    try:
        payload = await review_customer(
            session,
            user=user,
            customer_id=_parse_id(customer_id),
            decision=body.decision,
            note=body.note,
        )
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    return CustomerView.model_validate(payload)


@router.post("/{customer_id}/rescreen", response_model=CustomerView)
async def rescreen(
    customer_id: str,
    user: Annotated[AuthenticatedUser, Depends(require_roles("manager", "admin", "superadmin", "analyst"))],
    session: Annotated[AsyncSession, Depends(get_current_session)],
) -> CustomerView:
    try:
        payload = await rescreen_customer(
            session, user=user, customer_id=_parse_id(customer_id)
        )
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    return CustomerView.model_validate(payload)
