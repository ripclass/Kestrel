from pydantic import BaseModel


class CrossBankMatch(BaseModel):
    id: str
    entity_id: str
    match_key: str
    match_type: str
    involved_orgs: list[str]
    involved_str_ids: list[str]
    match_count: int
    total_exposure: float
    risk_score: int
    severity: str
    status: str


class TypologySummary(BaseModel):
    id: str
    title: str
    category: str
    channels: list[str]
    indicators: list[str]
    narrative: str


class CrossBankSummary(BaseModel):
    window_days: int
    entities_flagged_across_banks: int
    new_this_week: int
    high_risk_cross_institution: int
    total_exposure: float
    cross_bank_alerts_count: int
    visible_matches_count: int
    persona_view: str  # "regulator" | "bank"


class CrossBankMatchView(BaseModel):
    id: str
    entity_id: str
    match_key: str
    match_type: str
    involved_orgs: list[str]
    bank_count: int
    match_count: int
    total_exposure: float
    risk_score: int
    severity: str
    status: str
    first_seen: str | None = None


class CrossBankSeverityBreakdown(BaseModel):
    critical: int = 0
    high: int = 0
    medium: int = 0
    low: int = 0


class CrossBankHeatmapBucket(BaseModel):
    label: str
    match_count: int
    severity_breakdown: CrossBankSeverityBreakdown


class CrossBankHeatmap(BaseModel):
    window_days: int
    buckets: list[CrossBankHeatmapBucket]
    persona_view: str


class CrossBankEntityRow(BaseModel):
    entity_id: str
    display: str
    entity_type: str
    risk_score: int
    severity: str
    bank_count: int
    involved_orgs: list[str]
    total_exposure: float
