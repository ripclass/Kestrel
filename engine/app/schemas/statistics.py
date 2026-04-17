from pydantic import BaseModel, Field


class ReportsByTypeByMonth(BaseModel):
    month: str
    report_type: str
    count: int


class ReportsByOrg(BaseModel):
    org_name: str
    count: int


class CtrVolumeByMonth(BaseModel):
    month: str
    count: int
    total_amount: float


class DisseminationsByAgency(BaseModel):
    recipient_agency: str
    recipient_type: str
    count: int


class CaseOutcomeBreakdown(BaseModel):
    status: str
    count: int


class TimeToReviewAverage(BaseModel):
    report_type: str
    average_hours: float
    sample_size: int


class OperationalStatisticsResponse(BaseModel):
    reports_by_type_by_month: list[ReportsByTypeByMonth] = Field(default_factory=list)
    reports_by_org: list[ReportsByOrg] = Field(default_factory=list)
    ctr_volume_by_month: list[CtrVolumeByMonth] = Field(default_factory=list)
    disseminations_by_agency: list[DisseminationsByAgency] = Field(default_factory=list)
    case_outcomes: list[CaseOutcomeBreakdown] = Field(default_factory=list)
    time_to_review: list[TimeToReviewAverage] = Field(default_factory=list)
    generated_at: str
