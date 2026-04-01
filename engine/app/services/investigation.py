from seed.fixtures import ENTITIES, clone_entity_dossier


def search_entities(query: str) -> list[dict[str, object]]:
    normalized = query.strip().lower()
    if not normalized:
        return [item.model_dump() for item in ENTITIES]

    return [
        item.model_dump()
        for item in ENTITIES
        if normalized in f"{item.display_value} {item.display_name or ''} {item.entity_type}".lower()
    ]


def get_entity_dossier(entity_id: str) -> dict[str, object]:
    dossier = clone_entity_dossier()
    if entity_id == dossier.id:
        return dossier.model_dump()
    return dossier.model_dump()
