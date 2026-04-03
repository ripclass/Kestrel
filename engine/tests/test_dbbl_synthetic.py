from app.parsers.statement_pdf import classify_statement_channel
from seed.dbbl_synthetic import derive_risk_profile, synthesize_name, synthetic_account_number


def test_channel_classification_covers_primary_bank_statement_patterns() -> None:
    assert classify_statement_channel("RTGS To ZARA ENTERPRISE") == "rtgs"
    assert classify_statement_channel("bKash_Inc/231425224928/23-02-25") == "mfs_bkash"
    assert classify_statement_channel("Fund Transfer through NAGAD") == "mfs_nagad"
    assert classify_statement_channel("CASH WITHDRAWAL BY SELF") == "cash"


def test_synthetic_identity_generation_is_deterministic() -> None:
    account_a = synthetic_account_number("1781430000701")
    account_b = synthetic_account_number("1781430000701")
    name_a = synthesize_name("RIZWANA ENTERPRISE")
    name_b = synthesize_name("RIZWANA ENTERPRISE")

    assert account_a == account_b
    assert name_a == name_b
    assert account_a != "1781430000701"
    assert name_a != "RIZWANA ENTERPRISE"


def test_risk_profile_flags_velocity_and_cashout() -> None:
    transactions = [
        {
            "posted_at": "2026-03-01T09:00:00+00:00",
            "deposit": 1_000_000.0,
            "withdrawal": 0.0,
            "channel": "rtgs",
        },
        {
            "posted_at": "2026-03-01T09:10:00+00:00",
            "deposit": 0.0,
            "withdrawal": 850_000.0,
            "channel": "mfs_bkash",
        },
        {
            "posted_at": "2026-03-01T09:15:00+00:00",
            "deposit": 0.0,
            "withdrawal": 120_000.0,
            "channel": "cash",
        },
    ]

    profile = derive_risk_profile(transactions)

    assert profile["risk_score"] >= 60
    assert "rapid_cashout" in profile["tags"]
    assert any(reason["rule"] == "rapid_cashout" for reason in profile["reasons"])
