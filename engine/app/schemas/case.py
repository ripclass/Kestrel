from pydantic import BaseModel

from app.schemas.investigate import ActivityEvent, EntitySearchResult


class CaseSummary(BaseModel):
    id: str
    case_ref: str
    title: str
    summary: str
    severity: str
    status: str
    total_exposure: float
    assigned_to: str
    linked_entity_ids: list[str]


class CaseWorkspace(CaseSummary):
    timeline: list[ActivityEvent]
    evidence_entities: list[EntitySearchResult]
    notes: list[str]
