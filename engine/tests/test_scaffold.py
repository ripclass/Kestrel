from pathlib import Path
from types import SimpleNamespace

from app.core.detection.loader import load_rules
from app.core.graph.builder import build_graph
from app.core.graph.export import export_graph
from seed.run import build_seed_summary


def test_rule_catalog_loads_all_seeded_rules() -> None:
    rules_path = Path(__file__).resolve().parents[1] / "app" / "core" / "detection" / "rules"
    rules = load_rules(rules_path)
    assert len(rules) == 8
    assert all(rule.get("code") for rule in rules)


def test_export_graph_returns_expected_shape() -> None:
    entities = [
        SimpleNamespace(
            id="ent-focus",
            entity_type="account",
            display_value="1781430000701",
            display_name="Rizwana Enterprise",
            risk_score=94,
            severity="critical",
        ),
        SimpleNamespace(
            id="ent-phone",
            entity_type="phone",
            display_value="01712XXXXXX",
            display_name="Shared phone",
            risk_score=82,
            severity="high",
        ),
        SimpleNamespace(
            id="ent-wallet",
            entity_type="wallet",
            display_value="01XXXXXXXX",
            display_name="Wallet hub",
            risk_score=88,
            severity="high",
        ),
    ]
    connections = [
        SimpleNamespace(
            id="edge-1",
            from_entity_id="ent-focus",
            to_entity_id="ent-phone",
            relation="shared_phone",
            evidence={},
        ),
        SimpleNamespace(
            id="edge-2",
            from_entity_id="ent-focus",
            to_entity_id="ent-wallet",
            relation="transacted",
            evidence={"amount": 14_000_000},
        ),
    ]

    graph = export_graph(build_graph(entities, connections), "ent-focus")
    assert graph["focus_entity_id"] == "ent-focus"
    assert len(graph["nodes"]) == 3
    assert len(graph["edges"]) == 2
    assert graph["stats"]["suspicious_paths"] >= 1


def test_seed_summary_matches_demo_scale() -> None:
    summary = build_seed_summary()
    assert summary["organizations"] == 7
    assert summary["entities"] >= 200
    assert summary["str_reports"] >= 500
    assert summary["transactions"] >= 100_000
