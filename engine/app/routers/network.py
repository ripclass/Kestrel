from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import AuthenticatedUser, get_current_user
from app.dependencies import get_current_session
from app.schemas.network import NetworkGraph
from app.services.investigation import get_network_graph

router = APIRouter()


@router.get("/entity/{entity_id}", response_model=NetworkGraph)
async def entity_graph(
    entity_id: str,
    user: Annotated[AuthenticatedUser, Depends(get_current_user)] = None,
    session: Annotated[AsyncSession, Depends(get_current_session)] = None,
) -> NetworkGraph:
    return NetworkGraph.model_validate(await get_network_graph(session, user=user, entity_id=entity_id))
