from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import case, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import AuthenticatedUser
from app.core.graph.builder import build_graph
from app.core.graph.export import export_graph
from app.models.alert import Alert
from app.models.case import Case
from app.models.connection import Connection
from app.models.entity import Entity
from app.models.match import Match
from app.models.org import Organization
from app.models.str_report import STRReport


def _as_float(value: object) -> float:
    if value is None:
        return 0.0
    return float(value)


def _iso(value: datetime | None) -> str:
    if value is None:
        return datetime.now(UTC).isoformat()
    return value.astimezone(UTC).isoformat()


def _safe_int(value: int | None) -> int:
    return value or 0


def _safe_severity(value: str | None) -> str:
    return value or "low"


def _safe_confidence(value: object) -> float:
    if value is None:
        return 0.5
    return float(value)


def _candidate_org_ids(values: list[str] | None) -> set[str]:
    return {str(value) for value in (values or []) if value}


async def _load_org_name_map(session: AsyncSession, org_ids: set[str]) -> dict[str, str]:
    parsed_ids: list[UUID] = []
    for value in org_ids:
        try:
            parsed_ids.append(UUID(value))
        except ValueError:
            continue

    if not parsed_ids:
        return {}

    result = await session.execute(select(Organization.id, Organization.name).where(Organization.id.in_(parsed_ids)))
    return {str(org_id): str(name) for org_id, name in result.all()}


def _label_orgs(values: list[str] | None, org_name_map: dict[str, str]) -> list[str]:
    labels: list[str] = []
    peer_index = 1

    for value in values or []:
        normalized = str(value)
        if normalized in org_name_map:
            labels.append(org_name_map[normalized])
            continue

        try:
            UUID(normalized)
            labels.append(f"Peer institution {peer_index}")
            peer_index += 1
        except ValueError:
            labels.append(normalized)

    return labels


def _serialize_entity_summary(entity: Entity, org_name_map: dict[str, str]) -> dict[str, object]:
    return {
        "id": str(entity.id),
        "entity_type": entity.entity_type,
        "display_value": entity.display_value,
        "display_name": entity.display_name,
        "canonical_value": entity.canonical_value,
        "risk_score": _safe_int(entity.risk_score),
        "severity": _safe_severity(entity.severity),
        "confidence": _safe_confidence(entity.confidence),
        "status": entity.status,
        "report_count": entity.report_count,
        "reporting_orgs": _label_orgs(entity.reporting_orgs, org_name_map),
        "total_exposure": _as_float(entity.total_exposure),
        "tags": list(entity.tags or []),
        "first_seen": _iso(entity.first_seen),
        "last_seen": _iso(entity.last_seen),
    }


def _build_entity_report_filters(entity: Entity) -> list[object]:
    values = {entity.canonical_value, entity.display_value}
    if entity.display_name:
        values.add(entity.display_name)
    candidates = [value for value in values if value]

    filters: list[object] = [STRReport.matched_entity_ids.any(entity.id)]
    if entity.entity_type == "account":
        filters.append(STRReport.subject_account.in_(candidates))
    elif entity.entity_type == "phone":
        filters.append(STRReport.subject_phone.in_(candidates))
    elif entity.entity_type == "wallet":
        filters.append(STRReport.subject_wallet.in_(candidates))
    elif entity.entity_type == "nid":
        filters.append(STRReport.subject_nid.in_(candidates))
    elif entity.entity_type in {"person", "business"} and entity.display_name:
        filters.append(STRReport.subject_name.ilike(f"%{entity.display_name}%"))

    return filters


async def _fetch_entity_or_404(session: AsyncSession, entity_id: str) -> Entity:
    try:
        parsed_id = UUID(entity_id)
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Entity not found.") from error

    entity = await session.get(Entity, parsed_id)
    if entity is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Entity not found.")
    return entity


async def _fetch_related_reports(
    session: AsyncSession,
    entity: Entity,
) -> list[tuple[STRReport, str]]:
    stmt = (
        select(STRReport, Organization.name.label("org_name"))
        .join(Organization, Organization.id == STRReport.org_id)
        .where(or_(*_build_entity_report_filters(entity)))
        .order_by(STRReport.reported_at.desc().nullslast(), STRReport.created_at.desc())
    )
    result = await session.execute(stmt)

    rows: list[tuple[STRReport, str]] = []
    seen: set[str] = set()
    for report, org_name in result.all():
        report_id = str(report.id)
        if report_id in seen:
            continue
        seen.add(report_id)
        rows.append((report, str(org_name)))
    return rows


async def _fetch_connections(session: AsyncSession, entity_id: UUID) -> list[Connection]:
    result = await session.execute(
        select(Connection)
        .where(or_(Connection.from_entity_id == entity_id, Connection.to_entity_id == entity_id))
        .order_by(Connection.weight.desc(), Connection.last_seen.desc().nullslast())
        .limit(24)
    )
    return list(result.scalars().all())


async def _fetch_entities_by_ids(session: AsyncSession, entity_ids: set[str]) -> dict[str, Entity]:
    parsed_ids: list[UUID] = []
    for value in entity_ids:
        try:
            parsed_ids.append(UUID(value))
        except ValueError:
            continue

    if not parsed_ids:
        return {}

    result = await session.execute(select(Entity).where(Entity.id.in_(parsed_ids)))
    return {str(entity.id): entity for entity in result.scalars().all()}


def _build_reporting_history(rows: list[tuple[STRReport, str]]) -> list[dict[str, object]]:
    history: list[dict[str, object]] = []
    for report, org_name in rows[:10]:
        history.append(
            {
                "org_name": org_name,
                "report_ref": report.report_ref,
                "reported_at": _iso(report.reported_at or report.created_at),
                "channel": report.primary_channel or "unknown",
                "amount": _as_float(report.total_amount),
            }
        )
    return history


def _build_narrative(
    entity: Entity,
    reporting_history: list[dict[str, object]],
    linked_alert_ids: list[str],
    linked_case_ids: list[str],
) -> str:
    institution_count = len({item["org_name"] for item in reporting_history})
    return (
        f"{entity.display_value} is a shared intelligence subject with {entity.report_count} linked STRs, "
        f"{institution_count} reporting institutions, and estimated exposure of BDT {_as_float(entity.total_exposure):,.0f}. "
        f"{len(linked_alert_ids)} alerts and {len(linked_case_ids)} cases reference this entity in the current investigation layer."
    )


def _build_timeline(
    entity: Entity,
    reports: list[tuple[STRReport, str]],
    alerts: list[Alert],
    cases: list[Case],
) -> list[dict[str, str]]:
    events: list[dict[str, str]] = []

    for report, org_name in reports[:6]:
        channel = report.primary_channel or "unknown channel"
        events.append(
            {
                "id": f"report-{report.id}",
                "title": f"STR {report.report_ref} {report.status}",
                "description": f"{org_name} reported {entity.display_value} via {channel} in category {report.category}.",
                "occurred_at": _iso(report.reported_at or report.created_at),
                "actor": org_name,
            }
        )

    for alert in alerts[:6]:
        events.append(
            {
                "id": f"alert-{alert.id}",
                "title": alert.title,
                "description": alert.description or f"{alert.alert_type} alert remains {alert.status}.",
                "occurred_at": _iso(alert.created_at),
                "actor": "Kestrel Engine",
            }
        )

    for case in cases[:4]:
        events.append(
            {
                "id": f"case-{case.id}",
                "title": f"Case {case.case_ref}",
                "description": case.summary or case.title,
                "occurred_at": _iso(case.updated_at or case.created_at),
                "actor": "Case management",
            }
        )

    return sorted(events, key=lambda item: item["occurred_at"], reverse=True)[:12]


async def get_network_graph(
    session: AsyncSession,
    *,
    user: AuthenticatedUser,
    entity_id: str,
) -> dict[str, object]:
    focus = await _fetch_entity_or_404(session, entity_id)
    first_hop = await _fetch_connections(session, focus.id)

    neighbor_ids = {
        str(connection.from_entity_id if connection.to_entity_id == focus.id else connection.to_entity_id)
        for connection in first_hop
    }
    graph_entity_ids = {str(focus.id), *neighbor_ids}

    second_hop_connections: list[Connection] = []
    if neighbor_ids:
        parsed_neighbor_ids = [UUID(value) for value in neighbor_ids]
        result = await session.execute(
            select(Connection)
            .where(
                or_(
                    Connection.from_entity_id.in_(parsed_neighbor_ids),
                    Connection.to_entity_id.in_(parsed_neighbor_ids),
                )
            )
            .order_by(Connection.weight.desc(), Connection.last_seen.desc().nullslast())
            .limit(48)
        )
        second_hop_connections = list(result.scalars().all())
        for connection in second_hop_connections:
            graph_entity_ids.add(str(connection.from_entity_id))
            graph_entity_ids.add(str(connection.to_entity_id))

    entity_map = await _fetch_entities_by_ids(session, graph_entity_ids)
    graph = build_graph(list(entity_map.values()), [*first_hop, *second_hop_connections])
    org_name_map = await _load_org_name_map(
        session,
        {org_id for item in entity_map.values() for org_id in _candidate_org_ids(item.reporting_orgs)},
    )
    del org_name_map
    return export_graph(graph, str(focus.id))


async def search_entities(
    session: AsyncSession,
    *,
    user: AuthenticatedUser,
    query: str,
    limit: int = 24,
) -> list[dict[str, object]]:
    normalized = query.strip().lower()
    stmt = select(Entity)

    if normalized:
        match_rank = case(
            (func.lower(Entity.canonical_value) == normalized, 0),
            (func.lower(Entity.display_value) == normalized, 0),
            else_=1,
        )
        stmt = stmt.where(
            or_(
                Entity.canonical_value.ilike(f"%{normalized}%"),
                Entity.display_value.ilike(f"%{normalized}%"),
                Entity.display_name.ilike(f"%{normalized}%"),
            )
        ).order_by(
            match_rank,
            Entity.risk_score.desc().nullslast(),
            Entity.report_count.desc(),
            Entity.last_seen.desc().nullslast(),
        )
    else:
        stmt = stmt.order_by(Entity.risk_score.desc().nullslast(), Entity.report_count.desc(), Entity.last_seen.desc().nullslast())

    result = await session.execute(stmt.limit(limit))
    entities = list(result.scalars().all())
    org_name_map = await _load_org_name_map(
        session,
        {org_id for entity in entities for org_id in _candidate_org_ids(entity.reporting_orgs)},
    )
    return [_serialize_entity_summary(entity, org_name_map) for entity in entities]


async def get_entity_dossier(
    session: AsyncSession,
    *,
    user: AuthenticatedUser,
    entity_id: str,
) -> dict[str, object]:
    entity = await _fetch_entity_or_404(session, entity_id)
    reports = await _fetch_related_reports(session, entity)
    alerts_result = await session.execute(select(Alert).where(Alert.entity_id == entity.id).order_by(Alert.created_at.desc()))
    alerts = list(alerts_result.scalars().all())
    cases_result = await session.execute(
        select(Case).where(Case.linked_entity_ids.any(str(entity.id))).order_by(Case.updated_at.desc().nullslast(), Case.created_at.desc())
    )
    cases = list(cases_result.scalars().all())
    connections = await _fetch_connections(session, entity.id)

    connected_ids = {
        str(connection.from_entity_id if connection.to_entity_id == entity.id else connection.to_entity_id)
        for connection in connections
    }
    connected_entities = await _fetch_entities_by_ids(session, connected_ids)
    org_name_map = await _load_org_name_map(
        session,
        {
            *{org_id for org_id in _candidate_org_ids(entity.reporting_orgs)},
            *{org_id for item in connected_entities.values() for org_id in _candidate_org_ids(item.reporting_orgs)},
        },
    )

    linked_alert_ids = [str(alert.id) for alert in alerts]
    linked_case_ids = [str(case.id) for case in cases]
    reporting_history = _build_reporting_history(reports)

    return {
        **_serialize_entity_summary(entity, org_name_map),
        "narrative": _build_narrative(entity, reporting_history, linked_alert_ids, linked_case_ids),
        "linked_case_ids": linked_case_ids,
        "linked_alert_ids": linked_alert_ids,
        "reporting_history": reporting_history,
        "connections": [
            _serialize_entity_summary(connected_entities[entity_id], org_name_map)
            for entity_id in connected_ids
            if entity_id in connected_entities
        ],
        "timeline": _build_timeline(entity, reports, alerts, cases),
        "graph": await get_network_graph(session, user=user, entity_id=str(entity.id)),
    }


async def list_matches(session: AsyncSession, *, user: AuthenticatedUser) -> list[dict[str, object]]:
    result = await session.execute(
        select(Match).order_by(Match.risk_score.desc().nullslast(), Match.detected_at.desc().nullslast(), Match.match_count.desc())
    )
    matches = list(result.scalars().all())
    org_name_map = await _load_org_name_map(
        session,
        {org_id for match in matches for org_id in _candidate_org_ids(match.involved_org_ids)},
    )

    payload: list[dict[str, object]] = []
    for match in matches:
        payload.append(
            {
                "id": str(match.id),
                "entity_id": str(match.entity_id) if match.entity_id else "",
                "match_key": match.match_key,
                "match_type": match.match_type,
                "involved_orgs": _label_orgs(match.involved_org_ids, org_name_map),
                "involved_str_ids": [str(value) for value in match.involved_str_ids or []],
                "match_count": match.match_count,
                "total_exposure": _as_float(match.total_exposure),
                "risk_score": _safe_int(match.risk_score),
                "severity": _safe_severity(match.severity),
                "status": match.status,
            }
        )
    return payload
