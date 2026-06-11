"""Service-layer tenant scoping helpers.

The engine connects to Postgres as the table-owner role, which bypasses
row-level security (none of the tables set FORCE ROW LEVEL SECURITY).
The GUCs written by ``apply_rls_context`` are therefore not an isolation
boundary on the engine request path — these helpers are. Every service
that reads or mutates an org-owned table must scope through them (or
apply the equivalent inline filter, as kyc/realtime_scoring already do).

Shared-by-design tables stay unscoped: entities, connections, matches,
watchlist_entries, typologies, reference_tables.
"""
from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import false
from sqlalchemy.sql import Select

if TYPE_CHECKING:
    from app.auth import AuthenticatedUser


def is_regulator(user: "AuthenticatedUser") -> bool:
    return (user.org_type or "").strip().lower() == "regulator"


def user_org_uuid(user: "AuthenticatedUser") -> UUID | None:
    raw = (user.org_id or "").strip()
    if not raw:
        return None
    try:
        return UUID(raw)
    except ValueError:
        return None


def scope_to_user(stmt: Select, user: "AuthenticatedUser", org_column) -> Select:
    """Restrict a SELECT on an org-owned table to the caller's org.

    Regulators see everything. A non-regulator without a parseable org
    claim sees nothing (fail closed) rather than everything.
    """
    if is_regulator(user):
        return stmt
    org_uuid = user_org_uuid(user)
    if org_uuid is None:
        return stmt.where(false())
    return stmt.where(org_column == org_uuid)


def ensure_org_access(
    resource_org_id,
    user: "AuthenticatedUser",
    *,
    detail: str = "Not found.",
) -> None:
    """Raise 404 when a non-regulator touches another org's row.

    404 (not 403) so cross-org probes can't confirm a row exists.
    """
    if is_regulator(user):
        return
    org_uuid = user_org_uuid(user)
    if org_uuid is None or resource_org_id is None or str(resource_org_id) != str(org_uuid):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=detail)
