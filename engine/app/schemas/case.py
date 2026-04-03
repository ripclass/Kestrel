from typing import Literal

from pydantic import BaseModel

from app.schemas.investigate import ActivityEvent, EntitySearchResult
from app.schemas.network import NetworkGraph


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
