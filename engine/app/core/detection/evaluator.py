def evaluate_transactions(transaction_count: int) -> list[dict[str, object]]:
    return [
        {"rule": "rapid_cashout", "score": 75 if transaction_count > 1_000 else 25},
        {"rule": "proximity_to_bad", "score": 55 if transaction_count > 500 else 10},
    ]
