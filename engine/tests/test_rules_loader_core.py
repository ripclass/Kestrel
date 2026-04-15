from pathlib import Path

import pytest

from app.core.detection.loader import load_rules

RULES_PATH = Path(__file__).resolve().parents[1] / "app" / "core" / "detection" / "rules"

EXPECTED_CODES = {
    "rapid_cashout",
    "fan_in_burst",
    "fan_out_burst",
    "dormant_spike",
    "layering",
    "proximity_to_bad",
    "structuring",
    "first_time_high_value",
}


def test_loader_returns_all_eight_rules() -> None:
    rules = load_rules(RULES_PATH)
    assert len(rules) == 8
    assert {rule["code"] for rule in rules} == EXPECTED_CODES


@pytest.mark.parametrize("code", sorted(EXPECTED_CODES))
def test_each_rule_has_full_schema(code: str) -> None:
    rules = {rule["code"]: rule for rule in load_rules(RULES_PATH)}
    rule = rules[code]

    assert isinstance(rule["title"], str) and rule["title"]
    assert isinstance(rule["category"], str) and rule["category"]
    assert isinstance(rule["weight"], (int, float)) and rule["weight"] > 0
    assert isinstance(rule["description"], str) and rule["description"].strip()

    conditions = rule["conditions"]
    assert isinstance(conditions["trigger"], str) and conditions["trigger"]
    assert isinstance(conditions["params"], dict)

    scoring = rule["scoring"]
    assert isinstance(scoring["base"], int) and 0 < scoring["base"] <= 100
    assert isinstance(scoring["modifiers"], list)
    for mod in scoring["modifiers"]:
        assert isinstance(mod["when"], str) and mod["when"]
        assert isinstance(mod["add"], int) and mod["add"] > 0
        assert isinstance(mod["reason"], str) and mod["reason"]

    severity = rule["severity"]
    assert severity["critical"] >= severity["high"] >= severity["medium"]

    template = rule["alert_template"]
    assert "{" in template["title"]
    assert "{" in template["description"]
