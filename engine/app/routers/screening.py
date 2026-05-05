"""Sanctions / PEP / adverse-media screening API (V2 phase 4).

Four endpoints:

    POST   /screening/entity         -> sanctions + PEP screen against the pool
    POST   /screening/adverse-media  -> ComplyAdvantage adapter (stub when key absent)
    GET    /screening/entries        -> browse watchlist (admin / regulator)
    POST   /screening/entries        -> manual upload (regulator only — BB Domestic etc.)

Auth: Supabase JWT. Bank persona can call the screening endpoints; only
regulator persona can browse / mutate the underlying watchlist.
"""
from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import AuthenticatedUser, get_current_user, require_roles
from app.dependencies import get_current_session
from app.models.audit import AuditLog
from app.models.watchlist import WatchlistEntry
from app.observability import current_request_id
from app.schemas.screening import (
    AdverseMediaHitModel,
    AdverseMediaRequest,
    AdverseMediaResponse,
    ScreeningEntityRequest,
    ScreeningEntityResponse,
    ScreeningMatchModel,
    WatchlistEntryUpload,
    WatchlistEntryView,
    entry_type_is_supported,
    isoformat,
    list_source_is_supported,
)
from app.services.adverse_media import (
    AdverseMediaQuery,
    is_provider_configured,
    search_adverse_media,
)
from app.services.billing import require_feature
from app.services.screening import ScreeningRequest, screen_entity

router = APIRouter()


@router.post("/entity", response_model=ScreeningEntityResponse)
async def screen(
    body: ScreeningEntityRequest,
    user: Annotated[AuthenticatedUser, Depends(require_roles("manager", "admin", "superadmin", "analyst"))],
    session: Annotated[AsyncSession, Depends(get_current_session)],
) -> ScreeningEntityResponse:
    try:
        await require_feature(session, user=user, feature="sanctions")
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_402_PAYMENT_REQUIRED, detail=str(exc)) from exc
    request = ScreeningRequest(
        name=body.name,
        date_of_birth=body.date_of_birth,
        nationality=body.nationality,
        nid=body.nid,
        passport=body.passport,
        screening_lists=[s.upper() for s in (body.screening_lists or [])],
        minimum_match_score=float(body.minimum_match_score),
    )
    matches = await screen_entity(session, request=request)
    request_id = current_request_id() or uuid.uuid4().hex

    session.add(
        AuditLog(
            org_id=uuid.UUID(str(user.org_id)),
            user_id=None,
            action="screening.entity",
            resource_type="watchlist_entries",
            resource_id=None,
            details={
                "name": body.name,
                "minimum_match_score": body.minimum_match_score,
                "screening_lists": body.screening_lists,
                "match_count": len(matches),
                "request_id": request_id,
            },
        )
    )
    await session.commit()

    return ScreeningEntityResponse(
        matches=[ScreeningMatchModel(**match.__dict__) for match in matches],
        screened_at=datetime.now(UTC).isoformat(),
        request_id=request_id,
    )


@router.post("/adverse-media", response_model=AdverseMediaResponse)
async def screen_media(
    body: AdverseMediaRequest,
    user: Annotated[AuthenticatedUser, Depends(require_roles("manager", "admin", "superadmin", "analyst"))],
    session: Annotated[AsyncSession, Depends(get_current_session)],
) -> AdverseMediaResponse:
    try:
        await require_feature(session, user=user, feature="sanctions")
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_402_PAYMENT_REQUIRED, detail=str(exc)) from exc
    hits = await search_adverse_media(
        AdverseMediaQuery(name=body.name, nationality=body.nationality, fuzziness=body.fuzziness)
    )
    request_id = current_request_id() or uuid.uuid4().hex
    provider = "complyadvantage" if is_provider_configured() else "stub"

    session.add(
        AuditLog(
            org_id=uuid.UUID(str(user.org_id)),
            user_id=None,
            action="screening.adverse_media",
            resource_type="adverse_media",
            resource_id=None,
            details={
                "name": body.name,
                "provider": provider,
                "hit_count": len(hits),
                "request_id": request_id,
            },
        )
    )
    await session.commit()

    return AdverseMediaResponse(
        provider=provider,
        hits=[
            AdverseMediaHitModel(
                name=hit.name,
                snippet=hit.snippet,
                url=hit.url,
                published_at=hit.published_at,
                score=hit.score,
            )
            for hit in hits
        ],
        screened_at=datetime.now(UTC).isoformat(),
        request_id=request_id,
    )


@router.get("/entries", response_model=list[WatchlistEntryView])
async def list_entries(
    user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_current_session)],
    list_source: str | None = None,
    limit: int = 100,
    include_removed: bool = False,
) -> list[WatchlistEntryView]:
    capped = max(1, min(int(limit or 100), 500))
    stmt = select(WatchlistEntry).order_by(desc(WatchlistEntry.ingested_at)).limit(capped)
    if list_source:
        if not list_source_is_supported(list_source):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Unsupported list_source '{list_source}'.",
            )
        stmt = stmt.where(WatchlistEntry.list_source == list_source.upper())
    if not include_removed:
        stmt = stmt.where(WatchlistEntry.removed_at.is_(None))

    result = await session.execute(stmt)
    rows = result.scalars().all()
    return [
        WatchlistEntryView(
            id=str(row.id),
            list_source=row.list_source,
            list_version=row.list_version,
            entry_type=row.entry_type,
            primary_name=row.primary_name,
            aliases=list(row.aliases or []),
            date_of_birth=row.date_of_birth,
            nationality=row.nationality,
            identifiers=row.identifiers or {},
            addresses=row.addresses or [],
            reason=row.reason,
            ingested_at=isoformat(row.ingested_at),
            removed_at=isoformat(row.removed_at),
        )
        for row in rows
    ]


@router.post("/entries", response_model=WatchlistEntryView)
async def upload_entry(
    body: WatchlistEntryUpload,
    user: Annotated[AuthenticatedUser, Depends(require_roles("admin", "superadmin"))],
    session: Annotated[AsyncSession, Depends(get_current_session)],
) -> WatchlistEntryView:
    if (user.org_type or "").lower() != "regulator":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only regulator-org admins can upload watchlist entries.",
        )
    if not list_source_is_supported(body.list_source):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Unsupported list_source '{body.list_source}'.",
        )
    if not entry_type_is_supported(body.entry_type):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Unsupported entry_type '{body.entry_type}'.",
        )

    entry = WatchlistEntry(
        id=uuid.uuid4(),
        list_source=body.list_source.upper(),
        list_version=body.list_version,
        entry_type=body.entry_type.lower(),
        primary_name=body.primary_name,
        aliases=list(body.aliases or []),
        date_of_birth=body.date_of_birth,
        nationality=body.nationality,
        identifiers=body.identifiers or {},
        addresses=body.addresses or [],
        reason=body.reason,
        raw_record={"source": "manual_upload", "uploaded_by": str(user.user_id)},
    )
    session.add(entry)
    session.add(
        AuditLog(
            org_id=uuid.UUID(str(user.org_id)),
            user_id=None,
            action="screening.upload_entry",
            resource_type="watchlist_entries",
            resource_id=entry.id,
            details={
                "list_source": entry.list_source,
                "list_version": entry.list_version,
                "primary_name": entry.primary_name,
                "request_id": current_request_id(),
            },
        )
    )
    await session.commit()

    return WatchlistEntryView(
        id=str(entry.id),
        list_source=entry.list_source,
        list_version=entry.list_version,
        entry_type=entry.entry_type,
        primary_name=entry.primary_name,
        aliases=list(entry.aliases or []),
        date_of_birth=entry.date_of_birth,
        nationality=entry.nationality,
        identifiers=entry.identifiers or {},
        addresses=entry.addresses or [],
        reason=entry.reason,
        ingested_at=isoformat(entry.ingested_at),
        removed_at=isoformat(entry.removed_at),
    )
