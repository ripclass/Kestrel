from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.report import ComplianceScorecard
from app.services.reporting import build_compliance_scorecard


async def get_scorecard(session: AsyncSession) -> ComplianceScorecard:
    return await build_compliance_scorecard(session)
