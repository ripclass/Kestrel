from pathlib import Path

from seed.load_dbbl_synthetic import build_load_plan


def test_load_plan_reads_generated_dataset_counts() -> None:
    dataset_root = Path(__file__).resolve().parents[1] / "seed" / "generated" / "dbbl_synthetic"
    plan = build_load_plan(dataset_root)

    assert plan["statements"] >= 4
    assert plan["entities"] >= 4
    assert plan["transactions"] >= 500
    assert str(dataset_root) == plan["dataset_root"]
