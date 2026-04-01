from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.auth import AuthenticatedUser, get_current_user
from app.schemas.investigate import EntityDossier, EntitySearchResult
from app.services.investigation import get_entity_dossier, search_entities

router = APIRouter()


@router.get("/search", response_model=list[EntitySearchResult])
async def search(
    query: str = Query(default=""),
    user: Annotated[AuthenticatedUser, Depends(get_current_user)] = None,
) -> list[EntitySearchResult]:
    return [EntitySearchResult.model_validate(item) for item in search_entities(query)]


@router.get("/entity/{entity_id}", response_model=EntityDossier)
async def dossier(
    entity_id: str,
    user: Annotated[AuthenticatedUser, Depends(get_current_user)] = None,
) -> EntityDossier:
    return EntityDossier.model_validate(get_entity_dossier(entity_id))
