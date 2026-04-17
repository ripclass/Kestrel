from datetime import datetime

from pydantic import BaseModel, Field


class DiagramCreate(BaseModel):
    title: str
    description: str | None = None
    graph_definition: dict[str, object] = Field(default_factory=dict)
    linked_case_id: str | None = None
    linked_str_id: str | None = None


class DiagramUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    graph_definition: dict[str, object] | None = None
    linked_case_id: str | None = None
    linked_str_id: str | None = None


class DiagramSummary(BaseModel):
    id: str
    org_id: str
    created_by: str | None = None
    title: str
    description: str | None = None
    linked_case_id: str | None = None
    linked_str_id: str | None = None
    created_at: datetime
    updated_at: datetime


class DiagramDetail(DiagramSummary):
    graph_definition: dict[str, object] = Field(default_factory=dict)


class DiagramListResponse(BaseModel):
    diagrams: list[DiagramSummary]


class DiagramMutationResponse(BaseModel):
    diagram: DiagramDetail
