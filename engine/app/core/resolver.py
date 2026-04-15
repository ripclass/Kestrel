"""Entity resolver.

Turns identifiers (account, phone, wallet, nid, person, business) into
canonical shared-intelligence ``Entity`` rows. Used by the STR submission
pipeline and the scan detection pipeline.
"""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.connection import Connection
from app.models.entity import Entity
from app.models.str_report import STRReport

_CONFIDENCE_BY_SOURCE: dict[str, float] = {
    "str_cross_ref": 0.7,
    "manual": 0.8,
    "pattern_scan": 0.6,
    "system": 0.5,
}

_FUZZY_ELIGIBLE_TYPES = {"person", "business"}
_FUZZY_SIMILARITY_THRESHOLD = 0.6


def normalize_identifier(entity_type: str, raw_value: str) -> str:
    """Return the canonical form of ``raw_value`` for the given ``entity_type``.

    - account / wallet: strip whitespace and separators, uppercase.
    - phone: strip whitespace/punctuation; if 12+ digits starting with 880 prepend ``+``.
    - nid: digits only.
    - person / business: lowercase, collapse whitespace.
    - anything else: strip + lowercase.

    Raises ``ValueError`` when the normalized value is empty.
    """
    if raw_value is None:
        raise ValueError("Identifier value is required")
    value = str(raw_value).strip()
    if not value:
        raise ValueError("Identifier value is required")

    if entity_type in {"account", "wallet"}:
        cleaned = re.sub(r"[\s\-]+", "", value).upper()
    elif entity_type == "phone":
        digits_plus = re.sub(r"[^\d+]", "", value)
        if digits_plus.startswith("+"):
            cleaned = digits_plus
        elif digits_plus.startswith("880") and len(digits_plus) >= 12:
            cleaned = "+" + digits_plus
        else:
            cleaned = digits_plus
    elif entity_type == "nid":
        cleaned = re.sub(r"[^\d]", "", value)
    elif entity_type in _FUZZY_ELIGIBLE_TYPES:
        cleaned = re.sub(r"\s+", " ", value).strip().lower()
    else:
        cleaned = value.lower()

    if not cleaned:
        raise ValueError(f"Normalized identifier is empty for type {entity_type}")
    return cleaned


async def _find_exact_entity(
    session: AsyncSession,
    *,
    entity_type: str,
    canonical_value: str,
) -> Entity | None:
    stmt = (
        select(Entity)
        .where(Entity.entity_type == entity_type)
        .where(Entity.canonical_value == canonical_value)
        .limit(1)
    )
    result = await session.execute(stmt)
    return result.scalars().first()


async def _find_fuzzy_entity(
    session: AsyncSession,
    *,
    entity_type: str,
    display_name: str,
) -> Entity | None:
    """Fuzzy-match on display_name using pg_trgm similarity.

    Only used for ``person`` and ``business`` entity types. Falls back to ``None``
    silently if pg_trgm is not available or the session cannot execute the query
    (useful for unit tests with a mock session).
    """
    try:
        stmt = (
            select(Entity)
            .where(Entity.entity_type == entity_type)
            .where(func.similarity(Entity.display_name, display_name) >= _FUZZY_SIMILARITY_THRESHOLD)
            .order_by(func.similarity(Entity.display_name, display_name).desc())
            .limit(1)
        )
        result = await session.execute(stmt)
        return result.scalars().first()
    except Exception:
        return None


def _update_existing(
    entity: Entity,
    *,
    org_id: uuid.UUID,
    source: str,
) -> Entity:
    now = datetime.now(UTC)
    entity.last_seen = now
    entity.report_count = (entity.report_count or 0) + 1
    reporting = list(entity.reporting_orgs or [])
    if org_id not in reporting:
        reporting.append(org_id)
    entity.reporting_orgs = reporting
    if not entity.first_seen:
        entity.first_seen = now
    if source and (not entity.source or entity.source == "system"):
        entity.source = source
    return entity


def _build_new_entity(
    *,
    entity_type: str,
    canonical_value: str,
    display_value: str,
    display_name: str | None,
    org_id: uuid.UUID,
    source: str,
) -> Entity:
    now = datetime.now(UTC)
    confidence = _CONFIDENCE_BY_SOURCE.get(source, 0.5)
    return Entity(
        id=uuid.uuid4(),
        entity_type=entity_type,
        canonical_value=canonical_value,
        display_value=display_value,
        display_name=display_name,
        confidence=confidence,
        source=source,
        status="active",
        reporting_orgs=[org_id],
        report_count=1,
        first_seen=now,
        last_seen=now,
        total_exposure=0,
        tags=[],
        metadata_json={},
    )


async def resolve_identifier(
    session: AsyncSession,
    *,
    entity_type: str,
    raw_value: str,
    org_id: uuid.UUID,
    source: str = "str_cross_ref",
    display_name: str | None = None,
) -> Entity:
    """Resolve one identifier to an ``Entity`` row, creating it if missing.

    - Normalizes the raw value to its canonical form.
    - Looks for an exact ``(entity_type, canonical_value)`` match.
    - For person/business types, falls back to fuzzy match on ``display_name``.
    - On hit: updates ``last_seen``, ``report_count``, ``reporting_orgs``.
    - On miss: inserts a new Entity with source-based initial confidence.

    The caller owns the surrounding transaction; this function calls
    ``session.flush()`` after adding new entities so the returned object has
    a populated ``id``.
    """
    canonical = normalize_identifier(entity_type, raw_value)

    existing = await _find_exact_entity(
        session, entity_type=entity_type, canonical_value=canonical
    )
    if existing is None and entity_type in _FUZZY_ELIGIBLE_TYPES and display_name:
        existing = await _find_fuzzy_entity(
            session, entity_type=entity_type, display_name=display_name
        )

    if existing is not None:
        return _update_existing(existing, org_id=org_id, source=source)

    entity = _build_new_entity(
        entity_type=entity_type,
        canonical_value=canonical,
        display_value=str(raw_value).strip(),
        display_name=display_name,
        org_id=org_id,
        source=source,
    )
    session.add(entity)
    await session.flush()
    return entity


@dataclass
class _IdentifierSlot:
    entity_type: str
    raw_value: str
    display_name: str | None


def _extract_identifier_slots(str_report: STRReport | Any) -> list[_IdentifierSlot]:
    slots: list[_IdentifierSlot] = []
    subject_name = getattr(str_report, "subject_name", None)

    subject_account = getattr(str_report, "subject_account", None)
    if subject_account:
        slots.append(_IdentifierSlot("account", subject_account, subject_name))

    subject_phone = getattr(str_report, "subject_phone", None)
    if subject_phone:
        slots.append(_IdentifierSlot("phone", subject_phone, subject_name))

    subject_wallet = getattr(str_report, "subject_wallet", None)
    if subject_wallet:
        slots.append(_IdentifierSlot("wallet", subject_wallet, subject_name))

    subject_nid = getattr(str_report, "subject_nid", None)
    if subject_nid:
        slots.append(_IdentifierSlot("nid", subject_nid, subject_name))

    if subject_name:
        slots.append(_IdentifierSlot("person", subject_name, subject_name))

    return slots


async def _upsert_same_owner_connection(
    session: AsyncSession,
    *,
    from_entity: Entity,
    to_entity: Entity,
) -> None:
    if from_entity.id == to_entity.id:
        return
    stmt = (
        select(Connection)
        .where(Connection.from_entity_id == from_entity.id)
        .where(Connection.to_entity_id == to_entity.id)
        .where(Connection.relation == "same_owner")
        .limit(1)
    )
    try:
        result = await session.execute(stmt)
        existing = result.scalars().first()
    except Exception:
        existing = None
    if existing is not None:
        existing.last_seen = datetime.now(UTC)
        return

    now = datetime.now(UTC)
    connection = Connection(
        id=uuid.uuid4(),
        from_entity_id=from_entity.id,
        to_entity_id=to_entity.id,
        relation="same_owner",
        weight=1.0,
        evidence={"source": "str_cross_ref"},
        first_seen=now,
        last_seen=now,
    )
    session.add(connection)


async def resolve_identifiers_from_str(
    session: AsyncSession,
    *,
    str_report: STRReport | Any,
    org_id: uuid.UUID,
) -> list[Entity]:
    """Resolve every identifier on ``str_report`` and link them pairwise.

    Emits ``same_owner`` directed connections between every pair of non-person
    entities so the shared graph picks up the relationship. Returns the full
    list of resolved entities (new + existing, including the person slot if any).
    """
    slots = _extract_identifier_slots(str_report)
    resolved: list[Entity] = []
    for slot in slots:
        try:
            entity = await resolve_identifier(
                session,
                entity_type=slot.entity_type,
                raw_value=slot.raw_value,
                org_id=org_id,
                source="str_cross_ref",
                display_name=slot.display_name,
            )
        except ValueError:
            continue
        resolved.append(entity)

    graph_entities = [e for e in resolved if e.entity_type != "person"]
    for i, a in enumerate(graph_entities):
        for b in graph_entities[i + 1:]:
            await _upsert_same_owner_connection(session, from_entity=a, to_entity=b)
            await _upsert_same_owner_connection(session, from_entity=b, to_entity=a)

    return resolved
