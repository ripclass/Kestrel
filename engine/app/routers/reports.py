from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import AuthenticatedUser, get_current_user
from app.dependencies import get_current_session
from app.schemas.report import ComplianceScorecard, NationalReportResponse, ReportExportResponse, TrendSeriesResponse
from app.services.pdf_export import build_report_export
from app.services.reporting import build_compliance_scorecard, build_national_dashboard, build_trend_series

router = APIRouter()


@router.get("/national", response_model=NationalReportResponse)
async def national(
    user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_current_session)],
) -> NationalReportResponse:
    return await build_national_dashboard(session)


@router.get("/compliance", response_model=ComplianceScorecard)
async def compliance(
    user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_current_session)],
) -> ComplianceScorecard:
    return await build_compliance_scorecard(session)


@router.get("/trends", response_model=TrendSeriesResponse)
async def trends(
    user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_current_session)],
) -> TrendSeriesResponse:
    return await build_trend_series(session)


@router.post("/export", response_model=ReportExportResponse)
async def export_report(
    report_type: str = Query("national"),
    user: Annotated[AuthenticatedUser, Depends(get_current_user)] = None,
) -> ReportExportResponse:
    return ReportExportResponse.model_validate(build_report_export(report_type))
