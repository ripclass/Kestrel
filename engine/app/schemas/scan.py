from pydantic import BaseModel, Field


class DetectionRunSummary(BaseModel):
    id: str
    file_name: str
    status: str
    alerts_generated: int
    accounts_scanned: int
    tx_count: int
    created_at: str
    started_at: str | None = None
    completed_at: str | None = None


class FlaggedAccount(BaseModel):
    entity_id: str
    account_number: str
    account_name: str
    score: int
    severity: str
    summary: str
    matched_banks: int
    total_exposure: float
    tags: list[str] = Field(default_factory=list)
    linked_alert_id: str | None = None
    linked_case_id: str | None = None


class DetectionRunDetail(DetectionRunSummary):
    run_type: str
    summary: str
    flagged_accounts: list[FlaggedAccount] = Field(default_factory=list)
    error: str | None = None


class ScanQueueRequest(BaseModel):
    file_name: str | None = None
    selected_rules: list[str] = Field(default_factory=list)


class ScanQueueResponse(BaseModel):
    run: DetectionRunDetail
    message: str
