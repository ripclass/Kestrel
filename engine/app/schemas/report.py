from pydantic import BaseModel, Field

from app.schemas.overview import KpiStat


class ComplianceScore(BaseModel):
    org_name: str
    submission_timeliness: int
    alert_conversion: int
    peer_coverage: int
    score: int


class ComplianceScorecard(BaseModel):
    banks: list[ComplianceScore] = Field(default_factory=list)


class ThreatMapRow(BaseModel):
    channel: str
    level: str
    detail: str
    signal_count: int
    total_exposure: float


class NationalReportResponse(BaseModel):
    headline: str
    operational: list[str] = Field(default_factory=list)
    stats: list[KpiStat] = Field(default_factory=list)
    threat_map: list[ThreatMapRow] = Field(default_factory=list)


class TrendPoint(BaseModel):
    month: str
    alerts: int
    str_reports: int
    cases: int
    scans: int


class TrendSeriesResponse(BaseModel):
    series: list[TrendPoint] = Field(default_factory=list)


class ReportExportResponse(BaseModel):
    report_type: str
    status: str
    message: str
    generated_at: str
