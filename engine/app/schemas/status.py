from typing import Any, Literal

from pydantic import BaseModel, Field


class StatusComponent(BaseModel):
    component: str
    status: Literal["up", "degraded", "down", "unknown"]
    latency_ms: int | None = None
    detail: str | None = None
    observed_at: str | None = None
    uptime_30d: float
    uptime_90d: float


class StatusIncidentView(BaseModel):
    id: str
    started_at: str | None = None
    ended_at: str | None = None
    severity: Literal["minor", "major", "outage"]
    component: str
    summary: str
    message: str | None = None
    is_active: bool


class StatusSummaryResponse(BaseModel):
    status: Literal["up", "degraded", "down"]
    components: list[StatusComponent] = Field(default_factory=list)
    incidents: list[StatusIncidentView] = Field(default_factory=list)
    overall_uptime_30d: float
    generated_at: str


class StatusIncidentInput(BaseModel):
    component: str = Field(..., max_length=32)
    severity: Literal["minor", "major", "outage"]
    summary: str = Field(..., min_length=1, max_length=255)
    message: str | None = Field(default=None, max_length=4000)


class StatusIncidentResolveInput(BaseModel):
    message: str | None = Field(default=None, max_length=4000)


class PlanView(BaseModel):
    plan_id: str
    display_name: str
    price_bdt_yearly: int
    seat_cap: int | None = None
    monthly_transaction_cap: int | None = None
    features: list[str] = Field(default_factory=list)
    on_prem_eligible: bool = False


class TenantPlanView(BaseModel):
    org_id: str
    plan: PlanView
    overrides: dict[str, Any] = Field(default_factory=dict)
    plan_set_at: str | None = None
    plan_set_by: str | None = None
