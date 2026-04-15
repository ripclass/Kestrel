from pathlib import Path
from typing import Any

import yaml

REQUIRED_TOP_LEVEL_KEYS = {
    "code",
    "title",
    "category",
    "weight",
    "description",
    "conditions",
    "scoring",
    "severity",
    "alert_template",
}


def _validate(rule: dict[str, Any], source: Path) -> None:
    missing = REQUIRED_TOP_LEVEL_KEYS - rule.keys()
    if missing:
        raise ValueError(f"Rule {source.name} is missing required keys: {sorted(missing)}")
    conditions = rule["conditions"]
    if not isinstance(conditions, dict) or "trigger" not in conditions or "params" not in conditions:
        raise ValueError(f"Rule {source.name} conditions must include trigger and params")
    scoring = rule["scoring"]
    if not isinstance(scoring, dict) or "base" not in scoring or "modifiers" not in scoring:
        raise ValueError(f"Rule {source.name} scoring must include base and modifiers")
    severity = rule["severity"]
    if not isinstance(severity, dict) or not {"critical", "high", "medium"}.issubset(severity.keys()):
        raise ValueError(f"Rule {source.name} severity must include critical/high/medium thresholds")
    template = rule["alert_template"]
    if not isinstance(template, dict) or "title" not in template or "description" not in template:
        raise ValueError(f"Rule {source.name} alert_template must include title and description")


def load_rules(rules_path: Path) -> list[dict[str, Any]]:
    """Load all YAML rule definition files under ``rules_path``.

    Returns a list of dicts conforming to the RuleDefinition schema.
    Raises ValueError if any rule file is missing required keys.
    """
    rules: list[dict[str, Any]] = []
    for path in sorted(rules_path.glob("*.yaml")):
        with path.open("r", encoding="utf-8") as handle:
            data = yaml.safe_load(handle)
        if not isinstance(data, dict):
            raise ValueError(f"Rule file {path.name} must contain a YAML mapping")
        _validate(data, path)
        rules.append(data)
    return rules
