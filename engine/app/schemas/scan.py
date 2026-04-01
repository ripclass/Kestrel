from pydantic import BaseModel


class DetectionRunSummary(BaseModel):
    id: str
    file_name: str
    status: str
    alerts_generated: int
    accounts_scanned: int
    tx_count: int
    created_at: str


class FlaggedAccount(BaseModel):
    label: str
    score: int


class ScanQueueResponse(BaseModel):
    run_id: str
    status: str
    message: str
