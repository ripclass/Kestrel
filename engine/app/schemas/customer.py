from datetime import date
from typing import Any, Literal

from pydantic import BaseModel, Field


class BeneficialOwnerInput(BaseModel):
    full_name: str = Field(..., min_length=1, max_length=255)
    nid: str | None = None
    passport: str | None = None
    date_of_birth: date | None = None
    nationality: str | None = None
    ownership_pct: float | None = Field(default=None, ge=0.0, le=100.0)


class CustomerOnboardInput(BaseModel):
    customer_external_id: str = Field(..., min_length=1, max_length=128)
    customer_type: Literal["individual", "business"]
    full_name: str = Field(..., min_length=1, max_length=255)
    nid: str | None = None
    passport: str | None = None
    date_of_birth: date | None = None
    nationality: str | None = Field(default=None, max_length=64)
    phone: str | None = None
    email: str | None = None
    address: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)
    beneficial_owners: list[BeneficialOwnerInput] = Field(default_factory=list)


class CustomerPatchInput(BaseModel):
    phone: str | None = None
    email: str | None = None
    address: dict[str, Any] | None = None
    metadata: dict[str, Any] | None = None
    beneficial_owners: list[BeneficialOwnerInput] | None = None


class CustomerReviewInput(BaseModel):
    decision: Literal["approved", "declined", "review"]
    note: str | None = Field(default=None, max_length=1000)


class CustomerView(BaseModel):
    id: str
    org_id: str
    customer_external_id: str
    customer_type: str
    full_name: str
    nid: str | None = None
    passport: str | None = None
    date_of_birth: str | None = None
    nationality: str | None = None
    phone: str | None = None
    email: str | None = None
    address: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)
    beneficial_owners: list[dict[str, Any]] = Field(default_factory=list)
    risk_score: int | None = None
    risk_level: str | None = None
    kyc_status: str
    screening_results: dict[str, Any] = Field(default_factory=dict)
    onboarded_at: str | None = None
    reviewed_at: str | None = None
    reviewed_by: str | None = None
    last_rescreened_at: str | None = None
