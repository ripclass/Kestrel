"""Assemble a full case pack (case + alerts + reports) for PDF rendering."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import AuthenticatedUser
from app.models.alert import Alert
from app.models.str_report import STRReport
from app.services.case_mgmt import get_case_workspace


async def assemble_case_pack(
    session: AsyncSession,
    *,
    case_id: str,
    user: AuthenticatedUser,
) -> dict[str, Any]:
    """Return a dict with everything the case_pack template needs."""
    workspace = await get_case_workspace(session, user=user, case_id=case_id)

    # Linked alerts — the case carries a linked_alert_ids array; also include
    # alerts whose case_id == this case.
    alert_ids = {uuid.UUID(str(a)) for a in workspace.get("linked_alert_ids", []) if a}
    alerts: list[dict[str, Any]] = []
    if alert_ids or workspace.get("id"):
        conditions = []
        if alert_ids:
            conditions.append(Alert.id.in_(alert_ids))
        case_uuid = uuid.UUID(workspace["id"])
        conditions.append(Alert.case_id == case_uuid)
        stmt = select(Alert).where(or_(*conditions)).order_by(Alert.created_at.desc())
        result = await session.execute(stmt)
        seen_ids: set[str] = set()
        for alert in result.scalars().all():
            key = str(alert.id)
            if key in seen_ids:
                continue
            seen_ids.add(key)
            alerts.append(
                {
                    "id": key,
                    "title": alert.title,
                    "description": alert.description,
                    "alert_type": alert.alert_type,
                    "risk_score": alert.risk_score,
                    "severity": alert.severity,
                    "status": alert.status,
                }
            )

    # Linked STR/SAR/CTR reports — anything whose matched_entity_ids overlaps
    # this case's linked entity set, OR whose metadata records this case id.
    entity_uuids = [uuid.UUID(str(e)) for e in workspace.get("linked_entity_ids", []) if e]
    str_reports: list[dict[str, Any]] = []
    if entity_uuids:
        stmt = (
            select(STRReport)
            .where(STRReport.matched_entity_ids.overlap(entity_uuids))
            .order_by(STRReport.created_at.desc())
        )
        result = await session.execute(stmt)
        for report in result.scalars().all():
            str_reports.append(
                {
                    "id": str(report.id),
                    "report_ref": report.report_ref,
                    "report_type": report.report_type or "str",
                    "status": report.status,
                    "subject_name": report.subject_name,
                    "subject_account": report.subject_account,
                    "category": report.category,
                    "total_amount": float(report.total_amount or 0),
                }
            )

    return {
        "case": workspace,
        "evidence_entities": workspace.get("evidence_entities", []),
        "timeline": workspace.get("timeline", []),
        "alerts": alerts,
        "str_reports": str_reports,
    }
