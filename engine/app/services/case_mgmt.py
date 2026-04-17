from __future__ import annotations

from copy import deepcopy
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import AuthenticatedUser
from app.core.graph.builder import build_graph
from app.core.graph.export import export_graph
from app.models.alert import Alert
from app.models.audit import AuditLog
from app.models.case import Case
from app.models.connection import Connection
from app.models.entity import Entity
from app.models.profile import Profile
from app.schemas.case import (
    CaseDecideRequest,
    CaseMutationRequest,
    CaseMutationResponse,
    CaseProposeRequest,
    CaseRfiRequest,
    CaseWorkspace,
)
from app.services.investigation import (
    _candidate_org_ids,
    _fetch_entities_by_ids,
    _load_org_name_map,
    _serialize_entity_summary,
)

_CLOSED_CASE_STATUSES = {"closed_confirmed", "closed_false_positive"}
_CASE_ALERT_OUTCOMES = {
    "closed_confirmed": "true_positive",
    "closed_false_positive": "false_positive",
}


def _as_float(value: Decimal | float | int | None) -> float:
    if value is None:
        return 0.0
    return float(value)


def _iso(value: datetime | None) -> str:
    if value is None:
        return datetime.now(UTC).isoformat()
    return value.astimezone(UTC).isoformat()


def _as_uuid(value: str | UUID | None) -> UUID | None:
    if value is None or value == "":
        return None
    if isinstance(value, UUID):
        return value
    try:
        return UUID(str(value))
    except ValueError:
        return None


def _timeline_entry(
    *,
    entry_type: str,
    user: AuthenticatedUser,
    content: str,
    timestamp: datetime | None = None,
) -> dict[str, str]:
    moment = (timestamp or datetime.now(UTC)).astimezone(UTC).isoformat()
    return {
        "type": entry_type,
        "user_id": user.user_id,
        "timestamp": moment,
        "content": content,
    }


def _append_timeline(
    timeline: list[dict[str, object]] | None,
    *,
    entry_type: str,
    user: AuthenticatedUser,
    content: str,
) -> list[dict[str, object]]:
    next_timeline = list(timeline or [])
    next_timeline.append(_timeline_entry(entry_type=entry_type, user=user, content=content))
    return next_timeline


async def _load_profile_name_map(session: AsyncSession, profile_ids: set[str]) -> dict[str, str]:
    parsed_ids = [_as_uuid(value) for value in profile_ids]
    parsed_ids = [value for value in parsed_ids if value is not None]
    if not parsed_ids:
        return {}

    result = await session.execute(select(Profile.id, Profile.full_name).where(Profile.id.in_(parsed_ids)))
    return {str(profile_id): full_name for profile_id, full_name in result.all()}


def _linked_uuid_strings(values: list[UUID] | None) -> list[str]:
    return [str(value) for value in values or []]


def _serialize_case_summary(case: Case, profile_name_map: dict[str, str]) -> dict[str, object]:
    assigned_to = str(case.assigned_to) if case.assigned_to else None
    requested_by = str(case.requested_by) if case.requested_by else None
    requested_from = str(case.requested_from) if case.requested_from else None
    return {
        "id": str(case.id),
        "case_ref": case.case_ref,
        "title": case.title,
        "summary": case.summary or case.title,
        "severity": case.severity,
        "status": case.status,
        "total_exposure": _as_float(case.total_exposure),
        "assigned_to": profile_name_map.get(assigned_to, assigned_to),
        "linked_entity_ids": _linked_uuid_strings(case.linked_entity_ids),
        "linked_alert_ids": _linked_uuid_strings(case.linked_alert_ids),
        "variant": case.variant or "standard",
        "parent_case_id": str(case.parent_case_id) if case.parent_case_id else None,
        "proposal_decision": case.proposal_decision,
        "requested_by": profile_name_map.get(requested_by, requested_by),
        "requested_from": profile_name_map.get(requested_from, requested_from),
    }


def _serialize_case_timeline(
    timeline: list[dict[str, object]] | None,
    profile_name_map: dict[str, str],
) -> list[dict[str, str]]:
    payload: list[dict[str, str]] = []
    for index, entry in enumerate(timeline or []):
        user_id = str(entry.get("user_id") or "")
        actor = profile_name_map.get(user_id, user_id or "Kestrel")
        timestamp = str(entry.get("timestamp") or datetime.now(UTC).isoformat())
        payload.append(
            {
                "id": f"case-event-{index}",
                "title": str(entry.get("type") or "event").replace("_", " ").title(),
                "description": str(entry.get("content") or ""),
                "occurred_at": timestamp,
                "actor": actor,
            }
        )

    return sorted(payload, key=lambda item: item["occurred_at"], reverse=True)


def _serialize_case_notes(
    timeline: list[dict[str, object]] | None,
    profile_name_map: dict[str, str],
) -> list[dict[str, str]]:
    notes: list[dict[str, str]] = []
    for entry in timeline or []:
        if str(entry.get("type")) != "note":
            continue
        user_id = str(entry.get("user_id") or "")
        notes.append(
            {
                "actor_user_id": profile_name_map.get(user_id, user_id or "Kestrel"),
                "actor_role": "case_management",
                "note": str(entry.get("content") or ""),
                "occurred_at": str(entry.get("timestamp") or datetime.now(UTC).isoformat()),
            }
        )
    return sorted(notes, key=lambda item: item["occurred_at"], reverse=True)


async def _build_case_graph(session: AsyncSession, case: Case) -> dict[str, object] | None:
    linked_entities = [value for value in case.linked_entity_ids or [] if value is not None]
    if not linked_entities:
        return None

    entity_map = await _fetch_entities_by_ids(session, {str(value) for value in linked_entities})
    if not entity_map:
        return None

    parsed_ids = [UUID(entity_id) for entity_id in entity_map]
    result = await session.execute(
        select(Connection)
        .where(
            or_(
                Connection.from_entity_id.in_(parsed_ids),
                Connection.to_entity_id.in_(parsed_ids),
            )
        )
        .order_by(Connection.weight.desc(), Connection.last_seen.desc().nullslast())
        .limit(48)
    )
    connections = list(result.scalars().all())

    graph_entity_ids = set(entity_map.keys())
    for connection in connections:
        graph_entity_ids.add(str(connection.from_entity_id))
        graph_entity_ids.add(str(connection.to_entity_id))

    expanded_entity_map = await _fetch_entities_by_ids(session, graph_entity_ids)
    graph = build_graph(list(expanded_entity_map.values()), connections)
    focus_entity_id = str(linked_entities[0])
    return export_graph(graph, focus_entity_id)


async def _fetch_case_or_404(session: AsyncSession, case_id: str) -> Case:
    parsed_id = _as_uuid(case_id)
    if parsed_id is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case not found.")

    case = await session.get(Case, parsed_id)
    if case is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case not found.")
    return case


async def _record_case_audit(
    session: AsyncSession,
    *,
    case: Case,
    user: AuthenticatedUser,
    action: str,
    details: dict[str, Any],
    ip: str | None,
) -> None:
    session.add(
        AuditLog(
            org_id=case.org_id,
            user_id=_as_uuid(user.user_id),
            action=action,
            resource_type="case",
            resource_id=case.id,
            details=details,
            ip=ip,
        )
    )


async def list_cases(
    session: AsyncSession,
    *,
    variant: str | None = None,
    status_filter: str | None = None,
    assigned_to: str | None = None,
) -> list[dict[str, object]]:
    stmt = select(Case).order_by(Case.updated_at.desc().nullslast(), Case.created_at.desc())
    if variant:
        stmt = stmt.where(Case.variant == variant)
    if status_filter:
        stmt = stmt.where(Case.status == status_filter)
    if assigned_to:
        parsed = _as_uuid(assigned_to)
        if parsed is not None:
            stmt = stmt.where(Case.assigned_to == parsed)
    result = await session.execute(stmt)
    cases = list(result.scalars().all())
    profile_ids: set[str] = set()
    for case in cases:
        if case.assigned_to:
            profile_ids.add(str(case.assigned_to))
        if case.requested_by:
            profile_ids.add(str(case.requested_by))
        if case.requested_from:
            profile_ids.add(str(case.requested_from))
    profile_name_map = await _load_profile_name_map(session, profile_ids)
    return [_serialize_case_summary(case, profile_name_map) for case in cases]


async def get_case_workspace(
    session: AsyncSession,
    *,
    user: AuthenticatedUser,
    case_id: str,
) -> dict[str, object]:
    case = await _fetch_case_or_404(session, case_id)
    linked_entity_ids = {str(value) for value in case.linked_entity_ids or [] if value}
    evidence_entities = await _fetch_entities_by_ids(session, linked_entity_ids)
    org_name_map = await _load_org_name_map(
        session,
        {org_id for entity in evidence_entities.values() for org_id in _candidate_org_ids(entity.reporting_orgs)},
    )

    linked_profile_ids: set[str] = set()
    if case.assigned_to:
        linked_profile_ids.add(str(case.assigned_to))
    if case.requested_by:
        linked_profile_ids.add(str(case.requested_by))
    if case.requested_from:
        linked_profile_ids.add(str(case.requested_from))
    if case.proposal_decided_by:
        linked_profile_ids.add(str(case.proposal_decided_by))
    linked_profile_ids.update(
        str(entry.get("user_id"))
        for entry in case.timeline or []
        if entry.get("user_id")
    )
    profile_name_map = await _load_profile_name_map(session, linked_profile_ids)

    summary = _serialize_case_summary(case, profile_name_map)
    decided_by = str(case.proposal_decided_by) if case.proposal_decided_by else None
    return {
        **summary,
        "timeline": _serialize_case_timeline(case.timeline, profile_name_map),
        "evidence_entities": [
            _serialize_entity_summary(evidence_entities[entity_id], org_name_map)
            for entity_id in linked_entity_ids
            if entity_id in evidence_entities
        ],
        "notes": _serialize_case_notes(case.timeline, profile_name_map),
        "graph": await _build_case_graph(session, case),
        "proposal_decided_by": profile_name_map.get(decided_by, decided_by),
        "proposal_decided_at": _iso(case.proposal_decided_at) if case.proposal_decided_at else None,
    }


async def update_case(
    session: AsyncSession,
    *,
    case_id: str,
    user: AuthenticatedUser,
    request: CaseMutationRequest,
    ip: str | None,
) -> CaseMutationResponse:
    case = await _fetch_case_or_404(session, case_id)

    if request.action == "add_note":
        if not request.note or not request.note.strip():
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="A note is required.")
        case.timeline = _append_timeline(
            deepcopy(case.timeline or []),
            entry_type="note",
            user=user,
            content=request.note.strip(),
        )
    elif request.action == "assign_to_me":
        assignee = _as_uuid(user.user_id)
        case.assigned_to = assignee
        case.timeline = _append_timeline(
            deepcopy(case.timeline or []),
            entry_type="assignment",
            user=user,
            content=f"Assigned to {user.designation or user.email}.",
        )
    else:
        if not request.status:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="A target case status is required.")
        previous_status = case.status
        case.status = request.status
        case.closed_at = datetime.now(UTC) if request.status in _CLOSED_CASE_STATUSES else None
        case.timeline = _append_timeline(
            deepcopy(case.timeline or []),
            entry_type="status_change",
            user=user,
            content=f"Status changed from {previous_status} to {request.status}.",
        )
        if request.note:
            case.timeline = _append_timeline(
                deepcopy(case.timeline or []),
                entry_type="note",
                user=user,
                content=request.note.strip(),
            )

        linked_alert_ids = [value for value in case.linked_alert_ids or [] if value]
        if linked_alert_ids and request.status in _CASE_ALERT_OUTCOMES:
            outcome = _CASE_ALERT_OUTCOMES[request.status]
            result = await session.execute(select(Alert).where(Alert.id.in_(linked_alert_ids)))
            for alert in result.scalars().all():
                alert.status = outcome
                alert.case_id = case.id
                alert.resolved_by = _as_uuid(user.user_id)
                alert.resolved_at = datetime.now(UTC)

    await _record_case_audit(
        session,
        case=case,
        user=user,
        action=f"case.{request.action}",
        details=request.model_dump(),
        ip=ip,
    )
    await session.commit()
    await session.refresh(case)
    workspace = await get_case_workspace(session, user=user, case_id=str(case.id))
    return CaseMutationResponse(case=CaseWorkspace.model_validate(workspace))


def _parse_uuid_list(values: list[str] | None) -> list[UUID]:
    if not values:
        return []
    parsed: list[UUID] = []
    for raw in values:
        uid = _as_uuid(raw)
        if uid is not None:
            parsed.append(uid)
    return parsed


def _require_org(user: AuthenticatedUser) -> UUID:
    org_uuid = _as_uuid(user.org_id)
    if org_uuid is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Authenticated user is missing a valid organization id.",
        )
    return org_uuid


async def propose_case(
    session: AsyncSession,
    *,
    user: AuthenticatedUser,
    request: CaseProposeRequest,
    ip: str | None,
) -> CaseMutationResponse:
    org_uuid = _require_org(user)
    case = Case(
        org_id=org_uuid,
        case_ref="",
        title=request.title.strip(),
        summary=(request.summary or request.title).strip(),
        category=request.category,
        severity=request.severity,
        status="open",
        total_exposure=request.total_exposure,
        linked_alert_ids=_parse_uuid_list(request.linked_alert_ids),
        linked_entity_ids=_parse_uuid_list(request.linked_entity_ids),
        timeline=[
            _timeline_entry(
                entry_type="proposed",
                user=user,
                content=f"Case proposed by {user.designation or user.email}.",
            )
        ],
        variant="proposal",
        proposal_decision="pending",
    )
    session.add(case)
    await session.flush()
    await _record_case_audit(
        session,
        case=case,
        user=user,
        action="case.proposed",
        details={
            "title": case.title,
            "severity": case.severity,
            "linked_alerts": len(case.linked_alert_ids or []),
            "linked_entities": len(case.linked_entity_ids or []),
        },
        ip=ip,
    )
    await session.commit()
    await session.refresh(case)
    workspace = await get_case_workspace(session, user=user, case_id=str(case.id))
    return CaseMutationResponse(case=CaseWorkspace.model_validate(workspace))


async def decide_proposal(
    session: AsyncSession,
    *,
    user: AuthenticatedUser,
    case_id: str,
    request: CaseDecideRequest,
    ip: str | None,
) -> CaseMutationResponse:
    if user.role not in {"manager", "admin", "superadmin"}:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only managers or above can decide a case proposal.",
        )
    case = await _fetch_case_or_404(session, case_id)
    if case.variant != "proposal":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Only cases with variant='proposal' can be decided.",
        )
    if case.proposal_decision and case.proposal_decision != "pending":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"This proposal was already {case.proposal_decision}.",
        )
    case.proposal_decision = request.decision
    case.proposal_decided_by = _as_uuid(user.user_id)
    case.proposal_decided_at = datetime.now(UTC)
    if request.decision == "approved":
        case.variant = "standard"
    case.timeline = _append_timeline(
        deepcopy(case.timeline or []),
        entry_type=f"proposal_{request.decision}",
        user=user,
        content=(request.note or f"Proposal {request.decision}.").strip(),
    )
    await _record_case_audit(
        session,
        case=case,
        user=user,
        action=f"case.proposal.{request.decision}",
        details={
            "case_ref": case.case_ref,
            "note": request.note,
        },
        ip=ip,
    )
    await session.commit()
    await session.refresh(case)
    workspace = await get_case_workspace(session, user=user, case_id=str(case.id))
    return CaseMutationResponse(case=CaseWorkspace.model_validate(workspace))


async def create_rfi(
    session: AsyncSession,
    *,
    user: AuthenticatedUser,
    request: CaseRfiRequest,
    ip: str | None,
) -> CaseMutationResponse:
    org_uuid = _require_org(user)
    requested_from_uuid = _as_uuid(request.requested_from)
    if requested_from_uuid is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A valid requested_from user id is required.",
        )
    parent_uuid = _as_uuid(request.parent_case_id) if request.parent_case_id else None
    case = Case(
        org_id=org_uuid,
        case_ref="",
        title=request.title.strip(),
        summary=request.summary.strip(),
        severity="medium",
        status="open",
        linked_alert_ids=_parse_uuid_list(request.linked_alert_ids),
        linked_entity_ids=_parse_uuid_list(request.linked_entity_ids),
        timeline=[
            _timeline_entry(
                entry_type="rfi_opened",
                user=user,
                content=f"RFI opened by {user.designation or user.email}.",
            )
        ],
        variant="rfi",
        parent_case_id=parent_uuid,
        requested_by=_as_uuid(user.user_id),
        requested_from=requested_from_uuid,
    )
    session.add(case)
    await session.flush()
    await _record_case_audit(
        session,
        case=case,
        user=user,
        action="case.rfi.opened",
        details={
            "title": case.title,
            "requested_from": str(requested_from_uuid),
            "parent_case_id": str(parent_uuid) if parent_uuid else None,
        },
        ip=ip,
    )
    await session.commit()
    await session.refresh(case)
    workspace = await get_case_workspace(session, user=user, case_id=str(case.id))
    return CaseMutationResponse(case=CaseWorkspace.model_validate(workspace))
