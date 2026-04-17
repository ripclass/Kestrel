from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

QueryType = Literal[
    "entity_search",
    "transaction_search",
    "str_filter",
    "alert_filter",
    "case_filter",
    "custom",
]


class SavedQueryCreate(BaseModel):
    name: str
    description: str | None = None
    query_type: QueryType
    query_definition: dict[str, object] = Field(default_factory=dict)
    is_shared: bool = False


class SavedQueryUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    query_definition: dict[str, object] | None = None
    is_shared: bool | None = None


class SavedQuerySummary(BaseModel):
    id: str
    org_id: str
    user_id: str
    name: str
    description: str | None = None
    query_type: QueryType
    is_shared: bool
    last_run_at: datetime | None = None
    run_count: int
    created_at: datetime
    updated_at: datetime


class SavedQueryDetail(SavedQuerySummary):
    query_definition: dict[str, object] = Field(default_factory=dict)


class SavedQueryListResponse(BaseModel):
    saved_queries: list[SavedQuerySummary]


class SavedQueryMutationResponse(BaseModel):
    saved_query: SavedQueryDetail
