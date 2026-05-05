from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


_VALID_CHANNELS = {
    "NPSB",
    "BEFTN",
    "RTGS",
    "MFS_BKASH",
    "MFS_NAGAD",
    "MFS_ROCKET",
    "CASH",
    "CHEQUE",
    "CARD",
    "WIRE",
    "LC",
    "DRAFT",
}


class RealtimeScoreRequest(BaseModel):
    """Request body for `POST /transactions/score`."""

    transaction_id: str = Field(..., min_length=1, max_length=128, description="Bank's own transaction ID.")
    from_account: str = Field(..., min_length=1, max_length=128)
    to_account: str = Field(..., min_length=1, max_length=128)
    amount: float = Field(..., ge=0)
    currency: str = Field("BDT", min_length=3, max_length=8)
    channel: str = Field(..., description="One of NPSB, BEFTN, RTGS, MFS_*, CASH, CHEQUE, CARD, WIRE, LC, DRAFT.")
    transaction_type: Literal["credit", "debit"]
    from_account_metadata: dict[str, Any] | None = None
    to_account_metadata: dict[str, Any] | None = None
    timestamp: datetime | None = None


class RealtimeReason(BaseModel):
    rule: str
    score: int
    reason_text: str
    detail: dict[str, Any] | None = None


class RealtimeScoreResponse(BaseModel):
    """Response body for `POST /transactions/score`."""

    log_id: str
    score: int = Field(..., ge=0, le=100)
    decision: Literal["approve", "review", "hold", "reject"]
    confidence: float = Field(..., ge=0.0, le=1.0)
    reasons: list[RealtimeReason] = Field(default_factory=list)
    evidence: dict[str, Any] = Field(default_factory=dict)
    cross_bank_flag: bool
    request_id: str
    latency_ms: int = Field(..., ge=0)


class RealtimeFeedbackRequest(BaseModel):
    outcome: Literal["legitimate", "fraud", "unsure"]
    note: str | None = Field(default=None, max_length=1000)


class RealtimeFeedbackResponse(BaseModel):
    id: str
    feedback_received: bool
    feedback_outcome: str
    feedback_at: str


class RealtimeRecentRow(BaseModel):
    id: str
    transaction_external_id: str
    score: int
    decision: str
    cross_bank_flag: bool
    latency_ms: int
    feedback_received: bool
    feedback_outcome: str | None = None
    created_at: str | None = None


def channel_is_supported(channel: str) -> bool:
    return (channel or "").upper() in _VALID_CHANNELS
