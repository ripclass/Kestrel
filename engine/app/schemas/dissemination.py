from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

RecipientType = Literal[
    "law_enforcement",
    "regulator",
    "foreign_fiu",
    "prosecutor",
    "other",
]

Classification = Literal[
    "public",
    "internal",
    "confidential",
    "restricted",
    "secret",
]


class DisseminationCreate(BaseModel):
    recipient_agency: str
    recipient_type: RecipientType
    subject_summary: str
    linked_report_ids: list[str] = Field(default_factory=list)
    linked_entity_ids: list[str] = Field(default_factory=list)
    linked_case_ids: list[str] = Field(default_factory=list)
    classification: Classification = "confidential"
    metadata: dict[str, object] = Field(default_factory=dict)


class DisseminationSummary(BaseModel):
    id: str
    org_id: str
    org_name: str
    dissemination_ref: str
    recipient_agency: str
    recipient_type: RecipientType
    subject_summary: str
    classification: Classification
    disseminated_by: str | None = None
    disseminated_at: datetime
    linked_report_count: int
    linked_entity_count: int
    linked_case_count: int
    created_at: datetime


class DisseminationDetail(DisseminationSummary):
    linked_report_ids: list[str] = Field(default_factory=list)
    linked_entity_ids: list[str] = Field(default_factory=list)
    linked_case_ids: list[str] = Field(default_factory=list)
    metadata: dict[str, object] = Field(default_factory=dict)


class DisseminationListResponse(BaseModel):
    disseminations: list[DisseminationSummary]


class DisseminationMutationResponse(BaseModel):
    dissemination: DisseminationDetail
