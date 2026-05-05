"""Confidence-source helpers (V3 phase 2.2).

Every provider response carries an optional ``confidence`` (0–1).
Adapters fill it in when the upstream API exposes a meaningful signal:

  - **Sovereign** (V3 P4): token log-probs from the local model.
  - **Anthropic / OpenAI** (V3 P2): not exposed in the API surface;
    the orchestrator computes a schema-validity score post-hoc.
  - **Heuristic**: filled inline by the heuristic provider based on
    template completeness.

The schema-validity scorer below is the universal fallback. It runs
against the validated structured output (a Pydantic model instance) and
returns:

  1.0 — every required field is populated AND every optional field that
        carries information has a value.
  0.5 — every required field is populated but optional fields are empty.
  0.0 — schema validation failed (caller short-circuits before this).

The orchestrator uses this only when the provider didn't supply a
confidence — explicit confidences from sovereign + heuristic providers
take precedence.
"""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel


def compute_schema_validity(output: BaseModel) -> float:
    """Score required- + optional-field coverage on a validated Pydantic
    output. Higher = more populated."""
    if output is None:
        return 0.0
    fields = type(output).model_fields
    if not fields:
        return 1.0

    required_total = 0
    required_filled = 0
    optional_total = 0
    optional_filled = 0

    dumped = output.model_dump()
    for name, field_info in fields.items():
        is_required = field_info.is_required()
        value = dumped.get(name)
        is_filled = _has_meaningful_value(value)
        if is_required:
            required_total += 1
            if is_filled:
                required_filled += 1
        else:
            optional_total += 1
            if is_filled:
                optional_filled += 1

    # If validation succeeded but we somehow have an unfilled required
    # field (Pydantic should have rejected this), treat as 0.5 — caller
    # decides what to do with a half-confident response.
    if required_total > 0 and required_filled < required_total:
        return 0.5

    # All required filled. Optional fields lift the score from 0.5 → 1.0.
    if optional_total == 0:
        return 1.0
    optional_share = optional_filled / optional_total
    return round(0.5 + 0.5 * optional_share, 3)


def _has_meaningful_value(value: Any) -> bool:
    """A field is meaningfully filled if it's not None, not an empty
    string, and not an empty container."""
    if value is None:
        return False
    if isinstance(value, str):
        return value.strip() != ""
    if isinstance(value, (list, tuple, set, dict)):
        return len(value) > 0
    return True


def cap_confidence(value: float | None) -> float:
    """Clamp a raw confidence into the [0, 0.95] range.

    Cap at 0.95 because we never claim 100% certainty on a single
    inference — leaves room for the operator to set a 1.0 threshold as
    'never accept' if needed."""
    if value is None:
        return 0.0
    if value < 0.0:
        return 0.0
    if value > 0.95:
        return 0.95
    return float(value)
