from decimal import Decimal
from uuid import uuid4

from app.models.rule import Rule
from app.services.admin import build_api_integrations, build_rule_catalog_items


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
