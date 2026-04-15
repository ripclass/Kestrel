import uuid

from app.core.detection.rule_hit import RuleHit
from app.core.detection.scorer import calculate_risk_score


def hit(rule: str, score: int, weight: float) -> RuleHit:
    return RuleHit(
        account_id=uuid.uuid4(),
        rule_code=rule,
        score=score,
        weight=weight,
        reasons=[],
        evidence={},
        alert_title=f"{rule} alert",
        alert_description=f"{rule} fired",
    )


def test_empty_hits_returns_low() -> None:
    score, severity, reasons = calculate_risk_score([])
    assert score == 0
    assert severity == "low"
    assert reasons == []


def test_weighted_average_with_two_rules() -> None:
    hits = [hit("rapid_cashout", 90, 8.0), hit("proximity_to_bad", 50, 5.0)]
    score, severity, reasons = calculate_risk_score(hits)

    # (90*8 + 50*5) / 13 = 970/13 = 74.6 -> 74
    assert score == 74
    assert severity == "high"
    assert reasons[0]["rule"] == "rapid_cashout"
    assert reasons[0]["weighted_contribution"] > reasons[1]["weighted_contribution"]
    # Contributions are percentages of the total weighted score and sum to ~100.
    total = sum(r["weighted_contribution"] for r in reasons)
    assert 99.5 <= total <= 100.5
    assert all(0 <= r["weighted_contribution"] <= 100 for r in reasons)


def test_single_hit_is_full_contribution() -> None:
    _, _, reasons = calculate_risk_score([hit("layering", 80, 7.0)])
    assert reasons[0]["weighted_contribution"] == 100.0


def test_score_clamped_at_100() -> None:
    hits = [hit("rapid_cashout", 200, 1.0)]
    score, severity, _ = calculate_risk_score(hits)
    assert score == 100
    assert severity == "critical"


def test_critical_at_90() -> None:
    hits = [hit("layering", 95, 7.0)]
    score, severity, _ = calculate_risk_score(hits)
    assert severity == "critical"
