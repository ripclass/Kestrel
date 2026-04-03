from __future__ import annotations

import json
from pathlib import Path


def test_generated_dbbl_dataset_is_present_and_sanitized() -> None:
    root = Path(__file__).resolve().parents[1] / "seed" / "generated" / "dbbl_synthetic"
    summary = json.loads((root / "summary.json").read_text(encoding="utf-8"))
    statements_text = (root / "statements.json").read_text(encoding="utf-8")
    entities_text = (root / "entities.json").read_text(encoding="utf-8")
    transactions_text = (root / "transactions.json").read_text(encoding="utf-8")

    assert summary["counts"]["statements"] >= 4
    assert summary["counts"]["transactions"] >= 500
    assert summary["counts"]["matches"] >= 1

    leaked_values = [
        "RIZWANA ENTERPRISE",
        "1781430000701",
        "STAR SHOES",
        "1494297585001",
        "EMBRYONIC ENTERPRISE",
        "1401805513001",
    ]
    combined = "\n".join([statements_text, entities_text, transactions_text])
    for value in leaked_values:
        assert value not in combined
