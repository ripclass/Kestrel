"""UK Sanctions List adapter (FCDO).

Feed: https://sanctionslist.fcdo.gov.uk/docs/UK-Sanctions-List.csv

The legacy OFSI Consolidated List at ``docs.fcdo.gov.uk`` was retired on
28 January 2026; UK sanctions designations are now published as a
single unified list at the new ``sanctionslist.fcdo.gov.uk`` host. The
schema changed: each designation now occupies multiple rows sharing an
``OFSI Group ID``, with one ``Name type=Primary Name`` row plus zero
or more ``Name type=AKA`` rows for aliases.

We keep ``LIST_SOURCE = "UK_OFSI"`` for backward compatibility with
existing ``watchlist_entries`` rows seeded under that label.

The "Name 1" / "Name 6" columns are name parts (forename, middle,
surname, business name parts). Empty strings are common — we join the
non-empty parts in declared order.
"""
from __future__ import annotations

import csv
import io
import logging
from collections import defaultdict
from datetime import date, datetime
from typing import Any

import httpx

from app.screening.sources.base import ParsedWatchlistEntry

logger = logging.getLogger("kestrel.screening.uk_ofsi")

LIST_SOURCE = "UK_OFSI"
FEED_URL = "https://sanctionslist.fcdo.gov.uk/docs/UK-Sanctions-List.csv"


async def fetch() -> bytes:
    async with httpx.AsyncClient(timeout=60.0, follow_redirects=True) as client:
        response = await client.get(FEED_URL)
        response.raise_for_status()
        return response.content


def parse(content: bytes) -> list[ParsedWatchlistEntry]:
    list_version = datetime.utcnow().strftime("%Y-%m-%d")
    text = content.decode("utf-8-sig", errors="replace")
    text = _strip_preamble(text, list_version_out=list_version)
    reader = csv.DictReader(io.StringIO(text))

    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    ungrouped: list[dict[str, Any]] = []
    for row in reader:
        gid = (row.get("OFSI Group ID") or row.get("Group ID") or "").strip()
        if gid:
            grouped[gid].append(row)
        else:
            ungrouped.append(row)

    entries: list[ParsedWatchlistEntry] = []
    for gid, rows in grouped.items():
        entry = _parse_group(gid, rows, list_version)
        if entry:
            entries.append(entry)
    # Back-compat path: an old-format CSV without a Group ID column.
    for row in ungrouped:
        entry = _parse_group("", [row], list_version)
        if entry:
            entries.append(entry)
    return entries


def _parse_group(
    gid: str, rows: list[dict[str, Any]], list_version: str
) -> ParsedWatchlistEntry | None:
    primary_row = _pick_primary(rows)
    if primary_row is None:
        return None
    primary_name = _build_name(primary_row)
    if not primary_name:
        return None

    aliases: list[str] = []
    for row in rows:
        if row is primary_row:
            continue
        alias = _build_name(row)
        if alias and alias != primary_name and alias not in aliases:
            aliases.append(alias)

    entry_type = _classify_entry_type(primary_row)
    dob = _parse_date(primary_row.get("D.O.B") or primary_row.get("DOB") or primary_row.get("Date of Birth") or "")
    nationality = (
        primary_row.get("Nationality(/ies)")
        or primary_row.get("Nationality")
        or ""
    ).strip() or None

    identifiers: dict[str, list[str]] = {}
    passport = (primary_row.get("Passport number") or primary_row.get("Passport Number") or "").strip()
    if passport:
        identifiers["passport"] = [passport]
    nid = (
        primary_row.get("National Identifier number")
        or primary_row.get("National Identification Number")
        or ""
    ).strip()
    if nid:
        identifiers["nid"] = [nid]

    addresses = _build_addresses(primary_row)
    reason = (
        primary_row.get("UK Statement of Reasons")
        or primary_row.get("Other Information")
        or ""
    ).strip() or None

    return ParsedWatchlistEntry(
        list_source=LIST_SOURCE,
        list_version=list_version,
        entry_type=entry_type,
        primary_name=primary_name,
        aliases=aliases,
        date_of_birth=dob,
        nationality=nationality,
        identifiers=identifiers,
        addresses=addresses,
        reason=reason,
        raw_record={
            "group_id": gid or None,
            "regime": (primary_row.get("Regime Name") or "").strip() or None,
        },
    )


def _pick_primary(rows: list[dict[str, Any]]) -> dict[str, Any] | None:
    """Prefer rows tagged ``Name type=Primary Name``; fall back to the
    first row in the group when the column is missing (back-compat)."""
    for row in rows:
        name_type = (row.get("Name type") or "").strip().lower()
        if name_type in ("primary name", "primary"):
            return row
    return rows[0] if rows else None


def _classify_entry_type(row: dict[str, Any]) -> str:
    raw = (row.get("Individual, Entity, Ship") or row.get("Individual/Entity") or "").strip().lower()
    if raw.startswith("individual"):
        return "individual"
    if raw.startswith("ship"):
        return "vessel"
    if raw.startswith("aircraft"):
        return "aircraft"
    return "entity"


def _build_name(row: dict[str, Any]) -> str:
    parts = [(row.get(f"Name {i}") or "").strip() for i in range(1, 7)]
    return " ".join(p for p in parts if p)


def _build_addresses(row: dict[str, Any]) -> list[dict[str, Any]]:
    lines = [
        (row.get(f"Address Line {i}") or "").strip()
        for i in range(1, 7)
    ]
    line_str = ", ".join(p for p in lines if p)
    country = (row.get("Address Country") or "").strip()
    postal = (row.get("Address Postal Code") or row.get("Address Postcode") or "").strip()
    legacy = (row.get("Address") or "").strip()
    if not (line_str or country or postal or legacy):
        return []
    return [
        {
            "address1": line_str or legacy or None,
            "country": country or None,
            "postal_code": postal or None,
        }
    ]


def _strip_preamble(text: str, *, list_version_out: str) -> str:
    """The new UK Sanctions List CSV begins with a single ``Report Date:``
    line BEFORE the column header. Strip it so csv.DictReader picks up
    the real header. Tolerant of leading blank lines."""
    lines = text.splitlines(keepends=True)
    skip = 0
    for ln in lines:
        stripped = ln.strip()
        if not stripped:
            skip += 1
            continue
        if stripped.lower().startswith("report date"):
            skip += 1
            continue
        break
    return "".join(lines[skip:])


def _parse_date(value: str) -> date | None:
    if not value:
        return None
    value = value.strip()
    for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y", "%Y"):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    return None
