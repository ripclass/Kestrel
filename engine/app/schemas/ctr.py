from datetime import datetime

from pydantic import BaseModel, Field


class CTRImportItem(BaseModel):
    account_number: str
    account_name: str | None = None
    transaction_date: str  # ISO date (YYYY-MM-DD)
    amount: float
    currency: str = "BDT"
    transaction_type: str | None = None  # deposit | withdrawal | transfer
    branch_code: str | None = None


class CTRBulkImportRequest(BaseModel):
    records: list[CTRImportItem] = Field(min_length=1)


class CTRSummary(BaseModel):
    id: str
    org_id: str
    account_number: str
    account_name: str | None = None
    transaction_date: str
    amount: float
    currency: str
    transaction_type: str | None = None
    branch_code: str | None = None
    reported_at: datetime | None = None
    created_at: datetime


class CTRListResponse(BaseModel):
    records: list[CTRSummary]
    total: int


class CTRBulkImportResponse(BaseModel):
    imported: int
    message: str
