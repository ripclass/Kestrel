from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import AuthenticatedUser, get_current_user, require_roles
from app.dependencies import get_current_session
from app.models.typology import Typology
from app.schemas.intelligence import CrossBankMatch, TypologySummary
from app.schemas.investigate import EntitySearchResult
from app.schemas.new_subject import NewSubjectRequest, NewSubjectResponse
from app.services.investigation import list_matches, search_entities
from app.services.new_subject import create_subject

router = APIRouter()


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
