from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import AuthenticatedUser, get_current_user
from app.dependencies import get_current_session
from app.schemas.investigate import EntityDossier, EntitySearchResult
from app.services.investigation import get_entity_dossier, search_entities

router = APIRouter()


@router.get("/search", response_model=list[EntitySearchResult])
async def search(
    query: str = Query(default=""),
    user: Annotated[AuthenticatedUser, Depends(get_current_user)] = None,
    session: Annotated[AsyncSession, Depends(get_current_session)] = None,
) -> list[EntitySearchResult]:
    items = await search_entities(session, user=user, query=query)
    return [EntitySearchResult.model_validate(item) for item in items]


@router.get("/entity/{entity_id}", response_model=EntityDossier)
async def dossier(
    entity_id: str,
    user: Annotated[AuthenticatedUser, Depends(get_current_user)] = None,
    session: Annotated[AsyncSession, Depends(get_current_session)] = None,
) -> EntityDossier:
    return EntityDossier.model_validate(await get_entity_dossier(session, user=user, entity_id=entity_id))
