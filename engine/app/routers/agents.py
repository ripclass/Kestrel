"""Agentic AI investigations API (V3 phase 3.2).

Three endpoints, all auth-gated.

    POST /agents/investigate                 -> run + persist + return
    GET  /agents/investigations              -> list (own-org or regulator)
    GET  /agents/investigations/{id}         -> detail
"""
from __future__ import annotations

import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import AuthenticatedUser, get_current_user, require_roles
from app.dependencies import get_current_session
from app.services.agent_investigations import (
    get_investigation,
    list_investigations,
    start_investigation,
)

router = APIRouter()


class InvestigateRequest(BaseModel):
    entity_id: str | None = None
    prompt: str = Field(..., min_length=1, max_length=4000)


class InvestigationView(BaseModel):
    id: str
    org_id: str
    entity_id: str | None = None
    prompt: str
    status: str
    hypothesis: str | None = None
    evidence: list[dict[str, Any]] = Field(default_factory=list)
    suggested_actions: list[str] = Field(default_factory=list)
    confidence: float | None = None
    hops_used: int
    latency_ms: int
    error: str | None = None
    created_at: str | None = None
    completed_at: str | None = None


def _parse_uuid_or_400(raw: str | None) -> uuid.UUID | None:
    if raw is None or raw == "":
        return None
    try:
        return uuid.UUID(raw)
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid UUID") from exc


@router.post("/investigate", response_model=InvestigationView)
async def investigate(
    body: InvestigateRequest,
    user: Annotated[AuthenticatedUser, Depends(require_roles("manager", "admin", "superadmin", "analyst"))],
    session: Annotated[AsyncSession, Depends(get_current_session)],
) -> InvestigationView:
    try:
        payload = await start_investigation(
            session,
            user=user,
            entity_id=_parse_uuid_or_400(body.entity_id),
            prompt=body.prompt,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    return InvestigationView.model_validate(payload)


@router.get("/investigations", response_model=list[InvestigationView])
async def investigations_list(
    user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_current_session)],
    entity_id: str | None = None,
    limit: int = 50,
) -> list[InvestigationView]:
    rows = await list_investigations(
        session,
        user=user,
        entity_id=_parse_uuid_or_400(entity_id),
        limit=limit,
    )
    return [InvestigationView.model_validate(r) for r in rows]


@router.get("/investigations/{investigation_id}", response_model=InvestigationView)
async def investigations_detail(
    investigation_id: str,
    user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_current_session)],
) -> InvestigationView:
    parsed = _parse_uuid_or_400(investigation_id)
    if parsed is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid id")
    try:
        payload = await get_investigation(session, user=user, investigation_id=parsed)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    return InvestigationView.model_validate(payload)
