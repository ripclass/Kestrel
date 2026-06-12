"""Coverage for statement-upload parsing: XLSX parser + CSV/XLSX dispatch.

Before this, the scan upload decoded every file as text and fed it to the CSV
parser, so an uploaded .xlsx (a binary ZIP) became garbage and surfaced a
confusing 'missing required columns' 400. parse_xlsx was a dead stub. These
tests pin real XLSX parsing and the format dispatch/rejection helpers.
"""
from __future__ import annotations

from datetime import datetime
from io import BytesIO

from openpyxl import Workbook

from app.parsers.xlsx import parse_xlsx
from app.services.csv_ingest import _looks_like_legacy_xls, _looks_like_xlsx


def _xlsx_bytes(rows: list[list[object]]) -> bytes:
    wb = Workbook()
    ws = wb.active
    for row in rows:
        ws.append(row)
    buf = BytesIO()
    wb.save(buf)
    return buf.getvalue()


def test_parse_xlsx_header_and_rows() -> None:
    content = _xlsx_bytes([
        ["posted_at", "src_account", "amount", "channel"],
        ["2026-04-01T10:30:00", "ACC-1", "1500.50", "NPSB"],
        ["2026-04-02T09:00:00", "ACC-2", "9000", "CASH"],
    ])
    rows = parse_xlsx(content)
    assert len(rows) == 2
    # String cells pass through verbatim (only true float cells get the .0 trim).
    assert rows[0] == {
        "posted_at": "2026-04-01T10:30:00",
        "src_account": "ACC-1",
        "amount": "1500.50",
        "channel": "NPSB",
    }
    assert rows[1]["src_account"] == "ACC-2"


def test_parse_xlsx_datetime_cell_becomes_iso() -> None:
    # Excel date cells come back as datetime objects; downstream _parse_timestamp
    # needs ISO 8601, so the parser must stringify them.
    content = _xlsx_bytes([
        ["posted_at", "src_account", "amount"],
        [datetime(2026, 4, 1, 10, 30, 0), "ACC-1", 1500],
    ])
    rows = parse_xlsx(content)
    assert rows[0]["posted_at"] == "2026-04-01T10:30:00"
    assert rows[0]["amount"] == "1500"  # integer-valued float loses the .0 tail


def test_parse_xlsx_skips_blank_trailing_rows() -> None:
    content = _xlsx_bytes([
        ["posted_at", "src_account", "amount"],
        ["2026-04-01T10:30:00", "ACC-1", "100"],
        [None, None, None],
        ["", "", ""],
    ])
    rows = parse_xlsx(content)
    assert len(rows) == 1


def test_parse_xlsx_leading_blank_rows_before_header() -> None:
    content = _xlsx_bytes([
        [None, None, None],
        ["posted_at", "src_account", "amount"],
        ["2026-04-01T10:30:00", "ACC-1", "100"],
    ])
    rows = parse_xlsx(content)
    assert rows == [{"posted_at": "2026-04-01T10:30:00", "src_account": "ACC-1", "amount": "100"}]


def test_parse_xlsx_short_row_pads_missing_cells() -> None:
    content = _xlsx_bytes([
        ["posted_at", "src_account", "amount", "channel"],
        ["2026-04-01T10:30:00", "ACC-1", "100"],  # no channel cell
    ])
    rows = parse_xlsx(content)
    assert rows[0]["channel"] == ""


def test_parse_xlsx_empty_workbook_returns_empty() -> None:
    assert parse_xlsx(_xlsx_bytes([])) == []


def test_looks_like_xlsx_by_magic_and_extension() -> None:
    xlsx = _xlsx_bytes([["posted_at", "src_account", "amount"]])
    assert _looks_like_xlsx(xlsx, "statement.xlsx") is True
    assert _looks_like_xlsx(xlsx, None) is True  # ZIP magic bytes alone
    assert _looks_like_xlsx(b"posted_at,src_account,amount\n", "statement.csv") is False


def test_looks_like_legacy_xls_detected() -> None:
    assert _looks_like_legacy_xls(b"\xd0\xcf\x11\xe0junk", "old.xls") is True
    assert _looks_like_legacy_xls(b"posted_at,amount\n", "data.csv") is False
