"""Tenant-scoping regression tests.

The engine connects to Postgres as the table-owner role, which bypasses
RLS — service-layer filters in app/services/tenancy.py are the only
isolation on the engine request path. These tests pin that behaviour:
a bank-persona statement must carry an org filter, a bank without an
org claim must see nothing (fail closed), and cross-org row access must
404.
"""
import uuid

import pytest
from fastapi import HTTPException
from sqlalchemy import select

from app.auth import AuthenticatedUser
from app.models.alert import Alert
from app.services.tenancy import ensure_org_access, is_regulator, scope_to_user, user_org_uuid

BANK_ORG = "9c222222-2222-4222-8222-222222222222"
OTHER_ORG = "8b111111-1111-4111-8111-111111111111"


def _user(org_type: str = "bank", org_id: str = BANK_ORG, user_id: str = "user-1") -> AuthenticatedUser:
    return AuthenticatedUser(
        user_id=user_id,
        email="camlco@example.test",
        org_id=org_id,
        org_type=org_type,
        role="admin",
        persona="bank_camlco",
        designation="CAMLCO",
    )


def _regulator() -> AuthenticatedUser:
    return AuthenticatedUser(
        user_id="reg-1",
        email="analyst@bfiu.test",
        org_id=OTHER_ORG,
        org_type="regulator",
        role="analyst",
        persona="bfiu_analyst",
        designation="Analyst",
    )


class TestIsRegulator:
    def test_regulator_true(self):
        assert is_regulator(_regulator()) is True

    def test_bank_false(self):
        assert is_regulator(_user()) is False

    def test_case_and_whitespace_insensitive(self):
        assert is_regulator(_user(org_type="  Regulator ")) is True

    def test_empty_org_type_false(self):
        assert is_regulator(_user(org_type="")) is False


class TestUserOrgUuid:
    def test_valid(self):
        assert user_org_uuid(_user()) == uuid.UUID(BANK_ORG)

    def test_invalid(self):
        assert user_org_uuid(_user(org_id="not-a-uuid")) is None

    def test_empty(self):
        assert user_org_uuid(_user(org_id="")) is None


class TestScopeToUser:
    def test_bank_statement_carries_org_filter(self):
        stmt = scope_to_user(select(Alert), _user(), Alert.org_id)
        compiled = str(stmt)
        assert "alerts.org_id" in compiled

    def test_regulator_statement_unfiltered(self):
        stmt = scope_to_user(select(Alert), _regulator(), Alert.org_id)
        assert stmt.whereclause is None

    def test_bank_without_org_claim_fails_closed(self):
        stmt = scope_to_user(select(Alert), _user(org_id="not-a-uuid"), Alert.org_id)
        assert stmt.whereclause is not None
        where_sql = str(stmt.whereclause).lower()
        assert "org_id" not in where_sql
        assert "false" in where_sql or "0 = 1" in where_sql


class TestEnsureOrgAccess:
    def test_own_org_passes(self):
        ensure_org_access(uuid.UUID(BANK_ORG), _user())

    def test_regulator_passes_any_org(self):
        ensure_org_access(uuid.UUID(BANK_ORG), _regulator())

    def test_cross_org_raises_404(self):
        with pytest.raises(HTTPException) as excinfo:
            ensure_org_access(uuid.UUID(OTHER_ORG), _user())
        assert excinfo.value.status_code == 404

    def test_missing_org_claim_raises_404(self):
        with pytest.raises(HTTPException) as excinfo:
            ensure_org_access(uuid.UUID(BANK_ORG), _user(org_id=""))
        assert excinfo.value.status_code == 404

    def test_missing_resource_org_raises_404_for_bank(self):
        with pytest.raises(HTTPException) as excinfo:
            ensure_org_access(None, _user())
        assert excinfo.value.status_code == 404

    def test_missing_resource_org_passes_for_regulator(self):
        ensure_org_access(None, _regulator())


class TestCaseAccessPredicate:
    """RFI recipients live in another org — the case predicate must let
    requested_from through while still blocking unrelated orgs."""

    def _case(self, org_id: str = OTHER_ORG, requested_from: str | None = None):
        from types import SimpleNamespace

        return SimpleNamespace(
            org_id=uuid.UUID(org_id),
            requested_from=uuid.UUID(requested_from) if requested_from else None,
        )

    def test_own_org_case_accessible(self):
        from app.services.case_mgmt import _user_can_access_case

        assert _user_can_access_case(self._case(org_id=BANK_ORG), _user()) is True

    def test_rfi_recipient_accessible_cross_org(self):
        from app.services.case_mgmt import _user_can_access_case

        recipient_id = "7a333333-3333-4333-8333-333333333333"
        case = self._case(org_id=OTHER_ORG, requested_from=recipient_id)
        assert _user_can_access_case(case, _user(user_id=recipient_id)) is True

    def test_unrelated_org_blocked(self):
        from app.services.case_mgmt import _user_can_access_case

        assert _user_can_access_case(self._case(org_id=OTHER_ORG), _user()) is False

    def test_regulator_sees_all(self):
        from app.services.case_mgmt import _user_can_access_case

        assert _user_can_access_case(self._case(org_id=OTHER_ORG), _regulator()) is True
