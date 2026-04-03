import asyncio

import pytest
from fastapi import HTTPException

from app.auth import AuthenticatedUser
from app.routers import admin as admin_router
from seed.dbbl_synthetic import OUTPUT_DIR_DEFAULT


def build_user(**overrides) -> AuthenticatedUser:
    payload = {
        "user_id": "00000000-0000-0000-0000-000000000123",
        "email": "director@kestrel-bfiu.test",
        "org_id": "9c111111-1111-4111-8111-111111111111",
        "org_type": "regulator",
        "role": "admin",
        "persona": "bfiu_director",
        "designation": "Director, BFIU",
    }
    payload.update(overrides)
    return AuthenticatedUser(**payload)


def test_synthetic_backfill_plan_is_regulator_only() -> None:
    with pytest.raises(HTTPException) as exc:
        admin_router._require_regulator_admin(build_user(org_type="bank"))

    assert exc.value.status_code == 403


def test_synthetic_backfill_plan_reads_default_dataset() -> None:
    plan = asyncio.run(admin_router.synthetic_backfill_plan(build_user()))

    assert plan["dataset_root"] == str(OUTPUT_DIR_DEFAULT)
    assert plan["transactions"] >= 500


def test_apply_synthetic_backfill_uses_default_dataset(monkeypatch) -> None:
    async def fake_apply_dataset(dataset_root):
        assert dataset_root == OUTPUT_DIR_DEFAULT
        return {"status": "ok", "transactions": 547}

    monkeypatch.setattr(admin_router, "apply_dataset", fake_apply_dataset)

    result = asyncio.run(admin_router.apply_synthetic_backfill(build_user()))

    assert result["status"] == "ok"
    assert result["transactions"] == 547
