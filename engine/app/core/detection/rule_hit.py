"""RuleHit dataclass - the unit of output from detection rule evaluators."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any


@dataclass
class RuleHit:
    """One rule triggering against one account.

    - ``account_id`` is the SQLAlchemy ``Account.id`` (or synthetic test id) the hit
      applies to. The pipeline resolves it to an Entity before alert creation.
    - ``score`` is the raw score including base + applied modifiers, clamped 0..100.
    - ``weight`` is the rule weight from YAML, used by the scorer's weighted average.
    - ``reasons`` is an ordered list of modifier-level contributions:
      ``[{"modifier": str, "score_added": int, "reason": str}, ...]``
    - ``evidence`` is rule-specific context (times, amounts, counts) used for
      alert templating and explainability.
    - ``alert_title`` / ``alert_description`` are rendered from the rule's
      ``alert_template`` using ``evidence`` fields.
    """

    account_id: uuid.UUID | str
    rule_code: str
    score: int
    weight: float
    reasons: list[dict[str, Any]] = field(default_factory=list)
    evidence: dict[str, Any] = field(default_factory=dict)
    alert_title: str = ""
    alert_description: str = ""
