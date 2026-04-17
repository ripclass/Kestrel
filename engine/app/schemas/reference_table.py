from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

TableName = Literal[
    "banks",
    "branches",
    "countries",
    "channels",
    "categories",
    "currencies",
    "agencies",
]


class ReferenceEntryCreate(BaseModel):
    table_name: TableName
    code: str
    value: str
    description: str | None = None
    parent_code: str | None = None
    metadata: dict[str, object] = Field(default_factory=dict)
    is_active: bool = True


class ReferenceEntryUpdate(BaseModel):
    value: str | None = None
    description: str | None = None
    parent_code: str | None = None
    metadata: dict[str, object] | None = None
    is_active: bool | None = None


class ReferenceEntrySummary(BaseModel):
    id: str
    table_name: TableName
    code: str
    value: str
    description: str | None = None
    parent_code: str | None = None
    metadata: dict[str, object] = Field(default_factory=dict)
    is_active: bool
    created_at: datetime
    updated_at: datetime


class ReferenceTableCount(BaseModel):
    table_name: TableName
    active_count: int
    total_count: int


class ReferenceTableListResponse(BaseModel):
    entries: list[ReferenceEntrySummary]


class ReferenceTableCountsResponse(BaseModel):
    tables: list[ReferenceTableCount]


class ReferenceEntryMutationResponse(BaseModel):
    entry: ReferenceEntrySummary
