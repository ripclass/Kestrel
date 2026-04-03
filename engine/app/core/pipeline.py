from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import AuthenticatedUser
from app.core.alerter import build_alerts
from app.core.matcher import match_entity
from app.core.resolver import resolve_entity


async def run_pipeline(
    session: AsyncSession,
    *,
    user: AuthenticatedUser,
    query: str,
) -> dict[str, object]:
    entity = await resolve_entity(session, user=user, query=query)
    matches = await match_entity(session, user=user, entity_id=entity["id"]) if entity else []
    alerts = build_alerts()
    return {
        "entity": entity,
        "matches": matches,
        "alerts": alerts,
    }
