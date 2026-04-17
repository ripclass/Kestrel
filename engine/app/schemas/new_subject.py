from typing import Literal

from pydantic import BaseModel, Field

SubjectEntityType = Literal[
    "account",
    "phone",
    "wallet",
    "nid",
    "person",
    "business",
    "device",
    "ip",
    "url",
]


class NewSubjectIdentifier(BaseModel):
    entity_type: SubjectEntityType
    value: str
    display_name: str | None = None


class NewSubjectRequest(BaseModel):
    primary_kind: Literal["account", "person", "business"] = "account"
    identifiers: list[NewSubjectIdentifier] = Field(default_factory=list)
    metadata: dict[str, object] = Field(default_factory=dict)


class NewSubjectResolvedEntity(BaseModel):
    id: str
    entity_type: str
    display_value: str
    display_name: str | None = None
    created: bool


class NewSubjectResponse(BaseModel):
    primary_entity_id: str
    resolved: list[NewSubjectResolvedEntity]
    connections_created: int
