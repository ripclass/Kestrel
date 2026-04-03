import asyncio

import pytest
from fastapi import HTTPException

from app.auth import AuthenticatedUser
from app.routers import admin as admin_router
from app.schemas.admin import AdminMaintenanceResponse
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

    assert plan.dataset_root == str(OUTPUT_DIR_DEFAULT)
    assert plan.transactions >= 500


def test_apply_synthetic_backfill_uses_default_dataset(monkeypatch) -> None:
    async def fake_apply_dataset(dataset_root):
        assert dataset_root == OUTPUT_DIR_DEFAULT
        return {
            "dataset_root": str(dataset_root),
            "organizations": 7,
            "entities": 22,
            "connections": 20,
            "matches": 1,
            "transactions": 547,
            "str_reports": 7,
            "alerts": 1,
            "cases": 1,
            "reporting_orgs": {"BFIU": 1},
        }

    monkeypatch.setattr(admin_router, "apply_dataset", fake_apply_dataset)

    result = asyncio.run(admin_router.apply_synthetic_backfill(build_user()))

    assert result.dataset_root == str(OUTPUT_DIR_DEFAULT)
    assert result.transactions == 547


def test_apply_rules_policy_fix_uses_maintenance_helper(monkeypatch) -> None:
    async def fake_apply_rules_insert_policy_fix():
        return AdminMaintenanceResponse(action="rules_insert_policy_fix", applied=True, detail="ok")

    monkeypatch.setattr(admin_router, "apply_rules_insert_policy_fix", fake_apply_rules_insert_policy_fix)

    result = asyncio.run(admin_router.apply_rules_policy_fix(build_user()))

    assert result.action == "rules_insert_policy_fix"
    assert result.applied is True
