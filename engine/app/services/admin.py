from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import AuthenticatedUser
from app.config import Settings, get_settings
from app.core.detection.loader import load_rules
from app.models.detection_run import DetectionRun
from app.models.org import Organization
from app.models.profile import Profile
from app.models.rule import Rule
from app.models.str_report import STRReport
from app.schemas.admin import (
    AdminIntegrationSummary,
    AdminIntegrationsResponse,
    AdminRuleSummary,
    AdminRulesResponse,
    AdminSettingsResponse,
    AdminSummaryResponse,
    AdminTeamMember,
    AdminTeamResponse,
)
from seed.dbbl_synthetic import OUTPUT_DIR_DEFAULT

RULES_DIR = Path(__file__).resolve().parents[1] / "core" / "detection" / "rules"
SYNTHETIC_SUMMARY_PATH = OUTPUT_DIR_DEFAULT / "summary.json"
ROLE_ORDER = {
    "superadmin": 0,
    "admin": 1,
    "manager": 2,
    "analyst": 3,
    "viewer": 4,
}


def _as_uuid(value: str) -> UUID:
    return UUID(str(value))


def _as_float(value: Decimal | float | int | None) -> float:
    if value is None:
        return 0.0
    return float(value)


def _synthetic_backfill_available() -> bool:
    return OUTPUT_DIR_DEFAULT.exists() and SYNTHETIC_SUMMARY_PATH.exists()


def _synthetic_generated_at() -> str | None:
    if not SYNTHETIC_SUMMARY_PATH.exists():
        return None
    try:
        payload = json.loads(SYNTHETIC_SUMMARY_PATH.read_text(encoding="utf-8"))
    except Exception:
        return None
    generated_at = payload.get("generated_at")
    return str(generated_at) if isinstance(generated_at, str) else None


async def _load_org(session: AsyncSession, user: AuthenticatedUser) -> Organization | None:
    result = await session.execute(select(Organization).where(Organization.id == _as_uuid(user.org_id)))
    return result.scalars().first()


async def _load_profiles(session: AsyncSession, user: AuthenticatedUser) -> list[Profile]:
    result = await session.execute(
        select(Profile).where(Profile.org_id == _as_uuid(user.org_id))
    )
    return list(result.scalars().all())


async def _load_reports(session: AsyncSession) -> list[STRReport]:
    return list((await session.execute(select(STRReport))).scalars().all())


async def _load_runs(session: AsyncSession) -> list[DetectionRun]:
    return list((await session.execute(select(DetectionRun))).scalars().all())


async def _load_db_rules(session: AsyncSession) -> list[Rule]:
    return list((await session.execute(select(Rule))).scalars().all())


def _sort_profiles(profiles: list[Profile]) -> list[Profile]:
    return sorted(
        profiles,
        key=lambda member: (
            ROLE_ORDER.get(member.role, 99),
            member.full_name.lower(),
        ),
    )


def _system_rule_name(rule_payload: dict[str, object]) -> str:
    title = rule_payload.get("title")
    if isinstance(title, str) and title.strip():
        return title.strip()
    code = str(rule_payload.get("code") or "unnamed_rule")
    return code.replace("_", " ").title()


def _system_rule_description(rule_payload: dict[str, object]) -> str:
    threshold = rule_payload.get("threshold")
    if isinstance(threshold, (int, float)):
        return f"Baseline system rule loaded from YAML with threshold {threshold}."
    return "Baseline system rule loaded from YAML."


def build_rule_catalog_items(yaml_rules: list[dict[str, object]], db_rules: list[Rule]) -> list[AdminRuleSummary]:
    db_rules_by_code = {rule.code: rule for rule in db_rules}
    catalog: list[AdminRuleSummary] = []

    for rule_payload in yaml_rules:
        code = str(rule_payload.get("code") or "").strip()
        if not code:
            continue
        db_rule = db_rules_by_code.pop(code, None)
        definition = db_rule.definition if db_rule and isinstance(db_rule.definition, dict) else {}
        threshold = definition.get("threshold", rule_payload.get("threshold"))
        catalog.append(
            AdminRuleSummary(
                code=code,
                name=db_rule.name if db_rule else _system_rule_name(rule_payload),
                description=db_rule.description or _system_rule_description(rule_payload) if db_rule else _system_rule_description(rule_payload),
                category=db_rule.category if db_rule else "behavioral",
                source="organization overlay" if db_rule and db_rule.org_id else "system baseline",
                is_active=db_rule.is_active if db_rule else True,
                is_system=db_rule.is_system if db_rule else True,
                weight=_as_float(db_rule.weight if db_rule else rule_payload.get("weight")),
                version=db_rule.version if db_rule else 1,
                threshold=float(threshold) if isinstance(threshold, (int, float)) else None,
            )
        )

    for db_rule in db_rules_by_code.values():
        threshold = None
        if isinstance(db_rule.definition, dict):
            raw_threshold = db_rule.definition.get("threshold")
            if isinstance(raw_threshold, (int, float)):
                threshold = float(raw_threshold)
        catalog.append(
            AdminRuleSummary(
                code=db_rule.code,
                name=db_rule.name,
                description=db_rule.description or "Custom organization rule stored in the Kestrel rules registry.",
                category=db_rule.category,
                source="organization custom" if db_rule.org_id else "system registry",
                is_active=db_rule.is_active,
                is_system=db_rule.is_system,
                weight=_as_float(db_rule.weight),
                version=db_rule.version,
                threshold=threshold,
            )
        )

    return sorted(
        catalog,
        key=lambda item: (
            not item.is_active,
            item.source.startswith("organization"),
            item.code,
        ),
    )


def build_api_integrations(*, settings: Settings, include_synthetic: bool) -> list[AdminIntegrationSummary]:
    integrations = [
        AdminIntegrationSummary(
            id="goaml-adapter",
            name="goAML adapter",
            status="active" if settings.goaml_sync_enabled and bool(settings.goaml_base_url) else "stubbed",
            detail=(
                "goAML sync endpoints are configured for network enrichment."
                if settings.goaml_sync_enabled and settings.goaml_base_url
                else "The coexistence adapter boundary is present, but live sync remains intentionally disabled."
            ),
            scope=["str:sync", "matches:read"],
        ),
        AdminIntegrationSummary(
            id="report-export-delivery",
            name="Report export delivery",
            status="active" if settings.has_complete_storage_config() else "pending",
            detail=(
                f"Exports are configured for Supabase buckets {settings.storage_bucket_exports} and {settings.storage_bucket_uploads}."
                if settings.has_complete_storage_config()
                else "Storage-backed report delivery is waiting on complete Supabase bucket configuration."
            ),
            scope=["reports:write", "cases:read"],
        ),
    ]

    if include_synthetic:
        integrations.append(
            AdminIntegrationSummary(
                id="synthetic-backfill",
                name="Synthetic intelligence backfill",
                status="available" if _synthetic_backfill_available() else "missing",
                detail=(
                    "Sanitized DBBL-derived synthetic fixtures are available for regulator-side enrichment backfill."
                    if _synthetic_backfill_available()
                    else "Synthetic backfill assets are not present on this deployment."
                ),
                scope=["entities:write", "matches:write", "alerts:write"],
                last_used_at=_synthetic_generated_at(),
            )
        )

    return integrations


async def build_admin_summary(
    session: AsyncSession,
    *,
    user: AuthenticatedUser,
    settings: Settings | None = None,
) -> AdminSummaryResponse:
    runtime_settings = settings or get_settings()
    org = await _load_org(session, user)
    profiles = await _load_profiles(session, user)
    reports = await _load_reports(session)
    runs = await _load_runs(session)
    rules = build_rule_catalog_items(load_rules(RULES_DIR), await _load_db_rules(session))
    integrations = build_api_integrations(
        settings=runtime_settings,
        include_synthetic=user.org_type == "regulator",
    )

    return AdminSummaryResponse(
        org_name=org.name if org else "Unknown organization",
        org_type=org.org_type if org else user.org_type,
        plan=org.plan if org else "standard",
        team_members=len(profiles),
        active_rules=sum(1 for rule in rules if rule.is_active),
        total_rules=len(rules),
        api_integrations=len(integrations),
        cross_bank_hits=sum(1 for report in reports if report.cross_bank_hit),
        detection_runs=len(runs),
        synthetic_backfill_available=user.org_type == "regulator" and _synthetic_backfill_available(),
    )


async def build_admin_settings(
    session: AsyncSession,
    *,
    user: AuthenticatedUser,
    settings: Settings | None = None,
) -> AdminSettingsResponse:
    runtime_settings = settings or get_settings()
    org = await _load_org(session, user)

    return AdminSettingsResponse(
        org_name=org.name if org else "Unknown organization",
        org_type=org.org_type if org else user.org_type,
        plan=org.plan if org else "standard",
        bank_code=org.bank_code if org else None,
        auth_configured=runtime_settings.has_complete_supabase_auth_config(),
        storage_configured=runtime_settings.has_complete_storage_config(),
        demo_mode_enabled=runtime_settings.demo_mode_enabled(),
        goaml_sync_enabled=runtime_settings.goaml_sync_enabled,
        goaml_base_url_configured=bool(runtime_settings.goaml_base_url),
        environment=runtime_settings.environment,
        app_version=runtime_settings.app_version,
        uploads_bucket=runtime_settings.storage_bucket_uploads,
        exports_bucket=runtime_settings.storage_bucket_exports,
        synthetic_backfill_available=user.org_type == "regulator" and _synthetic_backfill_available(),
    )


async def build_team_directory(
    session: AsyncSession,
    *,
    user: AuthenticatedUser,
) -> AdminTeamResponse:
    profiles = _sort_profiles(await _load_profiles(session, user))
    return AdminTeamResponse(
        members=[
            AdminTeamMember(
                id=str(member.id),
                full_name=member.full_name,
                designation=member.designation,
                role=member.role,
                persona=member.persona,
            )
            for member in profiles
        ]
    )


async def build_rule_catalog(
    session: AsyncSession,
) -> AdminRulesResponse:
    db_rules = await _load_db_rules(session)
    system_rules = load_rules(RULES_DIR)
    return AdminRulesResponse(rules=build_rule_catalog_items(system_rules, db_rules))


async def build_admin_integrations(
    *,
    user: AuthenticatedUser,
    settings: Settings | None = None,
) -> AdminIntegrationsResponse:
    runtime_settings = settings or get_settings()
    return AdminIntegrationsResponse(
        integrations=build_api_integrations(
            settings=runtime_settings,
            include_synthetic=user.org_type == "regulator",
        )
    )
