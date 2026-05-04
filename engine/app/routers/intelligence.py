from io import BytesIO
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import AuthenticatedUser, get_current_user, require_roles
from app.dependencies import get_current_session
from app.models.typology import Typology
from app.schemas.intelligence import (
    CrossBankEntityRow,
    CrossBankHeatmap,
    CrossBankMatch,
    CrossBankMatchView,
    CrossBankSummary,
    TypologySummary,
)
from app.schemas.investigate import EntitySearchResult
from app.schemas.new_subject import NewSubjectRequest, NewSubjectResponse
from app.services.cross_bank import (
    cross_bank_heatmap,
    list_cross_bank_matches,
    list_recent_cross_bank_entities,
    summarize_cross_bank,
)
from app.services.investigation import list_matches, search_entities
from app.services.new_subject import create_subject
from app.services.xlsx_export import build_entities_xlsx

router = APIRouter()


@router.get("/entities/export.xlsx")
async def export_entities_xlsx(
    user: Annotated[AuthenticatedUser, Depends(require_roles("analyst", "manager", "admin", "superadmin"))],
    session: Annotated[AsyncSession, Depends(get_current_session)],
    query: str = Query(""),
) -> StreamingResponse:
    items = await search_entities(session, user=user, query=query)
    rows: list[dict[str, object]] = []
    for entity in items:
        rows.append({
            "id": entity.get("id"),
            "entity_type": entity.get("entity_type"),
            "display_value": entity.get("display_value"),
            "display_name": entity.get("display_name"),
            "risk_score": entity.get("risk_score"),
            "severity": entity.get("severity"),
            "report_count": entity.get("report_count"),
            "reporting_orgs_count": len(entity.get("reporting_orgs", []) or []),
            "total_exposure": entity.get("total_exposure"),
            "status": entity.get("status"),
        })
    payload = build_entities_xlsx(rows)
    return StreamingResponse(
        BytesIO(payload),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": 'attachment; filename="kestrel-entities.xlsx"'},
    )


@router.get("/entities", response_model=list[EntitySearchResult])
async def entities(
    user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_current_session)],
    query: str = Query(""),
) -> list[EntitySearchResult]:
    items = await search_entities(session, user=user, query=query)
    return [EntitySearchResult.model_validate(item) for item in items]


@router.post("/entities", response_model=NewSubjectResponse)
async def create_new_subject(
    body: NewSubjectRequest,
    request: Request,
    user: Annotated[AuthenticatedUser, Depends(require_roles("analyst", "manager", "admin", "superadmin"))],
    session: Annotated[AsyncSession, Depends(get_current_session)],
) -> NewSubjectResponse:
    return await create_subject(
        session,
        user=user,
        payload=body,
        ip=request.client.host if request.client else None,
    )


@router.get("/matches", response_model=list[CrossBankMatch])
async def matches(
    user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_current_session)],
) -> list[CrossBankMatch]:
    items = await list_matches(session, user=user)
    return [CrossBankMatch.model_validate(item) for item in items]


@router.get("/cross-bank/summary", response_model=CrossBankSummary)
async def cross_bank_summary_endpoint(
    user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_current_session)],
    window_days: int = Query(30, ge=1, le=365),
) -> CrossBankSummary:
    payload = await summarize_cross_bank(session, user=user, window_days=window_days)
    return CrossBankSummary.model_validate(payload)


@router.get("/cross-bank/matches", response_model=list[CrossBankMatchView])
async def cross_bank_matches_endpoint(
    user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_current_session)],
    window_days: int = Query(30, ge=1, le=365),
    severity: str | None = Query(None),
    min_banks: int = Query(2, ge=2, le=10),
    limit: int = Query(50, ge=1, le=200),
) -> list[CrossBankMatchView]:
    items = await list_cross_bank_matches(
        session,
        user=user,
        window_days=window_days,
        severity=severity,
        min_banks=min_banks,
        limit=limit,
    )
    return [CrossBankMatchView.model_validate(item) for item in items]


@router.get("/cross-bank/heatmap", response_model=CrossBankHeatmap)
async def cross_bank_heatmap_endpoint(
    user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_current_session)],
    window_days: int = Query(30, ge=1, le=365),
) -> CrossBankHeatmap:
    payload = await cross_bank_heatmap(session, user=user, window_days=window_days)
    return CrossBankHeatmap.model_validate(payload)


@router.get("/cross-bank/top-entities", response_model=list[CrossBankEntityRow])
async def cross_bank_top_entities_endpoint(
    user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_current_session)],
    window_days: int = Query(30, ge=1, le=365),
    limit: int = Query(12, ge=1, le=50),
) -> list[CrossBankEntityRow]:
    items = await list_recent_cross_bank_entities(
        session, user=user, window_days=window_days, limit=limit
    )
    return [CrossBankEntityRow.model_validate(item) for item in items]


@router.get("/typologies", response_model=list[TypologySummary])
async def typologies(
    user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_current_session)],
) -> list[TypologySummary]:
    result = await session.execute(select(Typology).order_by(Typology.title))
    rows = result.scalars().all()
    return [
        TypologySummary(
            id=row.id,
            title=row.title,
            category=row.category,
            channels=list(row.channels or []),
            indicators=list(row.indicators or []),
            narrative=row.narrative,
        )
        for row in rows
    ]
