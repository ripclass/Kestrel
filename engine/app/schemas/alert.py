from pydantic import BaseModel

from app.schemas.network import NetworkGraph


class AlertReason(BaseModel):
    rule: str
    score: int
    weight: float
    explanation: str
    evidence: dict[str, str | int | float | bool]
    recommended_action: str | None = None


class AlertSummary(BaseModel):
    id: str
    title: str
    description: str
    alert_type: str
    risk_score: int
    severity: str
    status: str
    created_at: str
    org_name: str
    entity_id: str


class AlertDetail(AlertSummary):
    reasons: list[AlertReason]
    graph: NetworkGraph
