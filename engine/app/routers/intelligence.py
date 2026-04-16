from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import AuthenticatedUser, get_current_user
from app.dependencies import get_current_session
from app.models.typology import Typology
from app.schemas.intelligence import CrossBankMatch, TypologySummary
from app.schemas.investigate import EntitySearchResult
from app.services.investigation import list_matches, search_entities

router = APIRouter()


@router.get("/entities", response_model=list[EntitySearchResult])
async def entities(
    user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_current_session)],
    query: str = Query(""),
) -> list[EntitySearchResult]:
    items = await search_entities(session, user=user, query=query)
    return [EntitySearchResult.model_validate(item) for item in items]


@router.get("/matches", response_model=list[CrossBankMatch])
async def matches(
    user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_current_session)],
) -> list[CrossBankMatch]:
    items = await list_matches(session, user=user)
    return [CrossBankMatch.model_validate(item) for item in items]


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
