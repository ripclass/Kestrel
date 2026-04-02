from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import AuthenticatedUser, get_current_user, require_roles
from app.dependencies import get_current_session
from app.schemas.str_report import (
    STREnrichmentResponse,
    STRListResponse,
    STRMutationResponse,
    STRReportDetail,
    STRReviewRequest,
    STRDraftUpsert,
)
from app.services.str_reports import (
    create_str_report,
    enrich_str_report,
    get_str_report,
    list_str_reports,
    review_str_report,
    submit_str_report,
    update_str_report,
)

router = APIRouter()


@router.get("", response_model=STRListResponse)
async def list_reports(
    user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_current_session)],
    status_filter: Annotated[str | None, Query(alias="status")] = None,
) -> STRListResponse:
    reports = await list_str_reports(session, status_filter=status_filter)
    return STRListResponse(reports=reports)


@router.post("", response_model=STRMutationResponse)
async def create_report(
    body: STRDraftUpsert,
    request: Request,
    user: Annotated[AuthenticatedUser, Depends(require_roles("analyst", "manager", "admin", "superadmin"))],
    session: Annotated[AsyncSession, Depends(get_current_session)],
) -> STRMutationResponse:
    return await create_str_report(
        session,
        user=user,
        payload=body.model_dump(),
        ip=request.client.host if request.client else None,
    )


@router.get("/{report_id}", response_model=STRReportDetail)
async def report_detail(
    report_id: str,
    user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_current_session)],
) -> STRReportDetail:
    return await get_str_report(session, report_id)


@router.patch("/{report_id}", response_model=STRMutationResponse)
async def update_report(
    report_id: str,
    body: STRDraftUpsert,
    request: Request,
    user: Annotated[AuthenticatedUser, Depends(require_roles("analyst", "manager", "admin", "superadmin"))],
    session: Annotated[AsyncSession, Depends(get_current_session)],
) -> STRMutationResponse:
    return await update_str_report(
        session,
        report_id=report_id,
        user=user,
        payload=body.model_dump(),
        ip=request.client.host if request.client else None,
    )


@router.post("/{report_id}/submit", response_model=STRMutationResponse)
async def submit_report(
    report_id: str,
    request: Request,
    user: Annotated[AuthenticatedUser, Depends(require_roles("analyst", "manager", "admin", "superadmin"))],
    session: Annotated[AsyncSession, Depends(get_current_session)],
) -> STRMutationResponse:
    return await submit_str_report(
        session,
        report_id=report_id,
        user=user,
        ip=request.client.host if request.client else None,
    )


@router.post("/{report_id}/review", response_model=STRMutationResponse)
async def review_report(
    report_id: str,
    body: STRReviewRequest,
    request: Request,
    user: Annotated[AuthenticatedUser, Depends(require_roles("analyst", "manager", "admin", "superadmin"))],
    session: Annotated[AsyncSession, Depends(get_current_session)],
) -> STRMutationResponse:
    return await review_str_report(
        session,
        report_id=report_id,
        user=user,
        request=body,
        ip=request.client.host if request.client else None,
    )


@router.post("/{report_id}/enrich", response_model=STREnrichmentResponse)
async def enrich_report(
    report_id: str,
    request: Request,
    user: Annotated[AuthenticatedUser, Depends(require_roles("analyst", "manager", "admin", "superadmin"))],
    session: Annotated[AsyncSession, Depends(get_current_session)],
) -> STREnrichmentResponse:
    enrichment = await enrich_str_report(
        session,
        report_id=report_id,
        user=user,
        ip=request.client.host if request.client else None,
    )
    report = await get_str_report(session, report_id)
    return STREnrichmentResponse(report=report, enrichment=enrichment)
