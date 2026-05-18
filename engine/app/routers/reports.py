from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import AuthenticatedUser, get_current_user
from app.dependencies import get_current_session
from app.schemas.report import ComplianceScorecard, NationalReportResponse, ReportExportResponse, TrendSeriesResponse
from app.services.pdf_export import render_report_pack_pdf
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


@router.post("/export")
async def export_report(
    user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_current_session)],
    report_type: str = Query("national"),
) -> Response:
    pdf_bytes = await render_report_pack_pdf(
        session, report_type=report_type, user=user
    )
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M")
    filename = f"kestrel-{report_type}-pack-{timestamp}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Cache-Control": "no-store",
        },
    )
