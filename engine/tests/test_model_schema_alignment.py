from app.models.detection_run import DetectionRun
from app.models.account import Account
from app.models.transaction import Transaction


def test_account_model_does_not_expect_updated_at() -> None:
    assert "updated_at" not in Account.__table__.c
    assert "created_at" in Account.__table__.c


def test_transaction_model_does_not_expect_updated_at() -> None:
    assert "updated_at" not in Transaction.__table__.c
    assert "created_at" in Transaction.__table__.c


def test_detection_run_model_exposes_created_at_and_triggered_by() -> None:
    assert "created_at" in DetectionRun.__table__.c
    assert "triggered_by" in DetectionRun.__table__.c
    assert "updated_at" not in DetectionRun.__table__.c
