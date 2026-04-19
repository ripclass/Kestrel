"""Tests for the match-definition DSL: parse + evaluate + render."""
from __future__ import annotations

from datetime import datetime, timezone

import pytest

from app.core.match_dsl import (
    MatchDSLError,
    evaluate,
    render_template,
    validate_definition,
)


def _record(**overrides: object) -> dict[str, object]:
    base: dict[str, object] = {
        "entity_type": "account",
        "canonical_value": "1234567890",
        "display_value": "Account 1234567890",
        "display_name": "Acme Holdings",
        "risk_score": 65,
        "severity": "high",
        "confidence": 0.91,
        "status": "active",
        "source": "system",
        "report_count": 3,
        "total_exposure": 4_500_000,
        "tags": ["mfs", "rapid_cashout"],
        "reporting_orgs": ["org-1", "org-2", "org-3"],
        "first_seen": datetime(2026, 1, 1, tzinfo=timezone.utc),
        "last_seen": datetime(2026, 4, 1, tzinfo=timezone.utc),
    }
    base.update(overrides)
    return base


# -------- validation -------------------------------------------------------


def test_validate_minimal_definition() -> None:
    dsl = validate_definition(
        {
            "match": {
                "scope": "entity",
                "where": {"field": "risk_score", "op": ">=", "value": 50},
            }
        }
    )
    assert dsl.scope == "entity"
    assert dsl.where == {"field": "risk_score", "op": ">=", "value": 50}
    # Default alert template
    assert dsl.alert.alert_type == "match_definition"


def test_validate_with_alert_template() -> None:
    dsl = validate_definition(
        {
            "match": {
                "where": {"field": "tags", "op": "contains", "value": "mfs"},
                "alert": {
                    "title": "MFS exposure: {display_value}",
                    "severity": "critical",
                    "risk_score": 88,
                },
            }
        }
    )
    assert dsl.alert.title == "MFS exposure: {display_value}"
    assert dsl.alert.severity == "critical"
    assert dsl.alert.risk_score == 88


def test_validate_rejects_unknown_field() -> None:
    with pytest.raises(MatchDSLError, match="Unknown field"):
        validate_definition(
            {"match": {"where": {"field": "ssn", "op": "==", "value": "x"}}}
        )


def test_validate_rejects_invalid_operator_for_kind() -> None:
    with pytest.raises(MatchDSLError, match="not valid for field"):
        validate_definition(
            {"match": {"where": {"field": "risk_score", "op": "contains", "value": 5}}}
        )


def test_validate_rejects_unsupported_scope() -> None:
    with pytest.raises(MatchDSLError, match="Unsupported scope"):
        validate_definition(
            {
                "match": {
                    "scope": "transaction",
                    "where": {"field": "risk_score", "op": ">=", "value": 1},
                }
            }
        )


def test_validate_rejects_empty_compound() -> None:
    with pytest.raises(MatchDSLError, match="must be a non-empty list"):
        validate_definition({"match": {"where": {"all": []}}})


def test_validate_rejects_too_deep_tree() -> None:
    # Build a depth-12 nested chain.
    node: dict = {"field": "risk_score", "op": ">=", "value": 1}
    for _ in range(12):
        node = {"all": [node]}
    with pytest.raises(MatchDSLError, match="exceeds max depth"):
        validate_definition({"match": {"where": node}})


def test_validate_rejects_in_op_without_list() -> None:
    with pytest.raises(MatchDSLError, match="requires a list"):
        validate_definition(
            {"match": {"where": {"field": "severity", "op": "in", "value": "high"}}}
        )


# -------- evaluation -------------------------------------------------------


def test_eval_numeric_gte_true() -> None:
    dsl = validate_definition(
        {"match": {"where": {"field": "risk_score", "op": ">=", "value": 60}}}
    )
    assert evaluate(_record(), dsl) is True


def test_eval_numeric_gte_false() -> None:
    dsl = validate_definition(
        {"match": {"where": {"field": "risk_score", "op": ">=", "value": 90}}}
    )
    assert evaluate(_record(), dsl) is False


def test_eval_string_in_list() -> None:
    dsl = validate_definition(
        {
            "match": {
                "where": {
                    "field": "severity",
                    "op": "in",
                    "value": ["high", "critical"],
                }
            }
        }
    )
    assert evaluate(_record(), dsl) is True
    assert evaluate(_record(severity="medium"), dsl) is False


def test_eval_string_i_contains() -> None:
    dsl = validate_definition(
        {
            "match": {
                "where": {
                    "field": "display_name",
                    "op": "i_contains",
                    "value": "ACME",
                }
            }
        }
    )
    assert evaluate(_record(), dsl) is True


def test_eval_array_contains_and_size_gte() -> None:
    dsl = validate_definition(
        {
            "match": {
                "where": {
                    "all": [
                        {"field": "tags", "op": "contains", "value": "mfs"},
                        {"field": "reporting_orgs", "op": "size_gte", "value": 2},
                    ]
                }
            }
        }
    )
    assert evaluate(_record(), dsl) is True
    assert evaluate(_record(tags=["other"]), dsl) is False
    assert evaluate(_record(reporting_orgs=["only-one"]), dsl) is False


def test_eval_compound_any_with_not() -> None:
    dsl = validate_definition(
        {
            "match": {
                "where": {
                    "any": [
                        {"field": "risk_score", "op": ">=", "value": 80},
                        {
                            "all": [
                                {"field": "tags", "op": "contains", "value": "mfs"},
                                {
                                    "not": {
                                        "field": "status",
                                        "op": "==",
                                        "value": "closed",
                                    }
                                },
                            ]
                        },
                    ]
                }
            }
        }
    )
    # risk_score=65 fails first arm, second arm: tags contains mfs AND status != closed
    assert evaluate(_record(), dsl) is True
    assert evaluate(_record(status="closed", risk_score=10), dsl) is False


def test_eval_is_null_and_not_empty() -> None:
    dsl = validate_definition(
        {
            "match": {
                "where": {
                    "all": [
                        {"field": "display_name", "op": "not_null"},
                        {"field": "tags", "op": "not_empty"},
                    ]
                }
            }
        }
    )
    assert evaluate(_record(), dsl) is True
    assert evaluate(_record(tags=[]), dsl) is False
    assert evaluate(_record(display_name=None), dsl) is False


# -------- rendering --------------------------------------------------------


def test_render_template_substitutes_known_keys() -> None:
    out = render_template(
        "MFS exposure on {display_value} (risk {risk_score})", _record()
    )
    assert out == "MFS exposure on Account 1234567890 (risk 65)"


def test_render_template_silently_drops_unknown_keys() -> None:
    out = render_template("{display_value} -> {missing}", _record())
    assert out == "Account 1234567890 -> "
