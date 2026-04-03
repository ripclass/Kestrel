from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import AuthenticatedUser
from app.services.investigation import list_matches


async def match_entity(
    session: AsyncSession,
    *,
    user: AuthenticatedUser,
    entity_id: str,
) -> list[dict[str, object]]:
    matches = await list_matches(session, user=user)
    return [match for match in matches if match.get("entity_id") == entity_id]
