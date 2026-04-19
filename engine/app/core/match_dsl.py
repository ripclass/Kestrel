"""Match-definition DSL.

A safe, declarative JSON DSL for analyst-defined entity matching rules.
The shape::

    {
      "match": {
        "scope": "entity",
        "where": <condition-node>,
        "alert": {
          "title": "Custom match: {display_value}",
          "description": "...",
          "severity": "high",
          "risk_score": 75,
          "alert_type": "match_definition"
        }
      }
    }

A condition node is one of:

- Leaf:   ``{"field": "<name>", "op": "<op>", "value": <literal>}``
- ``and``: ``{"all": [<node>, ...]}``
- ``or``:  ``{"any": [<node>, ...]}``
- ``not``: ``{"not": <node>}``

Operators are whitelisted (see ``_OPS``). Fields are whitelisted to a
fixed list of Entity columns (see ``_ENTITY_FIELDS``). The DSL never
evaluates strings as Python; the executor only ever does dictionary
lookups and the ops table.

``validate_definition`` raises ``MatchDSLError`` with a human-readable
message on any structural problem so the executor can persist a clean
``execution_status='failed'`` row instead of crashing.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

_MAX_DEPTH = 8
_MAX_NODES = 100

_ENTITY_FIELDS: dict[str, str] = {
    # field name -> kind ("number" | "string" | "array" | "datetime")
    "entity_type": "string",
    "canonical_value": "string",
    "display_value": "string",
    "display_name": "string",
    "risk_score": "number",
    "severity": "string",
    "confidence": "number",
    "status": "string",
    "source": "string",
    "report_count": "number",
    "total_exposure": "number",
    "tags": "array",
    "reporting_orgs": "array",
    "first_seen": "datetime",
    "last_seen": "datetime",
}

_OPS_BY_KIND: dict[str, set[str]] = {
    "number": {"==", "!=", ">", ">=", "<", "<=", "in", "not_in", "is_null", "not_null"},
    "string": {
        "==",
        "!=",
        "in",
        "not_in",
        "contains",
        "i_contains",
        "starts_with",
        "ends_with",
        "is_null",
        "not_null",
    },
    "array": {"contains", "size_gte", "size_lte", "is_empty", "not_empty"},
    "datetime": {"is_null", "not_null"},
}


class MatchDSLError(ValueError):
    """Raised when a definition fails structural validation."""


@dataclass(frozen=True)
class AlertTemplate:
    title: str = "Custom match: {display_value}"
    description: str | None = None
    severity: str | None = None
    risk_score: int | None = None
    alert_type: str = "match_definition"


@dataclass(frozen=True)
class MatchDefinitionDSL:
    scope: str
    where: dict[str, Any]
    alert: AlertTemplate


def _check_depth_and_count(node: Any, depth: int, counter: list[int]) -> None:
    if depth > _MAX_DEPTH:
        raise MatchDSLError(f"Condition tree exceeds max depth {_MAX_DEPTH}")
    counter[0] += 1
    if counter[0] > _MAX_NODES:
        raise MatchDSLError(f"Condition tree exceeds max node count {_MAX_NODES}")
    if not isinstance(node, dict):
        raise MatchDSLError(f"Condition node must be an object, got {type(node).__name__}")
    if "all" in node:
        children = node["all"]
        if not isinstance(children, list) or not children:
            raise MatchDSLError("`all` must be a non-empty list of conditions")
        for child in children:
            _check_depth_and_count(child, depth + 1, counter)
        return
    if "any" in node:
        children = node["any"]
        if not isinstance(children, list) or not children:
            raise MatchDSLError("`any` must be a non-empty list of conditions")
        for child in children:
            _check_depth_and_count(child, depth + 1, counter)
        return
    if "not" in node:
        _check_depth_and_count(node["not"], depth + 1, counter)
        return
    # Leaf
    field = node.get("field")
    op = node.get("op")
    if field not in _ENTITY_FIELDS:
        raise MatchDSLError(
            f"Unknown field {field!r}; allowed: {sorted(_ENTITY_FIELDS)}"
        )
    kind = _ENTITY_FIELDS[field]
    if op not in _OPS_BY_KIND.get(kind, set()):
        raise MatchDSLError(
            f"Operator {op!r} is not valid for field {field!r} (kind={kind}); "
            f"allowed: {sorted(_OPS_BY_KIND.get(kind, set()))}"
        )
    # Value shape sanity for ops that demand a list.
    if op in {"in", "not_in"}:
        if not isinstance(node.get("value"), list):
            raise MatchDSLError(f"Operator {op!r} requires a list value")
    if op in {"is_null", "not_null", "is_empty", "not_empty"}:
        # No value expected.
        pass


def validate_definition(definition: dict[str, Any]) -> MatchDefinitionDSL:
    if not isinstance(definition, dict):
        raise MatchDSLError("Definition must be a JSON object")
    match = definition.get("match")
    if not isinstance(match, dict):
        raise MatchDSLError("Definition is missing top-level `match` object")
    scope = match.get("scope", "entity")
    if scope != "entity":
        raise MatchDSLError(f"Unsupported scope {scope!r}; only `entity` is implemented in v1")
    where = match.get("where")
    if not isinstance(where, dict):
        raise MatchDSLError("`match.where` must be a condition object")

    counter = [0]
    _check_depth_and_count(where, depth=1, counter=counter)

    alert_data = match.get("alert") or {}
    if not isinstance(alert_data, dict):
        raise MatchDSLError("`match.alert` must be an object if provided")
    alert = AlertTemplate(
        title=str(alert_data.get("title") or AlertTemplate.title),
        description=alert_data.get("description"),
        severity=alert_data.get("severity"),
        risk_score=alert_data.get("risk_score"),
        alert_type=str(alert_data.get("alert_type") or AlertTemplate.alert_type),
    )

    return MatchDefinitionDSL(scope=scope, where=where, alert=alert)


# ---------------------------------------------------------------- evaluation


def _coerce_number(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _eval_leaf(node: dict[str, Any], record: dict[str, Any]) -> bool:
    field = node["field"]
    op = node["op"]
    field_value = record.get(field)

    if op == "is_null":
        return field_value is None
    if op == "not_null":
        return field_value is not None
    if op == "is_empty":
        return not field_value
    if op == "not_empty":
        return bool(field_value)

    target = node.get("value")

    kind = _ENTITY_FIELDS[field]
    if kind == "number":
        lhs = _coerce_number(field_value)
        if op in {"in", "not_in"}:
            members = {_coerce_number(v) for v in target}
            inside = lhs in members
            return inside if op == "in" else not inside
        if lhs is None:
            return False
        rhs = _coerce_number(target)
        if rhs is None:
            return False
        return _NUMERIC_OPS[op](lhs, rhs)
    if kind == "string":
        lhs = "" if field_value is None else str(field_value)
        if op == "==":
            return lhs == str(target)
        if op == "!=":
            return lhs != str(target)
        if op == "in":
            return lhs in {str(v) for v in target}
        if op == "not_in":
            return lhs not in {str(v) for v in target}
        if op == "contains":
            return str(target) in lhs
        if op == "i_contains":
            return str(target).casefold() in lhs.casefold()
        if op == "starts_with":
            return lhs.startswith(str(target))
        if op == "ends_with":
            return lhs.endswith(str(target))
    if kind == "array":
        items = list(field_value or [])
        if op == "contains":
            return target in items or str(target) in {str(x) for x in items}
        if op == "size_gte":
            n = _coerce_number(target)
            return n is not None and len(items) >= int(n)
        if op == "size_lte":
            n = _coerce_number(target)
            return n is not None and len(items) <= int(n)
    return False


_NUMERIC_OPS = {
    "==": lambda a, b: a == b,
    "!=": lambda a, b: a != b,
    ">": lambda a, b: a > b,
    ">=": lambda a, b: a >= b,
    "<": lambda a, b: a < b,
    "<=": lambda a, b: a <= b,
}


def _eval_node(node: dict[str, Any], record: dict[str, Any]) -> bool:
    if "all" in node:
        return all(_eval_node(child, record) for child in node["all"])
    if "any" in node:
        return any(_eval_node(child, record) for child in node["any"])
    if "not" in node:
        return not _eval_node(node["not"], record)
    return _eval_leaf(node, record)


def evaluate(record: dict[str, Any], dsl: MatchDefinitionDSL) -> bool:
    """Evaluate the DSL against a record dict (typically an Entity dict)."""
    return _eval_node(dsl.where, record)


# ---------------------------------------------------------------- rendering


class _DefaultDict(dict):
    def __missing__(self, key: str) -> str:
        return ""


def render_template(template: str, record: dict[str, Any]) -> str:
    try:
        return template.format_map(_DefaultDict(record))
    except Exception:
        return template
