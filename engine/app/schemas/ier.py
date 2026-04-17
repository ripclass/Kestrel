from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field

IERDirection = Literal["inbound", "outbound"]


class IEROutboundCreate(BaseModel):
    counterparty_fiu: str
    counterparty_country: str | None = None
    request_narrative: str
    deadline: date | None = None
    egmont_ref: str | None = None
    linked_entity_ids: list[str] = Field(default_factory=list)


class IERInboundCreate(BaseModel):
    counterparty_fiu: str
    counterparty_country: str | None = None
    request_narrative: str
    egmont_ref: str
    deadline: date | None = None
    linked_entity_ids: list[str] = Field(default_factory=list)


class IERRespondRequest(BaseModel):
    response_narrative: str
    linked_str_ids: list[str] = Field(default_factory=list)


class IERCloseRequest(BaseModel):
    note: str | None = None


class IERSummary(BaseModel):
    id: str
    report_ref: str
    status: str
    direction: IERDirection
    counterparty_fiu: str
    counterparty_country: str | None = None
    egmont_ref: str | None = None
    deadline: date | None = None
    has_response: bool
    org_name: str
    created_at: datetime
    updated_at: datetime | None = None


class IERDetail(IERSummary):
    request_narrative: str | None = None
    response_narrative: str | None = None
    narrative: str | None = None
    linked_entity_ids: list[str] = Field(default_factory=list)
    reported_at: datetime | None = None


class IERListResponse(BaseModel):
    iers: list[IERSummary]


class IERMutationResponse(BaseModel):
    ier: IERDetail
