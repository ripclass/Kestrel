from typing import Literal

from pydantic import BaseModel, Field


class XMLImportResponse(BaseModel):
    report_id: str
    report_ref: str
    report_type: str
    detection_run_id: str | None = None
    transactions_ingested: int
    subjects_resolved: int
    warnings: list[str] = Field(default_factory=list)
    status: Literal["ok", "partial"] = "ok"
