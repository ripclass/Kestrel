from pydantic import BaseModel


class CrossBankMatch(BaseModel):
    id: str
    entity_id: str
    match_key: str
    match_type: str
    involved_orgs: list[str]
    involved_str_ids: list[str]
    match_count: int
    total_exposure: float
    risk_score: int
    severity: str
    status: str


class TypologySummary(BaseModel):
    id: str
    title: str
    category: str
    channels: list[str]
    indicators: list[str]
    narrative: str
