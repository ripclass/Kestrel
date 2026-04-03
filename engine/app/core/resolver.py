from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import AuthenticatedUser
from app.services.investigation import search_entities


async def resolve_entity(
    session: AsyncSession,
    *,
    user: AuthenticatedUser,
    query: str,
) -> dict[str, object] | None:
    results = await search_entities(session, user=user, query=query, limit=1)
    return results[0] if results else None
