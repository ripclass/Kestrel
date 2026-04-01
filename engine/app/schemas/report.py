from pydantic import BaseModel


class ComplianceScore(BaseModel):
    org_name: str
    submission_timeliness: int
    alert_conversion: int
    peer_coverage: int
    score: int


class ComplianceScorecard(BaseModel):
    banks: list[ComplianceScore]
