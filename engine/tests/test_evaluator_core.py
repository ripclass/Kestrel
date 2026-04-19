import uuid
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import networkx as nx
import pytest

from app.core.detection.evaluator import (
    _group_transactions_by_account,
    evaluate_accounts,
    evaluate_dormant_spike,
    evaluate_fan_in_burst,
    evaluate_fan_out_burst,
    evaluate_first_time_high_value,
    evaluate_layering,
    evaluate_proximity_to_bad,
    evaluate_rapid_cashout,
    evaluate_structuring,
)
from app.core.detection.rule_hit import RuleHit

NOW = datetime(2026, 4, 15, 12, 0, 0, tzinfo=UTC)


def make_txn(
    *,
    src: uuid.UUID | None,
    dst: uuid.UUID | None,
    amount: float,
    posted_at: datetime,
    channel: str = "NPSB",
    tx_type: str = "transfer",
) -> SimpleNamespace:
    return SimpleNamespace(
        id=uuid.uuid4(),
        src_account_id=src,
        dst_account_id=dst,
        amount=amount,
        posted_at=posted_at,
        channel=channel,
        tx_type=tx_type,
        currency="BDT",
        metadata_json={},
    )


def make_account(
    account_id: uuid.UUID,
    *,
    name: str,
    bank_code: str = "DBBL",
    age_days: int = 365,
) -> SimpleNamespace:
    return SimpleNamespace(
        id=account_id,
        account_number=f"ACC{str(account_id)[:8]}",
        account_name=name,
        bank_code=bank_code,
        created_at=NOW - timedelta(days=age_days),
        metadata_json={},
    )


def test_group_transactions_by_account_includes_src_and_dst() -> None:
    a = uuid.uuid4()
    b = uuid.uuid4()
    c = uuid.uuid4()
    txns = [
        make_txn(src=a, dst=b, amount=100, posted_at=NOW),
        make_txn(src=b, dst=c, amount=50, posted_at=NOW),
    ]
    grouped = _group_transactions_by_account(txns)
    assert set(grouped.keys()) == {a, b, c}
    assert len(grouped[a]) == 1
    assert len(grouped[b]) == 2
    assert len(grouped[c]) == 1


RAPID_CASHOUT_CONFIG = {
    "code": "rapid_cashout",
    "title": "Rapid cash-out",
    "weight": 8.0,
    "conditions": {
        "trigger": "credit_then_debit_percentage",
        "params": {
            "debit_pct_min": 80,
            "time_window_minutes": 60,
            "min_credit_amount": 50_000,
        },
    },
    "scoring": {
        "base": 60,
        "modifiers": [
            {"when": "time_gap_minutes < 30", "add": 20, "reason": "Under 30 minutes"},
            {"when": "total_credit > 1000000", "add": 15, "reason": "Credit over 10 lakh"},
            {"when": "account_age_days < 90", "add": 10, "reason": "New account"},
            {"when": "cross_bank_debit == true", "add": 10, "reason": "Cross-bank exit"},
        ],
    },
    "severity": {"critical": 90, "high": 70, "medium": 50},
    "alert_template": {
        "title": "Rapid cash-out: {account_name}",
        "description": "{debit_pct}% of BDT {credit_amount} debited within {time_gap} minutes",
    },
}


def test_rapid_cashout_triggers_on_large_credit_then_fast_debit() -> None:
    account_id = uuid.uuid4()
    other_id = uuid.uuid4()
    account = make_account(account_id, name="Mule One", age_days=45)
    txns = [
        make_txn(src=other_id, dst=account_id, amount=1_500_000, posted_at=NOW),
        make_txn(src=account_id, dst=uuid.uuid4(), amount=700_000, posted_at=NOW + timedelta(minutes=5)),
        make_txn(src=account_id, dst=uuid.uuid4(), amount=725_000, posted_at=NOW + timedelta(minutes=18)),
    ]
    hit = evaluate_rapid_cashout(account=account, account_txns=txns, rule_config=RAPID_CASHOUT_CONFIG)
    assert hit is not None
    assert hit.rule_code == "rapid_cashout"
    assert hit.score == 100  # 60 base + 20 + 15 + 10 = 105, clamped
    assert hit.weight == 8.0
    assert "Mule One" in hit.alert_title
    assert any("Under 30 minutes" in r["reason"] for r in hit.reasons)


def test_rapid_cashout_no_trigger_when_debit_too_slow() -> None:
    account_id = uuid.uuid4()
    account = make_account(account_id, name="Normal", age_days=500)
    txns = [
        make_txn(src=uuid.uuid4(), dst=account_id, amount=1_000_000, posted_at=NOW),
        make_txn(src=account_id, dst=uuid.uuid4(), amount=900_000, posted_at=NOW + timedelta(hours=5)),
    ]
    hit = evaluate_rapid_cashout(account=account, account_txns=txns, rule_config=RAPID_CASHOUT_CONFIG)
    assert hit is None


def test_rapid_cashout_no_trigger_when_credit_too_small() -> None:
    account_id = uuid.uuid4()
    account = make_account(account_id, name="Small", age_days=500)
    txns = [
        make_txn(src=uuid.uuid4(), dst=account_id, amount=20_000, posted_at=NOW),
        make_txn(src=account_id, dst=uuid.uuid4(), amount=18_000, posted_at=NOW + timedelta(minutes=10)),
    ]
    hit = evaluate_rapid_cashout(account=account, account_txns=txns, rule_config=RAPID_CASHOUT_CONFIG)
    assert hit is None


FAN_IN_CONFIG = {
    "code": "fan_in_burst",
    "title": "Fan-in burst",
    "weight": 6.0,
    "conditions": {
        "trigger": "unique_senders_to_recipient",
        "params": {
            "min_unique_senders": 5,
            "time_window_minutes": 30,
            "min_total_amount": 100_000,
        },
    },
    "scoring": {
        "base": 55,
        "modifiers": [
            {"when": "unique_senders > 10", "add": 15, "reason": "More than 10 senders"},
            {"when": "total_amount > 2000000", "add": 10, "reason": "Over 20 lakh"},
            {"when": "all_similar_amounts == true", "add": 10, "reason": "Similar amounts"},
        ],
    },
    "severity": {"critical": 90, "high": 70, "medium": 50},
    "alert_template": {
        "title": "Fan-in: {account_name}",
        "description": "{unique_senders} senders -> BDT {total_amount}",
    },
}


def test_fan_in_burst_triggers_on_many_unique_senders() -> None:
    recipient = uuid.uuid4()
    account = make_account(recipient, name="Pool", age_days=200)
    txns = [
        make_txn(src=uuid.uuid4(), dst=recipient, amount=50_000, posted_at=NOW + timedelta(minutes=i))
        for i in range(6)
    ]
    hit = evaluate_fan_in_burst(account=account, account_txns=txns, rule_config=FAN_IN_CONFIG)
    assert hit is not None
    assert hit.evidence["unique_senders"] == 6


def test_fan_in_burst_no_trigger_under_threshold() -> None:
    recipient = uuid.uuid4()
    account = make_account(recipient, name="Low", age_days=200)
    txns = [
        make_txn(src=uuid.uuid4(), dst=recipient, amount=50_000, posted_at=NOW + timedelta(minutes=i))
        for i in range(3)
    ]
    hit = evaluate_fan_in_burst(account=account, account_txns=txns, rule_config=FAN_IN_CONFIG)
    assert hit is None


FAN_OUT_CONFIG = {
    "code": "fan_out_burst",
    "title": "Fan-out burst",
    "weight": 6.0,
    "conditions": {
        "trigger": "unique_recipients_from_sender",
        "params": {
            "min_unique_recipients": 5,
            "time_window_minutes": 30,
            "min_total_amount": 100_000,
        },
    },
    "scoring": {
        "base": 50,
        "modifiers": [
            {"when": "unique_recipients > 8", "add": 15, "reason": "More than 8 recipients"},
            {"when": "total_amount > 2000000", "add": 10, "reason": "Over 20 lakh"},
            {"when": "all_similar_amounts == true", "add": 10, "reason": "Similar amounts"},
        ],
    },
    "severity": {"critical": 90, "high": 70, "medium": 50},
    "alert_template": {
        "title": "Fan-out: {account_name}",
        "description": "{unique_recipients} recipients <- BDT {total_amount}",
    },
}


def test_fan_out_burst_triggers_on_many_unique_recipients() -> None:
    sender = uuid.uuid4()
    account = make_account(sender, name="Distributor", age_days=200)
    txns = [
        make_txn(src=sender, dst=uuid.uuid4(), amount=60_000, posted_at=NOW + timedelta(minutes=i))
        for i in range(6)
    ]
    hit = evaluate_fan_out_burst(account=account, account_txns=txns, rule_config=FAN_OUT_CONFIG)
    assert hit is not None
    assert hit.evidence["unique_recipients"] == 6


STRUCTURING_CONFIG = {
    "code": "structuring",
    "title": "Structuring",
    "weight": 5.0,
    "conditions": {
        "trigger": "sub_threshold_clustering",
        "params": {
            "threshold_amount": 1_000_000,
            "margin_pct": 5,
            "min_count": 3,
            "time_window_hours": 24,
        },
    },
    "scoring": {
        "base": 45,
        "modifiers": [
            {"when": "count > 5", "add": 15, "reason": "More than 5 txns"},
            {"when": "same_channel == true", "add": 10, "reason": "Same channel"},
            {"when": "amounts_tightly_clustered == true", "add": 10, "reason": "Tight cluster"},
        ],
    },
    "severity": {"critical": 90, "high": 70, "medium": 50},
    "alert_template": {
        "title": "Structuring: {account_name}",
        "description": "{count} txns avg BDT {avg_amount}",
    },
}


def test_structuring_triggers_on_sub_threshold_cluster() -> None:
    account_id = uuid.uuid4()
    account = make_account(account_id, name="Structurer")
    txns = [
        make_txn(src=account_id, dst=uuid.uuid4(), amount=970_000, posted_at=NOW + timedelta(hours=i), channel="NPSB")
        for i in range(4)
    ]
    hit = evaluate_structuring(account=account, account_txns=txns, rule_config=STRUCTURING_CONFIG)
    assert hit is not None
    assert hit.evidence["count"] == 4


LAYERING_CONFIG = {
    "code": "layering",
    "title": "Layering",
    "weight": 7.0,
    "conditions": {
        "trigger": "structured_similar_transfers",
        "params": {
            "min_transfer_count": 5,
            "amount_variance_pct": 10,
            "time_window_hours": 48,
            "min_total_amount": 200_000,
        },
    },
    "scoring": {
        "base": 55,
        "modifiers": [
            {"when": "transfer_count > 10", "add": 15, "reason": "Over 10 transfers"},
            {"when": "amount_variance_pct < 5", "add": 10, "reason": "Tight variance"},
        ],
    },
    "severity": {"critical": 90, "high": 70, "medium": 50},
    "alert_template": {
        "title": "Layering: {account_name}",
        "description": "{transfer_count} transfers avg BDT {avg_amount}",
    },
}


def test_layering_triggers_on_similar_clustered_transfers() -> None:
    account_id = uuid.uuid4()
    account = make_account(account_id, name="Layer")
    txns = [
        make_txn(src=account_id, dst=uuid.uuid4(), amount=200_000 + (i * 100), posted_at=NOW + timedelta(hours=i))
        for i in range(6)
    ]
    hit = evaluate_layering(account=account, account_txns=txns, rule_config=LAYERING_CONFIG)
    assert hit is not None
    assert hit.evidence["transfer_count"] == 6


FIRST_TIME_CONFIG = {
    "code": "first_time_high_value",
    "title": "First-time high value",
    "weight": 4.0,
    "conditions": {
        "trigger": "new_beneficiary_high_value",
        "params": {
            "min_amount": 500_000,
            "max_account_age_days": 90,
            "no_prior_transactions_to_beneficiary": True,
        },
    },
    "scoring": {
        "base": 50,
        "modifiers": [
            {"when": "amount > 1000000", "add": 20, "reason": "Over 10 lakh"},
            {"when": "account_age_days < 30", "add": 10, "reason": "Very new"},
        ],
    },
    "severity": {"critical": 90, "high": 70, "medium": 50},
    "alert_template": {
        "title": "First-time high value: {account_name}",
        "description": "BDT {amount} -> {beneficiary_name} (age {account_age})",
    },
}


def test_first_time_high_value_triggers_for_new_sender_large_amount() -> None:
    account_id = uuid.uuid4()
    account = make_account(account_id, name="NewBie", age_days=20)
    txns = [
        make_txn(src=account_id, dst=uuid.uuid4(), amount=1_500_000, posted_at=NOW),
    ]
    hit = evaluate_first_time_high_value(account=account, account_txns=txns, rule_config=FIRST_TIME_CONFIG)
    assert hit is not None
    assert hit.score >= 50 + 20 + 10


DORMANT_CONFIG = {
    "code": "dormant_spike",
    "title": "Dormant spike",
    "weight": 5.0,
    "conditions": {
        "trigger": "balance_spike_after_dormancy",
        "params": {
            "dormant_days": 30,
            "max_prior_balance": 10_000,
            "min_spike_amount": 5_000_000,
        },
    },
    "scoring": {
        "base": 65,
        "modifiers": [
            {"when": "spike_amount > 10000000", "add": 15, "reason": "Over 1 crore"},
            {"when": "dormant_days > 90", "add": 10, "reason": "Long dormancy"},
        ],
    },
    "severity": {"critical": 90, "high": 70, "medium": 50},
    "alert_template": {
        "title": "Dormant spike: {account_name}",
        "description": "BDT {spike_amount} after {dormant_days}d",
    },
}


def test_dormant_spike_triggers_on_large_credit_after_dormancy() -> None:
    account_id = uuid.uuid4()
    account = make_account(account_id, name="Dormie")
    txns = [
        make_txn(src=uuid.uuid4(), dst=account_id, amount=1_000, posted_at=NOW - timedelta(days=120)),
        make_txn(src=uuid.uuid4(), dst=account_id, amount=12_000_000, posted_at=NOW),
    ]
    hit = evaluate_dormant_spike(account=account, account_txns=txns, rule_config=DORMANT_CONFIG)
    assert hit is not None
    assert hit.score >= 65 + 15 + 10


PROXIMITY_CONFIG = {
    "code": "proximity_to_bad",
    "title": "Proximity",
    "weight": 5.0,
    "conditions": {
        "trigger": "graph_proximity",
        "params": {"max_hops": 2, "target_entity_status": ["active", "confirmed"], "min_target_confidence": 0.6},
    },
    "scoring": {
        "base": 40,
        "modifiers": [
            {"when": "hop_distance == 1", "add": 25, "reason": "Direct link"},
            {"when": "multiple_flagged_neighbors == true", "add": 15, "reason": "Multiple"},
        ],
    },
    "severity": {"critical": 90, "high": 70, "medium": 50},
    "alert_template": {
        "title": "Proximity: {account_name}",
        "description": "{hop_distance} hops from {flagged_entity_name}",
    },
}


def test_proximity_fires_when_account_directly_connects_to_flagged() -> None:
    account_id = uuid.uuid4()
    account_entity_id = str(uuid.uuid4())
    flagged_entity_id = str(uuid.uuid4())

    account = make_account(account_id, name="ProxAcct")
    account.metadata_json = {"entity_id": account_entity_id}

    graph = nx.DiGraph()
    graph.add_node(account_entity_id, type="account", label="ProxAcct", risk_score=10, severity="low")
    graph.add_node(flagged_entity_id, type="account", label="Bad Guy", risk_score=95, severity="critical")
    graph.add_edge(account_entity_id, flagged_entity_id, relation="transacted")

    hit = evaluate_proximity_to_bad(
        account=account,
        account_txns=[],
        rule_config=PROXIMITY_CONFIG,
        graph=graph,
        flagged_entity_ids={flagged_entity_id},
    )
    assert hit is not None
    assert hit.evidence["hop_distance"] == 1
    assert hit.score >= 40 + 25


ALL_RULES = [
    RAPID_CASHOUT_CONFIG,
    FAN_IN_CONFIG,
    FAN_OUT_CONFIG,
    STRUCTURING_CONFIG,
    LAYERING_CONFIG,
    FIRST_TIME_CONFIG,
    DORMANT_CONFIG,
    PROXIMITY_CONFIG,
]


def test_evaluate_accounts_returns_hits_across_multiple_rules() -> None:
    account_id = uuid.uuid4()
    other = uuid.uuid4()
    account = make_account(account_id, name="MultiHit", age_days=30)
    txns = [
        make_txn(src=other, dst=account_id, amount=2_000_000, posted_at=NOW),
        make_txn(src=account_id, dst=uuid.uuid4(), amount=1_900_000, posted_at=NOW + timedelta(minutes=10)),
    ]
    hits = evaluate_accounts(
        accounts=[account],
        transactions=txns,
        rules=ALL_RULES,
    )
    assert any(h.rule_code == "rapid_cashout" for h in hits)
    assert all(isinstance(h, RuleHit) for h in hits)


# --- Graph-aware modifier coverage ---------------------------------------

RAPID_CASHOUT_WITH_PROXIMITY_CONFIG = {
    **RAPID_CASHOUT_CONFIG,
    "scoring": {
        "base": 60,
        "modifiers": [
            *RAPID_CASHOUT_CONFIG["scoring"]["modifiers"],
            {
                "when": "proximity_to_flagged <= 2",
                "add": 15,
                "reason": "Within 2 hops of flagged entity",
            },
        ],
    },
}


def _rapid_cashout_txns(
    account_id: uuid.UUID,
) -> list[SimpleNamespace]:
    return [
        make_txn(src=uuid.uuid4(), dst=account_id, amount=200_000, posted_at=NOW),
        make_txn(
            src=account_id,
            dst=uuid.uuid4(),
            amount=180_000,
            posted_at=NOW + timedelta(minutes=10),
        ),
    ]


def test_rapid_cashout_proximity_modifier_fires_within_two_hops() -> None:
    account_id = uuid.uuid4()
    account_entity = str(uuid.uuid4())
    intermediate_entity = str(uuid.uuid4())
    flagged_entity = str(uuid.uuid4())

    account = make_account(account_id, name="MuleProx", age_days=400)
    account.metadata_json = {"entity_id": account_entity}

    graph = nx.DiGraph()
    graph.add_node(account_entity, label="Mule")
    graph.add_node(intermediate_entity, label="Hop")
    graph.add_node(flagged_entity, label="Bad", risk_score=95)
    graph.add_edge(account_entity, intermediate_entity, relation="transacted")
    graph.add_edge(intermediate_entity, flagged_entity, relation="transacted")

    hit_with_graph = evaluate_rapid_cashout(
        account=account,
        account_txns=_rapid_cashout_txns(account_id),
        rule_config=RAPID_CASHOUT_WITH_PROXIMITY_CONFIG,
        graph=graph,
        flagged_entity_ids={flagged_entity},
    )
    hit_without = evaluate_rapid_cashout(
        account=account,
        account_txns=_rapid_cashout_txns(account_id),
        rule_config=RAPID_CASHOUT_WITH_PROXIMITY_CONFIG,
    )
    assert hit_with_graph is not None and hit_without is not None
    # Same base + cross-bank-debit context, the graph-aware run is +15 over baseline.
    assert hit_with_graph.score == hit_without.score + 15
    assert any(
        r["modifier"] == "proximity_to_flagged <= 2" for r in hit_with_graph.reasons
    )


def test_rapid_cashout_proximity_modifier_does_not_fire_beyond_max_hops() -> None:
    account_id = uuid.uuid4()
    account_entity = str(uuid.uuid4())
    far_flagged_entity = str(uuid.uuid4())

    account = make_account(account_id, name="MuleFar", age_days=400)
    account.metadata_json = {"entity_id": account_entity}

    graph = nx.DiGraph()
    graph.add_node(account_entity, label="Mule")
    # Build a chain of 3 intermediates so the flagged target is 4 hops away.
    prev = account_entity
    for _ in range(3):
        nxt = str(uuid.uuid4())
        graph.add_node(nxt, label="hop")
        graph.add_edge(prev, nxt, relation="transacted")
        prev = nxt
    graph.add_node(far_flagged_entity, label="Bad", risk_score=95)
    graph.add_edge(prev, far_flagged_entity, relation="transacted")

    hit = evaluate_rapid_cashout(
        account=account,
        account_txns=_rapid_cashout_txns(account_id),
        rule_config=RAPID_CASHOUT_WITH_PROXIMITY_CONFIG,
        graph=graph,
        flagged_entity_ids={far_flagged_entity},
    )
    assert hit is not None
    assert not any(
        r["modifier"] == "proximity_to_flagged <= 2" for r in hit.reasons
    )


LAYERING_WITH_GRAPH_CONFIG = {
    **LAYERING_CONFIG,
    "scoring": {
        "base": 55,
        "modifiers": [
            {"when": "transfer_count > 10", "add": 15, "reason": "Over 10 transfers"},
            {
                "when": "involves_multiple_banks == true",
                "add": 10,
                "reason": "Spans multiple banks",
            },
            {"when": "amount_variance_pct < 5", "add": 10, "reason": "Tight variance"},
            {
                "when": "circular_flow_detected == true",
                "add": 15,
                "reason": "Circular flow detected",
            },
        ],
    },
}


def test_layering_involves_multiple_banks_modifier_fires_with_cross_bank_recipients() -> None:
    account_id = uuid.uuid4()
    account = make_account(account_id, name="LayerCross", bank_code="DBBL")
    recipient_ids = [uuid.uuid4() for _ in range(6)]
    accounts_by_id = {account_id: account}
    # Half the recipients sit at a different bank.
    for i, rid in enumerate(recipient_ids):
        bank = "BRAC" if i % 2 == 0 else "DBBL"
        accounts_by_id[rid] = make_account(rid, name=f"R{i}", bank_code=bank)
    txns = [
        make_txn(src=account_id, dst=rid, amount=200_000, posted_at=NOW + timedelta(hours=i))
        for i, rid in enumerate(recipient_ids)
    ]

    hit_with = evaluate_layering(
        account=account,
        account_txns=txns,
        rule_config=LAYERING_WITH_GRAPH_CONFIG,
        accounts_by_id=accounts_by_id,
    )
    # Same shape but no accounts_by_id => can't see cross-bank recipients.
    hit_without = evaluate_layering(
        account=account,
        account_txns=txns,
        rule_config=LAYERING_WITH_GRAPH_CONFIG,
    )
    assert hit_with is not None and hit_without is not None
    assert hit_with.score == hit_without.score + 10
    assert any(
        r["modifier"] == "involves_multiple_banks == true" for r in hit_with.reasons
    )


def test_layering_circular_flow_modifier_fires_when_entity_in_cycle() -> None:
    account_id = uuid.uuid4()
    account_entity = str(uuid.uuid4())
    other_entity = str(uuid.uuid4())
    account = make_account(account_id, name="LayerLoop")
    account.metadata_json = {"entity_id": account_entity}

    graph = nx.DiGraph()
    graph.add_node(account_entity, label="Loop")
    graph.add_node(other_entity, label="Hop")
    graph.add_edge(account_entity, other_entity, relation="transacted")
    graph.add_edge(other_entity, account_entity, relation="transacted")

    txns = [
        make_txn(src=account_id, dst=uuid.uuid4(), amount=200_000, posted_at=NOW + timedelta(hours=i))
        for i in range(6)
    ]

    hit_with = evaluate_layering(
        account=account,
        account_txns=txns,
        rule_config=LAYERING_WITH_GRAPH_CONFIG,
        graph=graph,
    )
    # Acyclic graph: cycle modifier must not fire.
    acyclic = nx.DiGraph()
    acyclic.add_node(account_entity, label="Loop")
    acyclic.add_node(other_entity, label="Hop")
    acyclic.add_edge(account_entity, other_entity, relation="transacted")
    hit_acyclic = evaluate_layering(
        account=account,
        account_txns=txns,
        rule_config=LAYERING_WITH_GRAPH_CONFIG,
        graph=acyclic,
    )

    assert hit_with is not None and hit_acyclic is not None
    assert hit_with.score == hit_acyclic.score + 15
    assert any(
        r["modifier"] == "circular_flow_detected == true" for r in hit_with.reasons
    )


PROXIMITY_WITH_CONFIDENCE_CONFIG = {
    **PROXIMITY_CONFIG,
    "scoring": {
        "base": 40,
        "modifiers": [
            {"when": "hop_distance == 1", "add": 25, "reason": "Direct link"},
            {
                "when": "target_confidence > 0.8",
                "add": 10,
                "reason": "High-confidence target",
            },
            {"when": "multiple_flagged_neighbors == true", "add": 15, "reason": "Multiple"},
        ],
    },
}


def test_proximity_target_confidence_modifier_fires_for_high_risk_target() -> None:
    account_id = uuid.uuid4()
    account_entity = str(uuid.uuid4())
    high_risk_target = str(uuid.uuid4())

    account = make_account(account_id, name="ProxHigh")
    account.metadata_json = {"entity_id": account_entity}

    graph = nx.DiGraph()
    graph.add_node(account_entity, label="acct", risk_score=10)
    graph.add_node(high_risk_target, label="Bad", risk_score=95)
    graph.add_edge(account_entity, high_risk_target, relation="transacted")

    hit = evaluate_proximity_to_bad(
        account=account,
        account_txns=[],
        rule_config=PROXIMITY_WITH_CONFIDENCE_CONFIG,
        graph=graph,
        flagged_entity_ids={high_risk_target},
    )
    assert hit is not None
    assert any(r["modifier"] == "target_confidence > 0.8" for r in hit.reasons)
    assert hit.evidence["confidence"] == "0.95"


def test_proximity_target_confidence_modifier_silent_for_borderline_target() -> None:
    account_id = uuid.uuid4()
    account_entity = str(uuid.uuid4())
    borderline_target = str(uuid.uuid4())

    account = make_account(account_id, name="ProxBorder")
    account.metadata_json = {"entity_id": account_entity}

    graph = nx.DiGraph()
    graph.add_node(account_entity, label="acct", risk_score=10)
    graph.add_node(borderline_target, label="Mid", risk_score=70)
    graph.add_edge(account_entity, borderline_target, relation="transacted")

    hit = evaluate_proximity_to_bad(
        account=account,
        account_txns=[],
        rule_config=PROXIMITY_WITH_CONFIDENCE_CONFIG,
        graph=graph,
        flagged_entity_ids={borderline_target},
    )
    assert hit is not None
    assert not any(
        r["modifier"] == "target_confidence > 0.8" for r in hit.reasons
    )
    assert hit.evidence["confidence"] == "0.70"


def test_evaluate_accounts_threads_graph_into_rapid_cashout_and_layering() -> None:
    """Dispatcher must hand graph + flagged_entity_ids to the right evaluators."""
    account_id = uuid.uuid4()
    account_entity = str(uuid.uuid4())
    flagged_entity = str(uuid.uuid4())
    account = make_account(account_id, name="Dispatcher", age_days=400)
    account.metadata_json = {"entity_id": account_entity}

    graph = nx.DiGraph()
    graph.add_node(account_entity, label="acct")
    graph.add_node(flagged_entity, label="Bad", risk_score=95)
    graph.add_edge(account_entity, flagged_entity, relation="transacted")

    txns = _rapid_cashout_txns(account_id)
    hits = evaluate_accounts(
        accounts=[account],
        transactions=txns,
        rules=[RAPID_CASHOUT_WITH_PROXIMITY_CONFIG],
        graph=graph,
        flagged_entity_ids={flagged_entity},
    )
    rapid = next(h for h in hits if h.rule_code == "rapid_cashout")
    assert any(
        r["modifier"] == "proximity_to_flagged <= 2" for r in rapid.reasons
    )
