from typing import Literal

from pydantic import BaseModel

from app.schemas.case import CaseSummary
from app.schemas.investigate import EntitySearchResult
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
    reasons: list[AlertReason] = []
    assigned_to: str | None = None
    case_id: str | None = None


class AlertDetail(AlertSummary):
    graph: NetworkGraph
    entity: EntitySearchResult | None = None


class AlertMutationRequest(BaseModel):
    action: Literal[
        "start_review",
        "assign_to_me",
        "escalate",
        "mark_true_positive",
        "mark_false_positive",
        "create_case",
    ]
    note: str | None = None
    case_title: str | None = None


class AlertMutationResponse(BaseModel):
    alert: AlertDetail
    case: CaseSummary | None = None
