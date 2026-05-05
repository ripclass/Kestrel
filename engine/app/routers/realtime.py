"""Real-time transaction-scoring API (V2 Phase 3.1).

Banks integrate their core-banking systems against this surface for
sub-500ms decisioning. Three endpoints:

    POST   /transactions/score              -> score one transaction
    POST   /transactions/score/{id}/feedback -> bank reports the truth label
    GET    /transactions/score/recent        -> live stream for the dashboard

All three require Supabase JWT auth. Bank persona sees its own org only;
regulator persona sees the cross-system stream.
"""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import AuthenticatedUser, get_current_user, require_roles
from app.dependencies import get_current_session
from app.schemas.realtime import (
    RealtimeFeedbackRequest,
    RealtimeFeedbackResponse,
    RealtimeMetricsResponse,
    RealtimeRecentRow,
    RealtimeScoreRequest,
    RealtimeScoreResponse,
    channel_is_supported,
)
from app.services.billing import require_feature
from app.services.metering import gate_then_increment
from app.services.realtime_scoring import (
    RealtimeScoringRequest,
    build_realtime_metrics,
    list_recent_scores,
    record_feedback,
    score_transaction,
)

router = APIRouter()


@router.post("/score", response_model=RealtimeScoreResponse)
async def score(
    body: RealtimeScoreRequest,
    user: Annotated[AuthenticatedUser, Depends(require_roles("manager", "admin", "superadmin", "analyst"))],
    session: Annotated[AsyncSession, Depends(get_current_session)],
) -> RealtimeScoreResponse:
    if not channel_is_supported(body.channel):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Unsupported channel '{body.channel}'.",
        )
    try:
        await require_feature(session, user=user, feature="realtime")
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_402_PAYMENT_REQUIRED, detail=str(exc)) from exc
    try:
        await gate_then_increment(session, user=user)
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_402_PAYMENT_REQUIRED, detail=str(exc)) from exc
    request = RealtimeScoringRequest(
        transaction_id=body.transaction_id,
        from_account=body.from_account,
        to_account=body.to_account,
        amount=float(body.amount),
        channel=body.channel.upper(),
        transaction_type=body.transaction_type,
        currency=body.currency,
        from_account_metadata=body.from_account_metadata,
        to_account_metadata=body.to_account_metadata,
        timestamp=body.timestamp,
    )
    result = await score_transaction(session, user=user, request=request)
    return RealtimeScoreResponse(
        log_id=result.log_id,
        score=result.score,
        decision=result.decision,
        confidence=result.confidence,
        reasons=result.reasons,
        evidence=result.evidence,
        cross_bank_flag=result.cross_bank_flag,
        request_id=result.request_id,
        latency_ms=result.latency_ms,
    )


@router.post("/score/{log_id}/feedback", response_model=RealtimeFeedbackResponse)
async def feedback(
    log_id: str,
    body: RealtimeFeedbackRequest,
    user: Annotated[AuthenticatedUser, Depends(require_roles("manager", "admin", "superadmin", "analyst"))],
    session: Annotated[AsyncSession, Depends(get_current_session)],
) -> RealtimeFeedbackResponse:
    try:
        parsed_id = uuid.UUID(log_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid log id") from exc
    try:
        payload = await record_feedback(
            session,
            user=user,
            log_id=parsed_id,
            outcome=body.outcome,
            note=body.note,
        )
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    return RealtimeFeedbackResponse.model_validate(payload)


@router.get("/score/recent", response_model=list[RealtimeRecentRow])
async def recent(
    user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_current_session)],
    limit: int = 50,
) -> list[RealtimeRecentRow]:
    capped = max(1, min(int(limit or 50), 200))
    rows = await list_recent_scores(session, user=user, limit=capped)
    return [RealtimeRecentRow.model_validate(row) for row in rows]


@router.get("/score/metrics", response_model=RealtimeMetricsResponse)
async def metrics(
    user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_current_session)],
    window_hours: int = 24,
    top_limit: int = 5,
) -> RealtimeMetricsResponse:
    payload = await build_realtime_metrics(
        session,
        user=user,
        window_hours=window_hours,
        top_limit=top_limit,
    )
    return RealtimeMetricsResponse.model_validate(payload)
