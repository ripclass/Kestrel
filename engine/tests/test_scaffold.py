from pathlib import Path

from app.core.detection.loader import load_rules
from app.core.graph.export import export_graph
from seed.fixtures import ALERTS
from seed.run import build_seed_summary


def test_rule_catalog_loads_all_seeded_rules() -> None:
    rules_path = Path(__file__).resolve().parents[1] / "app" / "core" / "detection" / "rules"
    rules = load_rules(rules_path)
    assert len(rules) == 8
    assert all(rule.get("code") for rule in rules)


def test_export_graph_returns_expected_shape() -> None:
    graph = export_graph()
    assert graph["focus_entity_id"] == "ent-rizwana-account"
    assert len(graph["nodes"]) >= 5
    assert len(graph["edges"]) >= 6
    assert graph["stats"]["suspicious_paths"] >= 1


def test_seed_summary_matches_demo_scale() -> None:
    summary = build_seed_summary()
    assert summary["organizations"] == 7
    assert summary["entities"] >= 200
    assert summary["str_reports"] >= 500
    assert summary["transactions"] >= 100_000


def test_alert_fixture_includes_explainability() -> None:
    reasons = ALERTS[0].reasons
    assert len(reasons) >= 2
    assert all(reason.rule for reason in reasons)
    assert all(reason.explanation for reason in reasons)
