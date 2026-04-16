"""Cash Transaction Report (CTR) service — bulk import and listing."""

from __future__ import annotations

import uuid
from datetime import date
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import AuthenticatedUser
from app.models.ctr import CashTransactionReport
from app.models.organization import Organization
from app.schemas.ctr import CTRBulkImportResponse, CTRListResponse, CTRSummary


def _iso(value: Any) -> str | None:
    if value is None:
        return None
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return str(value)


async def list_ctrs(
    session: AsyncSession,
    *,
    user: AuthenticatedUser,
    limit: int = 100,
    offset: int = 0,
) -> CTRListResponse:
    base = select(CashTransactionReport)
    if user.org_type != "regulator":
        base = base.where(CashTransactionReport.org_id == uuid.UUID(user.org_id))

    count_result = await session.execute(select(func.count()).select_from(base.subquery()))
    total = count_result.scalar() or 0

    stmt = (
        base.order_by(CashTransactionReport.transaction_date.desc(), CashTransactionReport.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    result = await session.execute(stmt)
    records = [
        CTRSummary(
            id=str(row.id),
            org_id=str(row.org_id),
            account_number=row.account_number,
            account_name=row.account_name,
            transaction_date=row.transaction_date.isoformat(),
            amount=float(row.amount),
            currency=row.currency,
            transaction_type=row.transaction_type,
            branch_code=row.branch_code,
            reported_at=row.reported_at,
            created_at=row.created_at,
        )
        for row in result.scalars().all()
    ]
    return CTRListResponse(records=records, total=total)


async def bulk_import_ctrs(
    session: AsyncSession,
    *,
    user: AuthenticatedUser,
    records: list[dict[str, Any]],
    ip: str | None,
) -> CTRBulkImportResponse:
    if not records:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No records to import.")

    org_id = uuid.UUID(user.org_id)
    rows = []
    for item in records:
        rows.append(
            CashTransactionReport(
                org_id=org_id,
                account_number=item["account_number"],
                account_name=item.get("account_name"),
                transaction_date=date.fromisoformat(item["transaction_date"]),
                amount=item["amount"],
                currency=item.get("currency", "BDT"),
                transaction_type=item.get("transaction_type"),
                branch_code=item.get("branch_code"),
            )
        )
    session.add_all(rows)
    await session.commit()
    return CTRBulkImportResponse(imported=len(rows), message=f"Imported {len(rows)} CTR records.")
