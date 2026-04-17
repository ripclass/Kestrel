from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field, model_validator

from app.schemas.ai import AIInvocationMeta, ExtractedEntity

ReportType = Literal[
    "str",
    "sar",
    "ctr",
    "tbml",
    "complaint",
    "ier",
    "internal",
    "adverse_media_str",
    "adverse_media_sar",
    "escalated",
    "additional_info",
]

IERDirection = Literal["inbound", "outbound"]


class STRLifecycleEvent(BaseModel):
    action: str
    actor_user_id: str
    actor_role: str
    actor_org_type: str
    from_status: str | None = None
    to_status: str | None = None
    note: str | None = None
    occurred_at: datetime


class STRReviewState(BaseModel):
    assigned_to: str | None = None
    notes: list[dict[str, str]] = Field(default_factory=list)
    status_history: list[STRLifecycleEvent] = Field(default_factory=list)


class STREnrichmentSnapshot(BaseModel):
    draft_narrative: str
    missing_fields: list[str] = Field(default_factory=list)
    category_suggestion: str
    severity_suggestion: str
    trigger_facts: list[str] = Field(default_factory=list)
    extracted_entities: list[ExtractedEntity] = Field(default_factory=list)
    generated_at: datetime
    narrative_meta: AIInvocationMeta
    extraction_meta: AIInvocationMeta


class STRReportSummary(BaseModel):
    id: str
    org_id: str
    org_name: str
    report_ref: str
    report_type: ReportType = "str"
    status: str
    subject_name: str | None = None
    subject_account: str | None = None
    subject_bank: str | None = None
    total_amount: float
    currency: str
    transaction_count: int
    primary_channel: str | None = None
    category: str
    auto_risk_score: int | None = None
    cross_bank_hit: bool
    reported_at: datetime | None = None
    created_at: datetime
    updated_at: datetime | None = None
    supplements_report_id: str | None = None
    ier_direction: IERDirection | None = None
    ier_counterparty_fiu: str | None = None
    media_source: str | None = None


class STRReportDetail(STRReportSummary):
    subject_phone: str | None = None
    subject_wallet: str | None = None
    subject_nid: str | None = None
    channels: list[str] = Field(default_factory=list)
    date_range_start: date | None = None
    date_range_end: date | None = None
    narrative: str | None = None
    matched_entity_ids: list[str] = Field(default_factory=list)
    submitted_by: str | None = None
    reviewed_by: str | None = None
    metadata: dict[str, object] = Field(default_factory=dict)
    enrichment: STREnrichmentSnapshot | None = None
    review: STRReviewState = Field(default_factory=STRReviewState)

    media_url: str | None = None
    media_published_at: date | None = None

    ier_counterparty_country: str | None = None
    ier_egmont_ref: str | None = None
    ier_request_narrative: str | None = None
    ier_response_narrative: str | None = None
    ier_deadline: date | None = None

    tbml_invoice_value: float | None = None
    tbml_declared_value: float | None = None
    tbml_lc_reference: str | None = None
    tbml_hs_code: str | None = None
    tbml_commodity: str | None = None
    tbml_counterparty_country: str | None = None


class STRDraftUpsert(BaseModel):
    report_type: ReportType = "str"
    subject_name: str | None = None
    subject_account: str | None = None
    subject_bank: str | None = None
    subject_phone: str | None = None
    subject_wallet: str | None = None
    subject_nid: str | None = None
    total_amount: float = 0
    currency: str = "BDT"
    transaction_count: int = 0
    primary_channel: str | None = None
    category: str = "fraud"
    channels: list[str] = Field(default_factory=list)
    date_range_start: date | None = None
    date_range_end: date | None = None
    narrative: str | None = None
    metadata: dict[str, object] = Field(default_factory=dict)

    supplements_report_id: str | None = None

    media_source: str | None = None
    media_url: str | None = None
    media_published_at: date | None = None

    ier_direction: IERDirection | None = None
    ier_counterparty_fiu: str | None = None
    ier_counterparty_country: str | None = None
    ier_egmont_ref: str | None = None
    ier_request_narrative: str | None = None
    ier_response_narrative: str | None = None
    ier_deadline: date | None = None

    tbml_invoice_value: float | None = None
    tbml_declared_value: float | None = None
    tbml_lc_reference: str | None = None
    tbml_hs_code: str | None = None
    tbml_commodity: str | None = None
    tbml_counterparty_country: str | None = None

    @model_validator(mode="after")
    def _enforce_type_requirements(self) -> "STRDraftUpsert":
        rt = self.report_type
        if rt == "ier":
            if not self.ier_direction or not self.ier_counterparty_fiu:
                raise ValueError(
                    "IER reports require ier_direction and ier_counterparty_fiu."
                )
        elif rt == "additional_info":
            if not self.supplements_report_id:
                raise ValueError(
                    "Additional Information Files require supplements_report_id."
                )
        elif rt == "tbml":
            if not self.tbml_counterparty_country:
                raise ValueError(
                    "TBML reports require tbml_counterparty_country."
                )
        elif rt in ("adverse_media_str", "adverse_media_sar"):
            if not self.media_source:
                raise ValueError(
                    "Adverse media reports require media_source."
                )
        return self


class STRReviewRequest(BaseModel):
    action: Literal["start_review", "assign", "flag", "confirm", "dismiss"]
    note: str | None = None
    assigned_to: str | None = None


class STRListResponse(BaseModel):
    reports: list[STRReportSummary]


class STRMutationResponse(BaseModel):
    report: STRReportDetail


class STREnrichmentResponse(BaseModel):
    report: STRReportDetail
    enrichment: STREnrichmentSnapshot
