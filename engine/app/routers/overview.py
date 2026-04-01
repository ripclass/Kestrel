from typing import Annotated

from fastapi import APIRouter, Depends

from app.auth import AuthenticatedUser, get_current_user
from app.schemas.overview import KpiStat, OverviewResponse

router = APIRouter()


@router.get("", response_model=OverviewResponse)
async def get_overview(user: Annotated[AuthenticatedUser, Depends(get_current_user)]) -> OverviewResponse:
    if user.persona == "bfiu_director":
        headline = "National threat posture across banks, channels, and typologies."
        stats = [
            KpiStat(label="High-severity networks", value="18", delta="+3 this week", detail="cross-bank clusters with regulator visibility"),
            KpiStat(label="Peer banks lagging", value="2", delta="attention required", detail="timeliness and conversion below national baseline"),
            KpiStat(label="Evaluation-ready packs", value="5", delta="up to date", detail="briefing packs assembled"),
        ]
    elif user.persona == "bank_camlco":
        headline = "Your bank posture with peer-network intelligence overlaid."
        stats = [
            KpiStat(label="Accounts above threshold", value="32", delta="+5 from last scan", detail="ready for manual review"),
            KpiStat(label="Peer-network signals", value="11", delta="3 urgent", detail="anonymized cross-bank indicators exposed"),
            KpiStat(label="Submission posture", value="84/100", delta="+4 month on month", detail="above peer median"),
        ]
    else:
        headline = "Unified triage for entity overlaps, alerts, and active investigations."
        stats = [
            KpiStat(label="Open priority alerts", value="18", delta="6 critical", detail="triage within today"),
            KpiStat(label="Cross-bank matches", value="7", delta="+2 overnight", detail="new overlaps ready for validation"),
            KpiStat(label="Cases in motion", value="4", delta="1 escalated", detail="shared evidence workspace active"),
        ]

    return OverviewResponse(headline=headline, operational=["RLS enforced at data layer", "Shared entities visible across orgs"], stats=stats)
