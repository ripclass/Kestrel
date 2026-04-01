from difflib import SequenceMatcher

from seed.fixtures import ENTITIES


def resolve_entity(query: str) -> dict[str, object]:
    normalized = query.strip().lower()
    exact = next(
        (
            item.model_dump()
            for item in ENTITIES
            if normalized in {item.display_value.lower(), item.canonical_value.lower()}
        ),
        None,
    )
    if exact:
        return exact

    ranked = sorted(
        ENTITIES,
        key=lambda item: SequenceMatcher(None, normalized, f"{item.display_value} {item.display_name or ''}".lower()).ratio(),
        reverse=True,
    )
    return ranked[0].model_dump()
