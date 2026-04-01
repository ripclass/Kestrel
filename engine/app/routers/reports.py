from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.auth import AuthenticatedUser, get_current_user
from app.schemas.overview import OverviewResponse
from app.schemas.report import ComplianceScorecard
from app.services.compliance import get_scorecard
from app.services.pdf_export import build_report_export
from seed.fixtures import TYPOLOGIES

router = APIRouter()


@router.get("/national", response_model=OverviewResponse)
async def national(user: Annotated[AuthenticatedUser, Depends(get_current_user)]) -> OverviewResponse:
    return OverviewResponse(
        headline="National threat posture across banks, channels, and typologies.",
        operational=[typology.title for typology in TYPOLOGIES],
        stats=[],
    )


@router.get("/compliance", response_model=ComplianceScorecard)
async def compliance(user: Annotated[AuthenticatedUser, Depends(get_current_user)]) -> ComplianceScorecard:
    return ComplianceScorecard(banks=get_scorecard())


@router.get("/trends")
async def trends(user: Annotated[AuthenticatedUser, Depends(get_current_user)]) -> dict[str, list[dict[str, int | str]]]:
    return {
        "series": [
            {"month": "Jan", "alerts": 74},
            {"month": "Feb", "alerts": 92},
            {"month": "Mar", "alerts": 108},
            {"month": "Apr", "alerts": 126},
        ]
    }


@router.post("/export")
async def export_report(
    report_type: str = Query(default="national"),
    user: Annotated[AuthenticatedUser, Depends(get_current_user)] = None,
) -> dict[str, str]:
    return build_report_export(report_type)
