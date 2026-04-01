from seed.fixtures import COMPLIANCE


def get_scorecard() -> list[dict[str, object]]:
    return [item.model_dump() for item in COMPLIANCE]
