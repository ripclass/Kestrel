from seed.fixtures import MATCHES


def match_entity(entity_id: str) -> list[dict[str, object]]:
    return [match.model_dump() for match in MATCHES if match.entity_id == entity_id]
