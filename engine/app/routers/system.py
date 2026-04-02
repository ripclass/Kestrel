from fastapi import APIRouter, Response

from app.config import get_settings
from app.schemas.system import HealthResponse, ReadinessResponse
from app.services.readiness import build_readiness_report

router = APIRouter()
settings = get_settings()


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse(
        status="ok",
        version=settings.app_version,
        environment=settings.environment,
    )


@router.get("/ready", response_model=ReadinessResponse)
async def readiness(response: Response) -> ReadinessResponse:
    report = await build_readiness_report(settings)
    response.status_code = 200 if report.status == "ready" else 503
    return report
