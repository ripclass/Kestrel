"""TBML detection-rule evaluators (Phase B).

Six pure-function evaluators run against ``TradeTransaction``-shaped rows:

  * evaluate_over_invoicing
  * evaluate_under_invoicing
  * evaluate_multiple_invoicing      (cross-org — needs peer_trades)
  * evaluate_phantom_shipment
  * evaluate_declaration_value_mismatch
  * evaluate_transshipment_routing

Each returns ``TradeRuleHit | None``. The ``evaluate_trade_transactions``
helper is the top-level entry point — it loads YAMLs from
``trade_rules/`` and runs every rule against every trade.

No I/O. No DB. No SQLAlchemy required — accepts any object with the
``TradeTransaction`` attribute shape (the prod model, a SimpleNamespace,
or a Pydantic schema).
"""
from __future__ import annotations

import pathlib
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Callable, Iterable

import yaml

RULES_DIR = pathlib.Path(__file__).resolve().parent / "trade_rules"

# Default high-risk jurisdiction list — banks override per their own risk
# appetite. ISO 3166-1 alpha-2 codes.
DEFAULT_HIGH_RISK_JURISDICTIONS: frozenset[str] = frozenset(
    {"IR", "KP", "SY", "VE", "MM", "CU"}
)


@dataclass
class TradeRuleHit:
    """One TBML rule firing against one trade transaction."""

    trade_id: str
    org_id: str
    rule_code: str
    score: int
    weight: float
    severity: str
    reasons: list[dict[str, Any]] = field(default_factory=list)
    evidence: dict[str, Any] = field(default_factory=dict)
    predicate_offences: list[str] = field(default_factory=list)
    bfiu_avenue_ref: str | None = None
    alert_title: str = ""
    alert_description: str = ""


def _as_float(value: Any) -> float:
    if value is None:
        return 0.0
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _attr(trade: Any, name: str, default: Any = None) -> Any:
    return getattr(trade, name, default)


def _trade_id(trade: Any) -> str:
    return str(_attr(trade, "id") or _attr(trade, "trade_ref") or "")


def _org_id(trade: Any) -> str:
    return str(_attr(trade, "org_id") or "")


def _severity_band(score: int, bands: dict[str, int]) -> str:
    if score >= bands.get("critical", 90):
        return "critical"
    if score >= bands.get("high", 70):
        return "high"
    if score >= bands.get("medium", 50):
        return "medium"
    return "low"


def _clamp(score: int) -> int:
    return max(0, min(100, score))


class _SafeFormat(dict):
    def __missing__(self, key: str) -> str:
        return f"{{{key}}}"


def _render(template: str, evidence: dict[str, Any]) -> str:
    try:
        return template.format_map(_SafeFormat(evidence))
    except Exception:
        return template


def _make_hit(
    *,
    trade: Any,
    rule: dict[str, Any],
    score: int,
    reasons: list[dict[str, Any]],
    evidence: dict[str, Any],
) -> TradeRuleHit:
    score = _clamp(score)
    bands = rule.get("severity", {}) or {}
    severity = _severity_band(score, bands)
    title_tpl = (rule.get("alert_template") or {}).get("title", "")
    desc_tpl = (rule.get("alert_template") or {}).get("description", "")
    return TradeRuleHit(
        trade_id=_trade_id(trade),
        org_id=_org_id(trade),
        rule_code=rule["code"],
        score=score,
        weight=float(rule.get("weight", 1.0)),
        severity=severity,
        reasons=reasons,
        evidence=evidence,
        predicate_offences=list(rule.get("predicate_offences", []) or []),
        bfiu_avenue_ref=rule.get("bfiu_avenue_ref"),
        alert_title=_render(title_tpl, evidence),
        alert_description=_render(desc_tpl, evidence),
    )


# Rule implementations -----------------------------------------------------


def evaluate_over_invoicing(
    trade: Any,
    *,
    rule_config: dict[str, Any],
    high_risk_jurisdictions: frozenset[str] = DEFAULT_HIGH_RISK_JURISDICTIONS,
) -> TradeRuleHit | None:
    """Invoice value materially above HS-code market reference."""
    params = rule_config["conditions"]["params"]
    invoice = _as_float(_attr(trade, "invoice_value"))
    market_ref = _as_float(_attr(trade, "market_reference_value"))
    min_ref = float(params.get("min_market_reference", 0))
    min_ratio = float(params.get("min_ratio_to_flag", 1.5))

    if market_ref <= 0 or market_ref < min_ref or invoice <= 0:
        return None
    ratio = invoice / market_ref
    if ratio < min_ratio:
        return None

    score = int(rule_config["scoring"]["base"])
    reasons: list[dict[str, Any]] = []
    if ratio >= 3.0:
        score += 25
        reasons.append(
            {"modifier": "invoice_to_market_ratio >= 3.0", "score_added": 25, "reason": "Invoice value 3x or more above market reference"}
        )
    elif ratio >= 2.0:
        score += 15
        reasons.append(
            {"modifier": "invoice_to_market_ratio >= 2.0", "score_added": 15, "reason": "Invoice value 2x or more above market reference"}
        )

    payment_mode = _attr(trade, "payment_mode")
    if payment_mode in {"open_account", "cash_in_advance"}:
        score += 15
        reasons.append(
            {"modifier": "payment_mode in (open_account, cash_in_advance)", "score_added": 15, "reason": "Open-account / cash-in-advance settlement with inflated invoice"}
        )
    counterparty_country = (_attr(trade, "counterparty_country") or "").upper()
    if counterparty_country in high_risk_jurisdictions:
        score += 10
        reasons.append(
            {"modifier": "counterparty_country in high_risk_jurisdictions", "score_added": 10, "reason": "Counterparty in a high-risk jurisdiction"}
        )
    advising = _attr(trade, "lc_advising_bank")
    cp_bank = _attr(trade, "counterparty_bank")
    if advising and cp_bank and advising != cp_bank:
        score += 5
        reasons.append(
            {"modifier": "lc_advising_bank != counterparty_bank", "score_added": 5, "reason": "LC advising bank differs from counterparty's stated bank"}
        )

    evidence = {
        "trade_ref": _attr(trade, "trade_ref"),
        "hs_code": _attr(trade, "hs_code"),
        "invoice_value": invoice,
        "market_reference_value": market_ref,
        "ratio": round(ratio, 2),
        "currency": _attr(trade, "currency"),
        "counterparty_country": counterparty_country,
    }
    return _make_hit(trade=trade, rule=rule_config, score=score, reasons=reasons, evidence=evidence)


def evaluate_under_invoicing(
    trade: Any,
    *,
    rule_config: dict[str, Any],
    high_risk_jurisdictions: frozenset[str] = DEFAULT_HIGH_RISK_JURISDICTIONS,
    high_duty_hs_codes: frozenset[str] = frozenset(),
) -> TradeRuleHit | None:
    """Invoice value materially below HS-code market reference."""
    params = rule_config["conditions"]["params"]
    invoice = _as_float(_attr(trade, "invoice_value"))
    market_ref = _as_float(_attr(trade, "market_reference_value"))
    min_ref = float(params.get("min_market_reference", 0))
    max_ratio = float(params.get("max_ratio_to_flag", 0.5))

    if market_ref <= 0 or market_ref < min_ref or invoice <= 0:
        return None
    ratio = invoice / market_ref
    if ratio > max_ratio:
        return None

    score = int(rule_config["scoring"]["base"])
    reasons: list[dict[str, Any]] = []
    if ratio <= 0.3:
        score += 25
        reasons.append({"modifier": "invoice_to_market_ratio <= 0.3", "score_added": 25, "reason": "Invoice value 30% or less of market reference"})
    elif ratio <= 0.4:
        score += 15
        reasons.append({"modifier": "invoice_to_market_ratio <= 0.4", "score_added": 15, "reason": "Invoice value 40% or less of market reference"})

    payment_mode = _attr(trade, "payment_mode")
    if payment_mode in {"lc_btb", "lc_red_clause"}:
        score += 15
        reasons.append({"modifier": "payment_mode in (lc_btb, lc_red_clause)", "score_added": 15, "reason": "Back-to-back or red-clause LC structure (high abuse pattern)"})
    counterparty_country = (_attr(trade, "counterparty_country") or "").upper()
    if counterparty_country in high_risk_jurisdictions:
        score += 10
        reasons.append({"modifier": "counterparty_country in high_risk_jurisdictions", "score_added": 10, "reason": "Counterparty in a high-risk jurisdiction"})
    hs_code = _attr(trade, "hs_code") or ""
    if hs_code in high_duty_hs_codes:
        score += 10
        reasons.append({"modifier": "hs_code_high_duty == true", "score_added": 10, "reason": "HS code is high-duty category — under-invoicing evades customs"})

    evidence = {
        "trade_ref": _attr(trade, "trade_ref"),
        "hs_code": hs_code,
        "invoice_value": invoice,
        "market_reference_value": market_ref,
        "ratio": round(ratio, 2),
        "currency": _attr(trade, "currency"),
    }
    return _make_hit(trade=trade, rule=rule_config, score=score, reasons=reasons, evidence=evidence)


def evaluate_phantom_shipment(
    trade: Any,
    *,
    rule_config: dict[str, Any],
    high_risk_jurisdictions: frozenset[str] = DEFAULT_HIGH_RISK_JURISDICTIONS,
    related_party_counterparties: frozenset[str] = frozenset(),
) -> TradeRuleHit | None:
    """Settlement happened but no shipment evidence captured."""
    settlement_amount = _as_float(_attr(trade, "settlement_amount"))
    status = _attr(trade, "status")
    bl = _attr(trade, "bl_number")
    port = _attr(trade, "port_of_loading")
    vessel = _attr(trade, "vessel")

    has_settled = settlement_amount > 0 or status == "settled"
    has_shipment_evidence = bool(bl) or bool(port) or bool(vessel)
    if not has_settled or has_shipment_evidence:
        return None

    score = int(rule_config["scoring"]["base"])
    reasons: list[dict[str, Any]] = []
    if settlement_amount > 5_000_000:
        score += 15
        reasons.append({"modifier": "settlement_amount > 5000000", "score_added": 15, "reason": "Settlement above 50 lakh BDT equivalent with no shipment evidence"})
    payment_mode = _attr(trade, "payment_mode")
    if payment_mode in {"lc_sight", "lc_red_clause"}:
        score += 10
        reasons.append({"modifier": "payment_mode in (lc_sight, lc_red_clause)", "score_added": 10, "reason": "Sight or red-clause LC settled without shipment evidence"})
    counterparty_country = (_attr(trade, "counterparty_country") or "").upper()
    if counterparty_country in high_risk_jurisdictions:
        score += 10
        reasons.append({"modifier": "counterparty_country in high_risk_jurisdictions", "score_added": 10, "reason": "Counterparty in a high-risk jurisdiction"})
    counterparty_name = _attr(trade, "counterparty_name") or ""
    if counterparty_name in related_party_counterparties:
        score += 10
        reasons.append({"modifier": "counterparty_is_related_party == true", "score_added": 10, "reason": "Counterparty is a related party (intra-group transaction)"})

    evidence = {
        "trade_ref": _attr(trade, "trade_ref"),
        "settlement_amount": settlement_amount,
        "currency": _attr(trade, "currency"),
        "counterparty_country": counterparty_country,
    }
    return _make_hit(trade=trade, rule=rule_config, score=score, reasons=reasons, evidence=evidence)


def evaluate_declaration_value_mismatch(
    trade: Any,
    *,
    rule_config: dict[str, Any],
) -> TradeRuleHit | None:
    """Declared (BE/LCAF) value vs invoice value diverges materially."""
    params = rule_config["conditions"]["params"]
    invoice = _as_float(_attr(trade, "invoice_value"))
    declared = _as_float(_attr(trade, "declared_value"))
    if invoice <= 0 or declared <= 0:
        return None
    ratio = declared / invoice
    max_low = float(params.get("max_declared_to_invoice_ratio", 0.7))
    min_high = float(params.get("min_declared_to_invoice_ratio", 1.3))
    if max_low < ratio < min_high:
        return None  # within tolerance band — no signal

    score = int(rule_config["scoring"]["base"])
    reasons: list[dict[str, Any]] = []
    if ratio <= 0.5:
        score += 25
        reasons.append({"modifier": "declared_to_invoice_ratio <= 0.5", "score_added": 25, "reason": "Customs declaration is half or less of LC invoice"})
    if ratio >= 1.5:
        score += 20
        reasons.append({"modifier": "declared_to_invoice_ratio >= 1.5", "score_added": 20, "reason": "Customs declaration is 1.5x or more of LC invoice"})
    if _attr(trade, "be_number") is None:
        score += 15
        reasons.append({"modifier": "be_number == null", "score_added": 15, "reason": "No Bill of Entry recorded against settled trade"})
    payment_mode = _attr(trade, "payment_mode")
    if payment_mode in {"lc_btb", "lc_transferable"}:
        score += 10
        reasons.append({"modifier": "payment_mode in (lc_btb, lc_transferable)", "score_added": 10, "reason": "Back-to-back or transferable LC — abuse-prone structures"})

    evidence = {
        "trade_ref": _attr(trade, "trade_ref"),
        "invoice_value": invoice,
        "declared_value": declared,
        "ratio_pct": round(ratio * 100, 1),
        "currency": _attr(trade, "currency"),
    }
    return _make_hit(trade=trade, rule=rule_config, score=score, reasons=reasons, evidence=evidence)


def evaluate_transshipment_routing(
    trade: Any,
    *,
    rule_config: dict[str, Any],
) -> TradeRuleHit | None:
    """Goods transit through one+ intermediary ports without obvious economic rationale."""
    params = rule_config["conditions"]["params"]
    ports = list(_attr(trade, "transshipment_ports") or [])
    high_risk = {code.upper() for code in (params.get("high_risk_jurisdictions") or [])}
    min_ports = int(params.get("min_transshipment_ports", 2))
    via_high_risk = any(port.upper() in high_risk for port in ports)
    if len(ports) < min_ports and not via_high_risk:
        return None

    score = int(rule_config["scoring"]["base"])
    reasons: list[dict[str, Any]] = []
    if len(ports) >= 3:
        score += 25
        reasons.append({"modifier": "transshipment_port_count >= 3", "score_added": 25, "reason": "Three or more transshipment ports"})
    if via_high_risk:
        score += 30
        reasons.append({"modifier": "transshipment_via_high_risk == true", "score_added": 30, "reason": "Transshipment via high-risk jurisdiction"})
    # LC-declared route check would compare against an LC documents table we
    # don't have yet — treat as soft signal.
    if _attr(trade, "lc_reference") is None and ports:
        score += 15
        reasons.append({"modifier": "lc_route_undeclared == true", "score_added": 15, "reason": "Transshipment not declared in LC at issuance"})
    if _attr(trade, "payment_mode") == "open_account":
        score += 10
        reasons.append({"modifier": "payment_mode == open_account", "score_added": 10, "reason": "Open-account settlement on opaque routing"})

    evidence = {
        "trade_ref": _attr(trade, "trade_ref"),
        "transshipment_chain": " → ".join(ports) if ports else "n/a",
        "transshipment_port_count": len(ports),
        "port_of_loading": _attr(trade, "port_of_loading"),
        "port_of_discharge": _attr(trade, "port_of_discharge"),
    }
    return _make_hit(trade=trade, rule=rule_config, score=score, reasons=reasons, evidence=evidence)


def evaluate_multiple_invoicing(
    trade: Any,
    *,
    rule_config: dict[str, Any],
    peer_trades: Iterable[Any] = (),
) -> TradeRuleHit | None:
    """Same B/L number or LC reference appears across multiple distinct orgs."""
    params = rule_config["conditions"]["params"]
    min_orgs = int(params.get("min_distinct_orgs", 2))
    bl = _attr(trade, "bl_number") or ""
    lc = _attr(trade, "lc_reference") or ""
    if not bl and not lc:
        return None

    same_bl_orgs: set[str] = set()
    same_lc_orgs: set[str] = set()
    aggregate_invoice = _as_float(_attr(trade, "invoice_value"))
    same_bl_orgs.add(_org_id(trade))
    same_lc_orgs.add(_org_id(trade))

    for peer in peer_trades:
        if _trade_id(peer) == _trade_id(trade):
            continue
        peer_bl = _attr(peer, "bl_number") or ""
        peer_lc = _attr(peer, "lc_reference") or ""
        peer_org = _org_id(peer)
        if bl and peer_bl == bl:
            same_bl_orgs.add(peer_org)
            aggregate_invoice += _as_float(_attr(peer, "invoice_value"))
        if lc and peer_lc == lc:
            same_lc_orgs.add(peer_org)

    bl_match = len(same_bl_orgs) >= min_orgs
    lc_match = len(same_lc_orgs) >= min_orgs
    if not bl_match and not lc_match:
        return None

    distinct_orgs = max(len(same_bl_orgs), len(same_lc_orgs))
    score = int(rule_config["scoring"]["base"])
    reasons: list[dict[str, Any]] = []
    if distinct_orgs >= 3:
        score += 20
        reasons.append({"modifier": "distinct_orgs >= 3", "score_added": 20, "reason": "Same B/L or LC reference at three or more banks"})
    if bl_match:
        score += 10
        reasons.append({"modifier": "bl_number_match == true", "score_added": 10, "reason": "B/L number matches across banks"})
    if lc_match:
        score += 10
        reasons.append({"modifier": "lc_reference_match == true", "score_added": 10, "reason": "LC reference matches across banks"})
    if aggregate_invoice > 10_000_000:
        score += 10
        reasons.append({"modifier": "aggregate_invoice_value > 10000000", "score_added": 10, "reason": "Aggregate invoice value across the duplicated shipment exceeds 1 crore BDT equivalent"})

    evidence = {
        "trade_ref": _attr(trade, "trade_ref"),
        "match_key": bl or lc,
        "bl_number": bl or "—",
        "lc_reference": lc or "—",
        "distinct_orgs": distinct_orgs,
        "aggregate_invoice_value": aggregate_invoice,
        "currency": _attr(trade, "currency"),
    }
    return _make_hit(trade=trade, rule=rule_config, score=score, reasons=reasons, evidence=evidence)


# Rule loader + top-level evaluator ---------------------------------------


def load_trade_rules(rules_dir: pathlib.Path = RULES_DIR) -> list[dict[str, Any]]:
    """Load every .yaml file in ``rules_dir`` into a list of rule dicts.

    Sorted by rule ``code`` for deterministic test output.
    """
    rules: list[dict[str, Any]] = []
    for path in sorted(rules_dir.glob("*.yaml")):
        with path.open(encoding="utf-8") as fh:
            data = yaml.safe_load(fh)
        if not isinstance(data, dict):
            raise ValueError(f"Trade rule at {path} is not a YAML mapping")
        if not data.get("code"):
            raise ValueError(f"Trade rule at {path} missing 'code'")
        rules.append(data)
    return rules


_EVALUATOR_BY_TRIGGER: dict[str, Callable[..., TradeRuleHit | None]] = {
    "invoice_to_market_ratio": evaluate_over_invoicing,  # disambiguated by params shape below
    "payment_without_shipment_evidence": evaluate_phantom_shipment,
    "declared_vs_invoice_mismatch": evaluate_declaration_value_mismatch,
    "transshipment_via_jurisdiction": evaluate_transshipment_routing,
    "same_bl_or_lc_across_orgs": evaluate_multiple_invoicing,
}


def evaluate_trade_transactions(
    trades: Iterable[Any],
    *,
    rules: list[dict[str, Any]] | None = None,
    peer_trades_by_ref: dict[str, list[Any]] | None = None,
) -> list[TradeRuleHit]:
    """Run all loaded TBML rules against every trade.

    ``peer_trades_by_ref`` is optional context for cross-org rules
    (multiple_invoicing). Keyed by trade_id; value is the list of trades
    (own + peers) that share a B/L or LC reference with this trade. For
    simple test setups callers can pass ``{trade.id: all_trades}``.
    """
    rule_list = rules if rules is not None else load_trade_rules()
    trade_list = list(trades)
    hits: list[TradeRuleHit] = []
    for trade in trade_list:
        peers = (peer_trades_by_ref or {}).get(_trade_id(trade), trade_list)
        for rule in rule_list:
            code = rule.get("code")
            hit: TradeRuleHit | None = None
            if code == "over_invoicing":
                hit = evaluate_over_invoicing(trade, rule_config=rule)
            elif code == "under_invoicing":
                hit = evaluate_under_invoicing(trade, rule_config=rule)
            elif code == "phantom_shipment":
                hit = evaluate_phantom_shipment(trade, rule_config=rule)
            elif code == "declaration_value_mismatch":
                hit = evaluate_declaration_value_mismatch(trade, rule_config=rule)
            elif code == "transshipment_routing":
                hit = evaluate_transshipment_routing(trade, rule_config=rule)
            elif code == "multiple_invoicing":
                hit = evaluate_multiple_invoicing(trade, rule_config=rule, peer_trades=peers)
            if hit is not None:
                hits.append(hit)
    return hits
