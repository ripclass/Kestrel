from __future__ import annotations

from copy import deepcopy
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import AuthenticatedUser
from app.models.alert import Alert
from app.models.audit import AuditLog
from app.models.case import Case
from app.models.entity import Entity
from app.models.org import Organization
from app.models.profile import Profile
from app.schemas.alert import AlertDetail, AlertMutationRequest, AlertMutationResponse, AlertReason
from app.schemas.case import CaseSummary
from app.services.case_mgmt import _serialize_case_summary
from app.services.investigation import (
    _candidate_org_ids,
    _load_org_name_map,
    _serialize_entity_summary,
    get_network_graph,
)


def _as_float(value: Decimal | float | int | None) -> float:
    if value is None:
        return 0.0
    return float(value)


def _as_uuid(value: str | UUID | None) -> UUID | None:
    if value is None or value == "":
        return None
    if isinstance(value, UUID):
        return value
    try:
        return UUID(str(value))
    except ValueError:
        return None


def _iso(value: datetime | None) -> str:
    if value is None:
        return datetime.now(UTC).isoformat()
    return value.astimezone(UTC).isoformat()


def _normalize_reasons(value: object) -> list[dict[str, object]]:
    payload = value if isinstance(value, list) else []
    reasons: list[dict[str, object]] = []
    for item in payload:
        if not isinstance(item, dict):
            continue
        normalized = dict(item)
        normalized["score"] = int(normalized.get("score") or 0)
        normalized["weight"] = float(normalized.get("weight") or 1.0)
        normalized["evidence"] = normalized.get("evidence") if isinstance(normalized.get("evidence"), dict) else {}
        normalized["recommended_action"] = normalized.get("recommended_action")
        reasons.append(AlertReason.model_validate(normalized).model_dump())
    return reasons


async def _load_profile_name_map(session: AsyncSession, profile_ids: set[str]) -> dict[str, str]:
    parsed_ids = [_as_uuid(value) for value in profile_ids]
    parsed_ids = [value for value in parsed_ids if value is not None]
    if not parsed_ids:
        return {}

    result = await session.execute(select(Profile.id, Profile.full_name).where(Profile.id.in_(parsed_ids)))
    return {str(profile_id): full_name for profile_id, full_name in result.all()}


async def _fetch_alert_with_org(session: AsyncSession, alert_id: str) -> tuple[Alert, str]:
    parsed_id = _as_uuid(alert_id)
    if parsed_id is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alert not found.")

    result = await session.execute(
        select(Alert, Organization.name.label("org_name"))
        .outerjoin(Organization, Organization.id == Alert.org_id)
        .where(Alert.id == parsed_id)
        .limit(1)
    )
    row = result.first()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alert not found.")
    alert, org_name = row
    return alert, str(org_name or "Kestrel")


async def _record_alert_audit(
    session: AsyncSession,
    *,
    alert: Alert,
    user: AuthenticatedUser,
    action: str,
    details: dict[str, Any],
    ip: str | None,
) -> None:
    session.add(
        AuditLog(
            org_id=alert.org_id,
            user_id=_as_uuid(user.user_id),
            action=action,
            resource_type="alert",
            resource_id=alert.id,
            details=details,
            ip=ip,
        )
    )


def _serialize_alert_summary(
    alert: Alert,
    *,
    org_name: str,
    profile_name_map: dict[str, str],
) -> dict[str, object]:
    assigned_to = str(alert.assigned_to) if alert.assigned_to else None
    return {
        "id": str(alert.id),
        "title": alert.title,
        "description": alert.description or "",
        "alert_type": alert.alert_type,
        "risk_score": alert.risk_score,
        "severity": alert.severity,
        "status": alert.status,
        "created_at": _iso(alert.created_at),
        "org_name": org_name,
        "entity_id": str(alert.entity_id) if alert.entity_id else "",
        "reasons": _normalize_reasons(alert.reasons),
        "assigned_to": profile_name_map.get(assigned_to, assigned_to),
        "case_id": str(alert.case_id) if alert.case_id else None,
    }


async def list_alerts(session: AsyncSession) -> list[dict[str, object]]:
    result = await session.execute(
        select(Alert, Organization.name.label("org_name"))
        .outerjoin(Organization, Organization.id == Alert.org_id)
        .order_by(Alert.risk_score.desc(), Alert.created_at.desc())
    )
    rows = list(result.all())
    profile_name_map = await _load_profile_name_map(
        session,
        {str(alert.assigned_to) for alert, _org_name in rows if alert.assigned_to},
    )

    return [
        _serialize_alert_summary(alert, org_name=str(org_name or "Kestrel"), profile_name_map=profile_name_map)
        for alert, org_name in rows
    ]


async def get_alert_detail(
    session: AsyncSession,
    *,
    user: AuthenticatedUser,
    alert_id: str,
) -> dict[str, object]:
    alert, org_name = await _fetch_alert_with_org(session, alert_id)
    profile_name_map = await _load_profile_name_map(
        session,
        {str(alert.assigned_to)} if alert.assigned_to else set(),
    )
    payload = _serialize_alert_summary(alert, org_name=org_name, profile_name_map=profile_name_map)

    entity_payload = None
    graph = {
        "focus_entity_id": str(alert.entity_id or alert.id),
        "stats": {"node_count": 0, "edge_count": 0, "max_depth": 0, "suspicious_paths": 0},
        "nodes": [],
        "edges": [],
    }

    if alert.entity_id:
        entity = await session.get(Entity, alert.entity_id)
        if entity is not None:
            org_name_map = await _load_org_name_map(
                session,
                {org_id for org_id in _candidate_org_ids(entity.reporting_orgs)},
            )
            entity_payload = _serialize_entity_summary(entity, org_name_map)
            graph = await get_network_graph(session, user=user, entity_id=str(entity.id))

    return {
        **payload,
        "graph": graph,
        "entity": entity_payload,
    }


async def _build_case_summary(
    session: AsyncSession,
    case: Case,
) -> dict[str, object]:
    profile_name_map = await _load_profile_name_map(
        session,
        {str(case.assigned_to)} if case.assigned_to else set(),
    )
    return _serialize_case_summary(case, profile_name_map)


async def _create_case_from_alert(
    session: AsyncSession,
    *,
    alert: Alert,
    entity: Entity | None,
    user: AuthenticatedUser,
    case_title: str | None,
    note: str | None,
) -> Case:
    if alert.case_id:
        existing = await session.get(Case, alert.case_id)
        if existing is not None:
            return existing

    case = Case(
        org_id=alert.org_id,
        title=case_title or alert.title,
        summary=note or alert.description or alert.title,
        category=alert.alert_type,
        severity=alert.severity,
        status="investigating",
        assigned_to=_as_uuid(user.user_id),
        linked_alert_ids=[alert.id],
        linked_entity_ids=[entity.id] if entity is not None else [],
        total_exposure=_as_float(entity.total_exposure) if entity is not None else 0.0,
        recovered=0.0,
        timeline=[
            {
                "type": "status_change",
                "user_id": user.user_id,
                "timestamp": datetime.now(UTC).isoformat(),
                "content": f"Case created from alert {alert.title}.",
            }
        ],
        tags=[alert.alert_type],
    )
    session.add(case)
    await session.flush()
    return case


async def update_alert(
    session: AsyncSession,
    *,
    alert_id: str,
    user: AuthenticatedUser,
    request: AlertMutationRequest,
    ip: str | None,
) -> AlertMutationResponse:
    alert, _org_name = await _fetch_alert_with_org(session, alert_id)
    linked_case: Case | None = None
    entity = await session.get(Entity, alert.entity_id) if alert.entity_id else None

    if request.action == "start_review":
        alert.status = "reviewing"
    elif request.action == "assign_to_me":
        alert.assigned_to = _as_uuid(user.user_id)
        if alert.status == "open":
            alert.status = "reviewing"
    elif request.action == "escalate":
        alert.status = "escalated"
    elif request.action == "mark_true_positive":
        alert.status = "true_positive"
        alert.resolved_by = _as_uuid(user.user_id)
        alert.resolved_at = datetime.now(UTC)
    elif request.action == "mark_false_positive":
        alert.status = "false_positive"
        alert.resolved_by = _as_uuid(user.user_id)
        alert.resolved_at = datetime.now(UTC)
    else:
        linked_case = await _create_case_from_alert(
            session,
            alert=alert,
            entity=entity,
            user=user,
            case_title=request.case_title,
            note=request.note,
        )
        alert.case_id = linked_case.id
        alert.status = "escalated"
        alert.assigned_to = alert.assigned_to or _as_uuid(user.user_id)

    await _record_alert_audit(
        session,
        alert=alert,
        user=user,
        action=f"alert.{request.action}",
        details=request.model_dump(),
        ip=ip,
    )
    await session.commit()
    await session.refresh(alert)

    case_payload = None
    if linked_case is not None:
        await session.refresh(linked_case)
        case_payload = await _build_case_summary(session, linked_case)

    detail = await get_alert_detail(session, user=user, alert_id=str(alert.id))
    return AlertMutationResponse(
        alert=AlertDetail.model_validate(detail),
        case=CaseSummary.model_validate(case_payload) if case_payload else None,
    )
