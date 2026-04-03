from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path
from uuid import UUID
import uuid

from sqlalchemy import or_, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import AuthenticatedUser
from app.database import SessionLocal
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
    AdminMaintenanceResponse,
    AdminRuleMutationRequest,
    AdminRuleSummary,
    AdminRulesResponse,
    AdminSettingsResponse,
    AdminSummaryResponse,
    AdminTeamMember,
    AdminTeamMutationResponse,
    AdminTeamResponse,
    AdminTeamUpdateRequest,
    SyntheticBackfillPlanResponse,
    SyntheticBackfillResultResponse,
)
from seed.dbbl_synthetic import OUTPUT_DIR_DEFAULT
from seed.load_dbbl_synthetic import build_load_plan

RULES_DIR = Path(__file__).resolve().parents[1] / "core" / "detection" / "rules"
SYNTHETIC_SUMMARY_PATH = OUTPUT_DIR_DEFAULT / "summary.json"
VALID_PERSONAS_BY_ORG_TYPE = {
    "regulator": {"bfiu_analyst", "bfiu_director"},
    "bank": {"bank_camlco"},
    "mfs": {"bank_camlco"},
    "nbfi": {"bank_camlco"},
}
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


def _yaml_rule_map() -> dict[str, dict[str, object]]:
    payloads: dict[str, dict[str, object]] = {}
    for rule_payload in load_rules(RULES_DIR):
        code = str(rule_payload.get("code") or "").strip()
        if code:
            payloads[code] = rule_payload
    return payloads


def _normalize_text(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    return normalized or None


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


async def _load_rule_variants(session: AsyncSession, code: str) -> list[Rule]:
    result = await session.execute(select(Rule).where(Rule.code == code))
    return list(result.scalars().all())


async def _load_rule_variants_for_org(session: AsyncSession, code: str, org_id: UUID) -> list[Rule]:
    result = await session.execute(
        select(Rule).where(
            Rule.code == code,
            or_(Rule.org_id == org_id, Rule.is_system.is_(True), Rule.org_id.is_(None)),
        )
    )
    return list(result.scalars().all())


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


def _prefer_rule_variant(left: Rule, right: Rule) -> Rule:
    left_priority = (0 if left.org_id else 1, 0 if not left.is_system else 1, left.version * -1)
    right_priority = (0 if right.org_id else 1, 0 if not right.is_system else 1, right.version * -1)
    return left if left_priority <= right_priority else right


def _rule_source(db_rule: Rule | None, yaml_rule: dict[str, object] | None = None) -> str:
    if db_rule is None:
        return "system baseline"
    if db_rule.org_id:
        return "organization overlay" if yaml_rule is not None else "organization custom"
    if db_rule.is_system:
        return "system registry"
    return "organization custom"


def build_rule_summary(
    *,
    code: str,
    yaml_rule: dict[str, object] | None,
    db_rule: Rule | None,
) -> AdminRuleSummary:
    definition = db_rule.definition if db_rule and isinstance(db_rule.definition, dict) else {}
    threshold = definition.get("threshold")
    if threshold is None and yaml_rule is not None:
        threshold = yaml_rule.get("threshold")

    return AdminRuleSummary(
        code=code,
        name=db_rule.name if db_rule else _system_rule_name(yaml_rule or {"code": code}),
        description=(
            db_rule.description if db_rule and db_rule.description else _system_rule_description(yaml_rule or {"code": code})
        ),
        category=(
            db_rule.category
            if db_rule
            else str((yaml_rule or {}).get("category") or "behavioral")
        ),
        source=_rule_source(db_rule, yaml_rule),
        is_active=db_rule.is_active if db_rule else True,
        is_system=db_rule.is_system if db_rule else True,
        weight=_as_float(db_rule.weight if db_rule else (yaml_rule or {}).get("weight")),
        version=db_rule.version if db_rule else 1,
        threshold=float(threshold) if isinstance(threshold, (int, float)) else None,
    )


def build_rule_catalog_items(yaml_rules: list[dict[str, object]], db_rules: list[Rule]) -> list[AdminRuleSummary]:
    yaml_rules_by_code = {
        str(rule_payload.get("code") or "").strip(): rule_payload
        for rule_payload in yaml_rules
        if str(rule_payload.get("code") or "").strip()
    }
    db_rules_by_code: dict[str, Rule] = {}
    for rule in db_rules:
        current = db_rules_by_code.get(rule.code)
        db_rules_by_code[rule.code] = rule if current is None else _prefer_rule_variant(current, rule)
    catalog: list[AdminRuleSummary] = []

    for code, yaml_rule in yaml_rules_by_code.items():
        catalog.append(
            build_rule_summary(
                code=code,
                yaml_rule=yaml_rule,
                db_rule=db_rules_by_code.pop(code, None),
            )
        )

    for code, db_rule in db_rules_by_code.items():
        catalog.append(build_rule_summary(code=code, yaml_rule=None, db_rule=db_rule))

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


def _validate_requested_role(actor: AuthenticatedUser, requested_role: str) -> None:
    if requested_role not in ROLE_ORDER:
        raise ValueError("Requested role is invalid.")
    if actor.role == "manager" and requested_role in {"admin", "superadmin"}:
        raise PermissionError("Managers cannot assign admin roles.")
    if actor.role == "admin" and requested_role == "superadmin":
        raise PermissionError("Admins cannot assign superadmin.")


def _validate_requested_persona(org_type: str, requested_persona: str) -> None:
    allowed = VALID_PERSONAS_BY_ORG_TYPE.get(org_type, {"bank_camlco"})
    if requested_persona not in allowed:
        raise ValueError(f"Persona {requested_persona} is not valid for {org_type} organizations.")


async def update_team_member(
    session: AsyncSession,
    *,
    user: AuthenticatedUser,
    member_id: str,
    payload: AdminTeamUpdateRequest,
) -> AdminTeamMutationResponse:
    org = await _load_org(session, user)
    if org is None:
        raise LookupError("Organization context is unavailable.")

    member = await session.get(Profile, _as_uuid(member_id))
    if member is None or member.org_id != org.id:
        raise LookupError("Team member not found for this organization.")

    if payload.role is not None:
        _validate_requested_role(user, payload.role)
        member.role = payload.role

    if payload.persona is not None:
        _validate_requested_persona(org.org_type, payload.persona)
        member.persona = payload.persona

    if payload.designation is not None:
        member.designation = _normalize_text(payload.designation)

    await session.commit()
    await session.refresh(member)

    return AdminTeamMutationResponse(
        member=AdminTeamMember(
            id=str(member.id),
            full_name=member.full_name,
            designation=member.designation,
            role=member.role,
            persona=member.persona,
        )
    )


async def _update_rule_configuration_in_session(
    session: AsyncSession,
    *,
    org_uuid: UUID,
    code: str,
    payload: AdminRuleMutationRequest,
    yaml_rule: dict[str, object] | None,
    variants: list[Rule],
) -> AdminRuleMutationResponse:
    org_rule = next((rule for rule in variants if rule.org_id == org_uuid), None)
    baseline_rule = next((rule for rule in variants if rule.org_id is None), None)

    if org_rule is None and yaml_rule is None and baseline_rule is None:
        raise LookupError("Rule definition was not found.")

    if org_rule is None:
        org_rule = Rule(
            id=uuid.uuid4(),
            org_id=org_uuid,
            code=code,
            name=baseline_rule.name if baseline_rule else _system_rule_name(yaml_rule or {"code": code}),
            description=baseline_rule.description if baseline_rule else _system_rule_description(yaml_rule or {"code": code}),
            category=baseline_rule.category if baseline_rule else str((yaml_rule or {}).get("category") or "behavioral"),
            is_active=True,
            is_system=False,
            weight=_as_float(baseline_rule.weight if baseline_rule else (yaml_rule or {}).get("weight")),
            definition=dict(baseline_rule.definition or {}) if baseline_rule and isinstance(baseline_rule.definition, dict) else {},
            version=1,
        )
        if "threshold" in (yaml_rule or {}):
            org_rule.definition = {
                **org_rule.definition,
                "threshold": (yaml_rule or {}).get("threshold"),
            }
        session.add(org_rule)
        await session.flush()

    changed = False
    fields_set = payload.model_fields_set

    if "is_active" in fields_set and payload.is_active is not None and org_rule.is_active != payload.is_active:
        org_rule.is_active = payload.is_active
        changed = True

    if "weight" in fields_set and payload.weight is not None and float(org_rule.weight) != payload.weight:
        org_rule.weight = payload.weight
        changed = True

    if "description" in fields_set:
        next_description = _normalize_text(payload.description)
        if org_rule.description != next_description:
            org_rule.description = next_description
            changed = True

    if "threshold" in fields_set:
        definition = dict(org_rule.definition or {})
        current_threshold = definition.get("threshold")
        if payload.threshold is None:
            if "threshold" in definition:
                definition.pop("threshold", None)
                changed = True
        elif current_threshold != payload.threshold:
            definition["threshold"] = payload.threshold
            changed = True
        org_rule.definition = definition

    if changed:
        org_rule.version += 1

    await session.commit()
    await session.refresh(org_rule)

    return AdminRuleMutationResponse(
        rule=build_rule_summary(code=code, yaml_rule=yaml_rule, db_rule=org_rule)
    )


async def update_rule_configuration(
    *,
    user: AuthenticatedUser,
    code: str,
    payload: AdminRuleMutationRequest,
) -> AdminRuleMutationResponse:
    yaml_rule = _yaml_rule_map().get(code)
    org_uuid = _as_uuid(user.org_id)
    async with SessionLocal() as session:
        variants = await _load_rule_variants_for_org(session, code, org_uuid)
        return await _update_rule_configuration_in_session(
            session,
            org_uuid=org_uuid,
            code=code,
            payload=payload,
            yaml_rule=yaml_rule,
            variants=variants,
        )


def build_synthetic_backfill_plan() -> SyntheticBackfillPlanResponse:
    return SyntheticBackfillPlanResponse.model_validate(build_load_plan(OUTPUT_DIR_DEFAULT))


def normalize_synthetic_backfill_result(payload: dict[str, object]) -> SyntheticBackfillResultResponse:
    reporting_orgs = payload.get("reporting_orgs")
    normalized_reporting_orgs = {
        str(key): int(value)
        for key, value in dict(reporting_orgs or {}).items()
    }
    return SyntheticBackfillResultResponse(
        dataset_root=str(payload["dataset_root"]),
        organizations=int(payload["organizations"]),
        entities=int(payload["entities"]),
        connections=int(payload["connections"]),
        matches=int(payload["matches"]),
        transactions=int(payload["transactions"]),
        str_reports=int(payload["str_reports"]),
        alerts=int(payload["alerts"]),
        cases=int(payload["cases"]),
        reporting_orgs=normalized_reporting_orgs,
    )


async def apply_rules_insert_policy_fix() -> AdminMaintenanceResponse:
    async with SessionLocal() as session:
        await session.execute(text("drop policy if exists rules_org on rules"))
        await session.execute(
            text(
                """
                create policy rules_org on rules
                  for all
                  using (org_id = auth_org_id() or is_system = true)
                  with check (org_id = auth_org_id() or is_system = true)
                """
            )
        )
        await session.commit()

    return AdminMaintenanceResponse(
        action="rules_insert_policy_fix",
        applied=True,
        detail="rules_org policy recreated with WITH CHECK for organization overlay inserts.",
    )
