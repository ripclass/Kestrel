"""Parse an uploaded CSV into Account + Transaction rows tagged with run_id."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timezone
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.account import Account
from app.models.org import Organization
from app.models.transaction import Transaction
from app.parsers.csv import parse_csv
from app.parsers.xlsx import parse_xlsx

REQUIRED_COLUMNS = ("posted_at", "src_account", "amount")

# File-format magic bytes. .xlsx is a ZIP container; legacy .xls is OLE2.
_XLSX_MAGIC = b"PK\x03\x04"
_XLS_MAGIC = b"\xd0\xcf\x11\xe0"


def _looks_like_xlsx(content_bytes: bytes, file_name: str | None) -> bool:
    return content_bytes[:4] == _XLSX_MAGIC or (file_name or "").lower().endswith(".xlsx")


def _looks_like_legacy_xls(content_bytes: bytes, file_name: str | None) -> bool:
    return content_bytes[:4] == _XLS_MAGIC or (file_name or "").lower().endswith(".xls")


def _parse_timestamp(value: str) -> datetime:
    """Accept ISO 8601 with or without timezone; default to UTC."""
    value = (value or "").strip()
    if not value:
        raise ValueError("posted_at is required")
    # Python's fromisoformat accepts '2026-04-01T10:30:00+00:00' and
    # '2026-04-01T10:30:00' (naive) — normalize to UTC.
    try:
        dt = datetime.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(f"Invalid posted_at: {value}") from exc
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    else:
        dt = dt.astimezone(UTC)
    return dt


def _parse_amount(value: str) -> float:
    if value is None or str(value).strip() == "":
        raise ValueError("amount is required")
    try:
        return float(str(value).replace(",", "").strip())
    except ValueError as exc:
        raise ValueError(f"Invalid amount: {value}") from exc


async def _resolve_account(
    session: AsyncSession,
    *,
    org_id: uuid.UUID,
    account_number: str,
    accounts_cache: dict[str, Account],
    bank_code: str | None = None,
) -> Account:
    number = (account_number or "").strip()
    if not number:
        raise ValueError("Account number cannot be empty")

    if number in accounts_cache:
        # If we previously cached this account with an unknown bank_code and
        # now we have one from the CSV, fill it in.
        cached = accounts_cache[number]
        if bank_code and not getattr(cached, "bank_code", None):
            cached.bank_code = bank_code
        return cached

    result = await session.execute(
        select(Account)
        .where(Account.org_id == org_id, Account.account_number == number)
        .limit(1)
    )
    account = result.scalars().first()
    if account is None:
        account = Account(
            org_id=org_id,
            account_number=number,
            account_name=None,
            bank_code=bank_code,
            risk_tier="normal",
            metadata_json={"source": "csv_upload"},
        )
        session.add(account)
        await session.flush()  # populate account.id
    elif bank_code and not account.bank_code:
        # Back-fill bank_code on pre-existing account rows
        account.bank_code = bank_code

    accounts_cache[number] = account
    return account


async def _load_org_bank_code(session: AsyncSession, org_id: uuid.UUID) -> str | None:
    result = await session.execute(
        select(Organization.bank_code).where(Organization.id == org_id).limit(1)
    )
    return result.scalar_one_or_none()


async def ingest_csv(
    session: AsyncSession,
    *,
    run_id: uuid.UUID,
    org_id: uuid.UUID,
    content: str,
) -> dict[str, int]:
    """Parse decoded CSV text and insert Account + Transaction rows.

    Retained for callers that already hold decoded text. The upload path uses
    ``ingest_upload`` (bytes + filename) so it can dispatch CSV vs XLSX.
    """
    try:
        rows = parse_csv(content)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"CSV parse error: {exc}",
        ) from exc
    return await _ingest_rows(
        session, run_id=run_id, org_id=org_id, rows=rows, source_label="csv_upload"
    )


async def ingest_upload(
    session: AsyncSession,
    *,
    run_id: uuid.UUID,
    org_id: uuid.UUID,
    content_bytes: bytes,
    file_name: str | None,
) -> dict[str, int]:
    """Ingest an uploaded statement file, dispatching by format.

    Handles .xlsx (openpyxl) and CSV/text. Legacy .xls is rejected with a
    clear message rather than being mis-decoded as garbage text and surfacing
    a confusing 'missing required columns' error.
    """
    if _looks_like_legacy_xls(content_bytes, file_name):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Legacy .xls workbooks aren't supported. Re-save as .xlsx or export to CSV.",
        )

    if _looks_like_xlsx(content_bytes, file_name):
        try:
            rows = parse_xlsx(content_bytes)
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Could not read the Excel file: {exc}",
            ) from exc
        source_label = "xlsx_upload"
    else:
        try:
            content_str = content_bytes.decode("utf-8-sig")
        except UnicodeDecodeError:
            content_str = content_bytes.decode("latin-1")
        try:
            rows = parse_csv(content_str)
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"CSV parse error: {exc}",
            ) from exc
        source_label = "csv_upload"

    return await _ingest_rows(
        session, run_id=run_id, org_id=org_id, rows=rows, source_label=source_label
    )


async def _ingest_rows(
    session: AsyncSession,
    *,
    run_id: uuid.UUID,
    org_id: uuid.UUID,
    rows: list[dict[str, str]],
    source_label: str,
) -> dict[str, int]:
    """Validate parsed rows and insert Account + Transaction records.

    Returns {'tx_count': N, 'accounts_touched': M}. Raises HTTPException(400)
    on an empty file or missing required columns.
    """
    if not rows:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The uploaded file is empty.",
        )

    missing = [col for col in REQUIRED_COLUMNS if col not in rows[0]]
    if missing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File is missing required columns: {', '.join(missing)}. "
                   f"Expected at least: {', '.join(REQUIRED_COLUMNS)}.",
        )

    accounts_cache: dict[str, Account] = {}
    tx_count = 0
    org_bank_code = await _load_org_bank_code(session, org_id)

    for idx, row in enumerate(rows, start=1):
        try:
            posted_at = _parse_timestamp(row.get("posted_at", ""))
            amount = _parse_amount(row.get("amount", ""))
            # Source accounts always belong to the uploading bank
            src = await _resolve_account(
                session,
                org_id=org_id,
                account_number=row.get("src_account", ""),
                accounts_cache=accounts_cache,
                bank_code=org_bank_code,
            )
            dst_number = (row.get("dst_account") or "").strip()
            dst = None
            if dst_number:
                # Optional dst_bank_code column flags cross-bank transfers.
                # Defaults to uploader's bank when absent.
                dst_bank = (row.get("dst_bank_code") or "").strip() or org_bank_code
                dst = await _resolve_account(
                    session,
                    org_id=org_id,
                    account_number=dst_number,
                    accounts_cache=accounts_cache,
                    bank_code=dst_bank,
                )
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Row {idx}: {exc}",
            ) from exc

        tx = Transaction(
            org_id=org_id,
            run_id=run_id,
            posted_at=posted_at,
            src_account_id=src.id,
            dst_account_id=dst.id if dst else None,
            amount=amount,
            currency=(row.get("currency") or "BDT").strip() or "BDT",
            channel=(row.get("channel") or "").strip() or None,
            tx_type=(row.get("tx_type") or "").strip() or None,
            description=(row.get("description") or "").strip() or None,
            metadata_json={"source": source_label, "row": idx},
        )
        session.add(tx)
        tx_count += 1

    await session.flush()
    return {"tx_count": tx_count, "accounts_touched": len(accounts_cache)}
