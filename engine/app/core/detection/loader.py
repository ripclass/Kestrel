from pathlib import Path

import yaml


def load_rules(rules_path: Path) -> list[dict[str, object]]:
    rules: list[dict[str, object]] = []
    for path in sorted(rules_path.glob("*.yaml")):
        with path.open("r", encoding="utf-8") as handle:
            rules.append(yaml.safe_load(handle))
    return rules
