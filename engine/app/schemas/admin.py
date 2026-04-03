from pydantic import BaseModel, Field


class AdminSummaryResponse(BaseModel):
    org_name: str
    org_type: str
    plan: str
    team_members: int
    active_rules: int
    total_rules: int
    api_integrations: int
    cross_bank_hits: int
    detection_runs: int
    synthetic_backfill_available: bool


class AdminSettingsResponse(BaseModel):
    org_name: str
    org_type: str
    plan: str
    bank_code: str | None = None
    auth_configured: bool
    storage_configured: bool
    demo_mode_enabled: bool
    goaml_sync_enabled: bool
    goaml_base_url_configured: bool
    environment: str
    app_version: str
    uploads_bucket: str
    exports_bucket: str
    synthetic_backfill_available: bool


class AdminTeamMember(BaseModel):
    id: str
    full_name: str
    designation: str | None = None
    role: str
    persona: str


class AdminTeamResponse(BaseModel):
    members: list[AdminTeamMember] = Field(default_factory=list)


class AdminRuleSummary(BaseModel):
    code: str
    name: str
    description: str
    category: str
    source: str
    is_active: bool
    is_system: bool
    weight: float
    version: int
    threshold: float | None = None


class AdminRulesResponse(BaseModel):
    rules: list[AdminRuleSummary] = Field(default_factory=list)


class AdminRuleMutationRequest(BaseModel):
    is_active: bool | None = None
    weight: float | None = Field(default=None, ge=0.1, le=100.0)
    threshold: float | None = Field(default=None, ge=0.0, le=1000.0)
    description: str | None = None


class AdminRuleMutationResponse(BaseModel):
    rule: AdminRuleSummary


class AdminIntegrationSummary(BaseModel):
    id: str
    name: str
    status: str
    detail: str
    scope: list[str] = Field(default_factory=list)
    last_used_at: str | None = None


class AdminIntegrationsResponse(BaseModel):
    integrations: list[AdminIntegrationSummary] = Field(default_factory=list)


class AdminTeamUpdateRequest(BaseModel):
    role: str | None = None
    persona: str | None = None
    designation: str | None = None


class AdminTeamMutationResponse(BaseModel):
    member: AdminTeamMember


class SyntheticBackfillPlanResponse(BaseModel):
    dataset_root: str
    statements: int
    entities: int
    matches: int
    transactions: int
    connections: int


class SyntheticBackfillResultResponse(BaseModel):
    dataset_root: str
    organizations: int
    entities: int
    connections: int
    matches: int
    transactions: int
    str_reports: int
    alerts: int
    cases: int
    reporting_orgs: dict[str, int] = Field(default_factory=dict)


class AdminMaintenanceResponse(BaseModel):
    action: str
    applied: bool
    detail: str
