def build_entities(count: int = 240) -> list[dict[str, object]]:
    entities: list[dict[str, object]] = []
    for index in range(count):
        entities.append(
            {
                "id": f"entity-{index:04d}",
                "entity_type": "account" if index % 3 else "phone",
                "display_value": f"178143{index:07d}",
                "display_name": f"Synthetic Entity {index}",
                "risk_score": 30 + (index % 70),
                "severity": "critical" if index % 29 == 0 else "high" if index % 11 == 0 else "medium",
            }
        )
    return entities
