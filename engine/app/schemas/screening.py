from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


_VALID_LIST_SOURCES = {"OFAC", "EU", "UN", "UK_OFSI", "BB_DOMESTIC", "PEP", "ADVERSE_MEDIA"}
_VALID_ENTRY_TYPES = {"individual", "entity", "vessel", "aircraft"}


class ScreeningEntityRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    date_of_birth: date | None = None
    nationality: str | None = Field(default=None, max_length=64)
    nid: str | None = Field(default=None, max_length=64)
    passport: str | None = Field(default=None, max_length=64)
    screening_lists: list[str] = Field(default_factory=list)
    minimum_match_score: float = Field(default=0.7, ge=0.0, le=1.0)


class ScreeningMatchModel(BaseModel):
    list_source: str
    list_version: str
    entry_id: str
    entry_type: str
    matched_name: str
    matched_aliases: list[str] = Field(default_factory=list)
    matched_entry: dict[str, Any] = Field(default_factory=dict)
    match_score: float
    match_reasons: list[str] = Field(default_factory=list)


class ScreeningEntityResponse(BaseModel):
    matches: list[ScreeningMatchModel] = Field(default_factory=list)
    screened_at: str
    request_id: str


class AdverseMediaRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    nationality: str | None = Field(default=None, max_length=64)
    fuzziness: float = Field(default=0.5, ge=0.0, le=1.0)


class AdverseMediaHitModel(BaseModel):
    name: str
    snippet: str
    url: str | None = None
    published_at: str | None = None
    score: float


class AdverseMediaResponse(BaseModel):
    provider: Literal["stub", "complyadvantage"]
    hits: list[AdverseMediaHitModel] = Field(default_factory=list)
    screened_at: str
    request_id: str


class WatchlistEntryView(BaseModel):
    id: str
    list_source: str
    list_version: str
    entry_type: str
    primary_name: str
    aliases: list[str] = Field(default_factory=list)
    date_of_birth: date | None = None
    nationality: str | None = None
    identifiers: dict[str, Any] = Field(default_factory=dict)
    addresses: list[Any] = Field(default_factory=list)
    reason: str | None = None
    ingested_at: str | None = None
    removed_at: str | None = None


class WatchlistEntryUpload(BaseModel):
    list_source: str = Field(..., max_length=32)
    list_version: str = Field(..., max_length=64)
    entry_type: str = Field(..., max_length=32)
    primary_name: str = Field(..., min_length=1, max_length=255)
    aliases: list[str] = Field(default_factory=list)
    date_of_birth: date | None = None
    nationality: str | None = Field(default=None, max_length=64)
    identifiers: dict[str, Any] = Field(default_factory=dict)
    addresses: list[Any] = Field(default_factory=list)
    reason: str | None = Field(default=None, max_length=2000)


def list_source_is_supported(value: str) -> bool:
    return (value or "").upper() in _VALID_LIST_SOURCES


def entry_type_is_supported(value: str) -> bool:
    return (value or "").lower() in _VALID_ENTRY_TYPES


def isoformat(value: datetime | None) -> str | None:
    return value.astimezone().isoformat() if value else None
