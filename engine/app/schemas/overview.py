from pydantic import BaseModel


class KpiStat(BaseModel):
    label: str
    value: str
    delta: str
    detail: str


class OverviewResponse(BaseModel):
    headline: str
    operational: list[str]
    stats: list[KpiStat]
