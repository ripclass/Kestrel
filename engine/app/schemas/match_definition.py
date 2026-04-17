from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

ExecutionStatus = Literal["pending", "running", "completed", "failed"]


class MatchDefinitionCreate(BaseModel):
    name: str
    description: str | None = None
    definition: dict[str, object] = Field(default_factory=dict)
    is_active: bool = True


class MatchDefinitionUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    definition: dict[str, object] | None = None
    is_active: bool | None = None


class MatchDefinitionSummary(BaseModel):
    id: str
    org_id: str
    name: str
    description: str | None = None
    is_active: bool
    created_by: str | None = None
    created_at: datetime
    updated_at: datetime
    last_execution_at: datetime | None = None
    total_hits: int


class MatchExecutionSummary(BaseModel):
    id: str
    definition_id: str
    executed_at: datetime
    executed_by: str | None = None
    hit_count: int
    execution_status: ExecutionStatus
    results_summary: dict[str, object] = Field(default_factory=dict)


class MatchDefinitionDetail(MatchDefinitionSummary):
    definition: dict[str, object] = Field(default_factory=dict)
    recent_executions: list[MatchExecutionSummary] = Field(default_factory=list)


class MatchDefinitionListResponse(BaseModel):
    match_definitions: list[MatchDefinitionSummary]


class MatchDefinitionMutationResponse(BaseModel):
    match_definition: MatchDefinitionDetail


class MatchExecutionResponse(BaseModel):
    execution: MatchExecutionSummary
    match_definition: MatchDefinitionDetail
