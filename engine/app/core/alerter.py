from seed.fixtures import ALERTS


def build_alerts() -> list[dict[str, object]]:
    return [alert.model_dump() for alert in ALERTS]
