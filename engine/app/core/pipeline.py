from app.core.alerter import build_alerts
from app.core.matcher import match_entity
from app.core.resolver import resolve_entity


def run_pipeline(query: str) -> dict[str, object]:
    entity = resolve_entity(query)
    matches = match_entity(entity["id"])
    alerts = build_alerts()
    return {
        "entity": entity,
        "matches": matches,
        "alerts": alerts,
    }
