"""Subject creation — manual entry via goAML-style New Subjects forms.

Wraps the existing resolver so the /intelligence/entities/new UI can
author accounts, persons, and entities explicitly without going through
an STR or scan. Every identifier in the submission is resolved (created
if missing, returned if already present) and pairwise same_owner
connections are emitted across the non-person entities so the graph
picks up the linkage.
"""
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import AuthenticatedUser
from app.core.resolver import link_subject_group, resolve_identifier
from app.models.audit import AuditLog
from app.models.entity import Entity
from app.schemas.new_subject import (
    NewSubjectRequest,
    NewSubjectResolvedEntity,
    NewSubjectResponse,
)


def _as_uuid(value: str | None) -> UUID | None:
    if not value:
        return None
    try:
        return UUID(value)
    except ValueError:
        return None


def _require_uuid(value: str | None, detail: str) -> UUID:
    parsed = _as_uuid(value)
    if parsed is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)
    return parsed


async def create_subject(
    session: AsyncSession,
    *,
    user: AuthenticatedUser,
    payload: NewSubjectRequest,
    ip: str | None,
) -> NewSubjectResponse:
    if not payload.identifiers:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one identifier is required.",
        )
    org_uuid = _require_uuid(user.org_id, "Authenticated user is missing a valid organization id.")

    resolved: list[Entity] = []
    was_new: list[bool] = []
    for identifier in payload.identifiers:
        value = (identifier.value or "").strip()
        if not value:
            continue
        try:
            before = await session.execute(
                Entity.__table__.select().where(
                    (Entity.canonical_value == value.upper())
                    & (Entity.entity_type == identifier.entity_type)
                )
            )
            existed = before.first() is not None
        except Exception:
            existed = False
        try:
            entity = await resolve_identifier(
                session,
                entity_type=identifier.entity_type,
                raw_value=value,
                org_id=org_uuid,
                source="manual",
                display_name=identifier.display_name,
            )
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
            ) from exc
        resolved.append(entity)
        was_new.append(not existed)

    if not resolved:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No usable identifiers in submission.",
        )

    connections = await link_subject_group(session, entities=resolved)

    # Pick the first entity whose entity_type matches primary_kind; fall back
    # to the first resolved identifier.
    primary = next(
        (entity for entity in resolved if entity.entity_type == payload.primary_kind),
        resolved[0],
    )

    session.add(
        AuditLog(
            org_id=org_uuid,
            user_id=_as_uuid(user.user_id),
            action="subject.created",
            resource_type="entity",
            resource_id=primary.id,
            details={
                "primary_kind": payload.primary_kind,
                "resolved_count": len(resolved),
                "connections_created": connections,
                "identifier_types": [ident.entity_type for ident in payload.identifiers],
            },
            ip=ip,
        )
    )
    await session.commit()
    for entity in resolved:
        await session.refresh(entity)

    return NewSubjectResponse(
        primary_entity_id=str(primary.id),
        resolved=[
            NewSubjectResolvedEntity(
                id=str(entity.id),
                entity_type=entity.entity_type,
                display_value=entity.display_value,
                display_name=entity.display_name,
                created=created,
            )
            for entity, created in zip(resolved, was_new)
        ],
        connections_created=connections,
    )
