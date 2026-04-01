from pydantic import BaseModel

from app.schemas.network import NetworkGraph


class EntitySearchResult(BaseModel):
    id: str
    entity_type: str
    display_value: str
    display_name: str | None = None
    canonical_value: str
    risk_score: int
    severity: str
    confidence: float
    status: str
    report_count: int
    reporting_orgs: list[str]
    total_exposure: float
    tags: list[str]


class ReportingHistoryItem(BaseModel):
    org_name: str
    report_ref: str
    reported_at: str
    channel: str
    amount: float


class ActivityEvent(BaseModel):
    id: str
    title: str
    description: str
    occurred_at: str
    actor: str


class EntityDossier(EntitySearchResult):
    narrative: str
    linked_case_ids: list[str]
    linked_alert_ids: list[str]
    reporting_history: list[ReportingHistoryItem]
    connections: list[EntitySearchResult]
    timeline: list[ActivityEvent]
    graph: NetworkGraph
