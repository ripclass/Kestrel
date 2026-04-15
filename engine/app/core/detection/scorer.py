"""Risk scorer.

Combines weighted rule hits into a final risk score per account.
"""

from __future__ import annotations

from typing import Any

from app.core.detection.rule_hit import RuleHit


def calculate_risk_score(rule_hits: list[RuleHit]) -> tuple[int, str, list[dict[str, Any]]]:
    """Return ``(score, severity, reasons)`` for a bag of rule hits.

    Formula: weighted average of per-hit scores, clamped to ``[0, 100]``.
    Severity bands: ``>=90`` critical, ``>=70`` high, ``>=50`` medium, else low.
    Reasons are sorted by weighted contribution (highest first) for UI ranking.
    """
    if not rule_hits:
        return 0, "low", []

    weight_sum = sum(hit.weight for hit in rule_hits)
    if weight_sum <= 0:
        return 0, "low", []

    weighted_sum = sum(hit.score * hit.weight for hit in rule_hits)
    score = min(100, int(weighted_sum / weight_sum))

    if score >= 90:
        severity = "critical"
    elif score >= 70:
        severity = "high"
    elif score >= 50:
        severity = "medium"
    else:
        severity = "low"

    reasons: list[dict[str, Any]] = []
    for hit in sorted(rule_hits, key=lambda h: h.score * h.weight, reverse=True):
        reasons.append(
            {
                "rule": hit.rule_code,
                "score": hit.score,
                "weight": hit.weight,
                "weighted_contribution": round(hit.score * hit.weight / weight_sum * 100, 1),
                "reasons": hit.reasons,
                "evidence": hit.evidence,
                "explanation": hit.alert_description,
            }
        )

    return score, severity, reasons
