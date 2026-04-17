from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.investigate import ActivityEvent, EntitySearchResult
from app.schemas.network import NetworkGraph

CaseVariant = Literal[
    "standard",
    "proposal",
    "rfi",
    "operation",
    "project",
    "escalated",
    "complaint",
    "adverse_media",
]

ProposalDecision = Literal["approved", "rejected", "pending"]


class CaseSummary(BaseModel):
    id: str
    case_ref: str
    title: str
    summary: str
    severity: str
    status: str
    total_exposure: float
    assigned_to: str | None = None
    linked_entity_ids: list[str]
    linked_alert_ids: list[str] = []
    variant: CaseVariant = "standard"
    parent_case_id: str | None = None
    proposal_decision: ProposalDecision | None = None
    requested_by: str | None = None
    requested_from: str | None = None


class CaseNote(BaseModel):
    actor_user_id: str
    actor_role: str
    note: str
    occurred_at: str


class CaseWorkspace(CaseSummary):
    timeline: list[ActivityEvent]
    evidence_entities: list[EntitySearchResult]
    notes: list[CaseNote]
    graph: NetworkGraph | None = None
    proposal_decided_by: str | None = None
    proposal_decided_at: str | None = None


class CaseMutationRequest(BaseModel):
    action: Literal["add_note", "assign_to_me", "update_status"]
    note: str | None = None
    status: Literal[
        "open",
        "investigating",
        "escalated",
        "pending_action",
        "closed_confirmed",
        "closed_false_positive",
    ] | None = None


class CaseMutationResponse(BaseModel):
    case: CaseWorkspace


class CaseProposeRequest(BaseModel):
    title: str
    summary: str | None = None
    severity: str = "medium"
    category: str | None = None
    linked_alert_ids: list[str] = Field(default_factory=list)
    linked_entity_ids: list[str] = Field(default_factory=list)
    total_exposure: float = 0.0


class CaseDecideRequest(BaseModel):
    decision: Literal["approved", "rejected"]
    note: str | None = None


class CaseRfiRequest(BaseModel):
    title: str
    summary: str
    requested_from: str
    parent_case_id: str | None = None
    linked_alert_ids: list[str] = Field(default_factory=list)
    linked_entity_ids: list[str] = Field(default_factory=list)
