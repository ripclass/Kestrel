"""Schemas for the platform-operator console (pilot-health surface).

Enso-internal, cross-tenant. Gated by the operator email allow-list — see
``app.auth.require_platform_operator``. All read-only.
"""
from typing import Literal

from pydantic import BaseModel, Field

Engagement = Literal["active", "idle", "dormant", "never"]
Trend = Literal["rising", "falling", "flat", "new"]


class PilotHealthCard(BaseModel):
    org_id: str
    org_name: str
    org_type: str
    plan_id: str
    created_at: str | None = None
    seats: int = 0
    seats_logged_in: int = 0
    last_login_at: str | None = None
    last_activity_at: str | None = None
    engagement: Engagement = "never"
    actions_7d: int = 0
    actions_prev_7d: int = 0
    actions_30d: int = 0
    trend: Trend = "flat"
    active_users_7d: int = 0
    strs: int = 0
    alerts: int = 0
    cases: int = 0
    scans: int = 0


class PlatformSummary(BaseModel):
    tenants_total: int = 0
    tenants_bank: int = 0
    tenants_active_7d: int = 0
    seats_total: int = 0
    seats_logged_in: int = 0
    actions_7d: int = 0
    strs_total: int = 0
    alerts_total: int = 0
    cases_total: int = 0
    generated_at: str


class PilotOverviewResponse(BaseModel):
    summary: PlatformSummary
    pilots: list[PilotHealthCard] = Field(default_factory=list)


class PilotUserActivity(BaseModel):
    user_id: str
    full_name: str | None = None
    role: str | None = None
    persona: str | None = None
    designation: str | None = None
    last_login_at: str | None = None
    last_activity_at: str | None = None
    actions_7d: int = 0
    actions_30d: int = 0
    engagement: Engagement = "never"


class PilotAuditEntry(BaseModel):
    created_at: str | None = None
    action: str
    resource_type: str | None = None
    user_id: str | None = None


class PilotDetailResponse(BaseModel):
    card: PilotHealthCard
    users: list[PilotUserActivity] = Field(default_factory=list)
    recent_actions: list[PilotAuditEntry] = Field(default_factory=list)
    action_breakdown: dict[str, int] = Field(default_factory=dict)
