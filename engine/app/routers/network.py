from typing import Annotated

from fastapi import APIRouter, Depends

from app.auth import AuthenticatedUser, get_current_user
from app.schemas.network import NetworkGraph
from app.services.investigation import get_entity_dossier

router = APIRouter()


@router.get("/entity/{entity_id}", response_model=NetworkGraph)
async def entity_graph(
    entity_id: str,
    user: Annotated[AuthenticatedUser, Depends(get_current_user)] = None,
) -> NetworkGraph:
    dossier = get_entity_dossier(entity_id)
    return NetworkGraph.model_validate(dossier["graph"])
