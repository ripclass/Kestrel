from typing import Literal

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: Literal["ok"]
    version: str
    environment: str


class ServiceCheck(BaseModel):
    name: str
    status: str
    required: bool
    detail: str
    metadata: dict[str, object] = Field(default_factory=dict)


class ReadinessResponse(BaseModel):
    status: Literal["ready", "not_ready"]
    version: str
    environment: str
    checks: list[ServiceCheck]
