from typing import Annotated

from fastapi import APIRouter, Depends

from app.auth import AuthenticatedUser, get_current_user
from app.schemas.intelligence import CrossBankMatch, TypologySummary
from app.schemas.investigate import EntitySearchResult
from seed.fixtures import ENTITIES, MATCHES, TYPOLOGIES

router = APIRouter()


@router.get("/entities", response_model=list[EntitySearchResult])
async def entities(user: Annotated[AuthenticatedUser, Depends(get_current_user)]) -> list[EntitySearchResult]:
    return ENTITIES


@router.get("/matches", response_model=list[CrossBankMatch])
async def matches(user: Annotated[AuthenticatedUser, Depends(get_current_user)]) -> list[CrossBankMatch]:
    return MATCHES


@router.get("/typologies", response_model=list[TypologySummary])
async def typologies(user: Annotated[AuthenticatedUser, Depends(get_current_user)]) -> list[TypologySummary]:
    return TYPOLOGIES
