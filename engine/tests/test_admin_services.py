from decimal import Decimal
from uuid import uuid4

from app.auth import AuthenticatedUser
from app.models.rule import Rule
from app.services.admin import (
    _validate_requested_persona,
    _validate_requested_role,
    build_api_integrations,
    build_rule_catalog_items,
)


def test_build_rule_catalog_items_merges_yaml_baselines_and_org_overrides() -> None:
    yaml_rules = [
        {"code": "rapid_cashout", "title": "Rapid cashout", "weight": 8.0, "threshold": 75},
        {"code": "fan_in_burst", "title": "Fan-in burst", "weight": 6.0, "threshold": 60},
    ]
    override = Rule(
        id=uuid4(),
        org_id=uuid4(),
        code="rapid_cashout",
        name="Rapid cashout override",
        description="Higher weight for this institution.",
        category="cashout",
        is_active=True,
        is_system=False,
        weight=Decimal("9.50"),
        definition={"threshold": 82},
        version=3,
    )
    custom = Rule(
        id=uuid4(),
        org_id=uuid4(),
        code="wallet_chain",
        name="Wallet chain",
        description="Custom organization rule stored in DB.",
        category="network",
        is_active=False,
        is_system=False,
        weight=Decimal("4.00"),
        definition={"threshold": 55},
        version=1,
    )

    catalog = build_rule_catalog_items(yaml_rules, [override, custom])

    rapid_cashout = next(rule for rule in catalog if rule.code == "rapid_cashout")
    wallet_chain = next(rule for rule in catalog if rule.code == "wallet_chain")

    assert rapid_cashout.name == "Rapid cashout override"
    assert rapid_cashout.source == "organization overlay"
    assert rapid_cashout.weight == 9.5
    assert rapid_cashout.threshold == 82.0
    assert wallet_chain.source == "organization custom"
    assert wallet_chain.is_active is False


def test_build_rule_catalog_items_prefers_org_specific_variant_over_system_registry() -> None:
    yaml_rules = [{"code": "layering", "title": "Layering", "weight": 7.0, "threshold": 65}]
    system_rule = Rule(
        id=uuid4(),
        org_id=None,
        code="layering",
        name="Layering system",
        description="System registry rule",
        category="network",
        is_active=True,
        is_system=True,
        weight=Decimal("7.00"),
        definition={"threshold": 65},
        version=2,
    )
    org_rule = Rule(
        id=uuid4(),
        org_id=uuid4(),
        code="layering",
        name="Layering overlay",
        description="Org-specific override",
        category="network",
        is_active=False,
        is_system=False,
        weight=Decimal("8.00"),
        definition={"threshold": 72},
        version=3,
    )

    catalog = build_rule_catalog_items(yaml_rules, [system_rule, org_rule])
    layering = next(rule for rule in catalog if rule.code == "layering")

    assert layering.name == "Layering overlay"
    assert layering.source == "organization overlay"
    assert layering.is_active is False
    assert layering.threshold == 72.0


def test_build_api_integrations_reflects_runtime_configuration() -> None:
    class StubSettings:
        goaml_sync_enabled = False
        goaml_base_url = None
        storage_bucket_exports = "kestrel-exports"
        storage_bucket_uploads = "kestrel-uploads"

        @staticmethod
        def has_complete_storage_config() -> bool:
            return True

    integrations = build_api_integrations(settings=StubSettings(), include_synthetic=True)

    ids = {integration.id for integration in integrations}
    statuses = {integration.id: integration.status for integration in integrations}

    assert {"goaml-adapter", "report-export-delivery", "synthetic-backfill"} <= ids
    assert statuses["goaml-adapter"] == "stubbed"
    assert statuses["report-export-delivery"] == "active"


def test_validate_requested_role_rejects_unauthorized_promotions() -> None:
    manager = AuthenticatedUser(
        user_id=str(uuid4()),
        email="manager@kestrel.test",
        org_id=str(uuid4()),
        org_type="bank",
        role="manager",
        persona="bank_camlco",
        designation="Manager",
    )

    try:
        _validate_requested_role(manager, "admin")
    except PermissionError as exc:
        assert "Managers cannot assign admin roles." in str(exc)
    else:
        raise AssertionError("Manager promotion restriction was not enforced.")


def test_validate_requested_persona_rejects_invalid_org_persona_pairing() -> None:
    try:
        _validate_requested_persona("bank", "bfiu_director")
    except ValueError as exc:
        assert "is not valid" in str(exc)
    else:
        raise AssertionError("Invalid persona pairing was not rejected.")
