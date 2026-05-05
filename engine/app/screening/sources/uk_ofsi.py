"""UK OFSI Consolidated Sanctions List adapter.

Feed: https://docs.fcdo.gov.uk/docs/UK-Sanctions-List.csv (CSV).

Schema (v1, columns vary; defensive lookup): Name 6 / Name 1 build the
primary; Aliases column is semicolon-separated; DOB/Nationality columns
are present for individuals; Group ID is the row identifier.
"""
from __future__ import annotations

import csv
import io
import logging
from datetime import date, datetime
from typing import Any

import httpx

from app.screening.sources.base import ParsedWatchlistEntry

logger = logging.getLogger("kestrel.screening.uk_ofsi")

LIST_SOURCE = "UK_OFSI"
FEED_URL = "https://docs.fcdo.gov.uk/docs/UK-Sanctions-List.csv"


async def fetch() -> bytes:
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(FEED_URL)
        response.raise_for_status()
        return response.content


def parse(content: bytes) -> list[ParsedWatchlistEntry]:
    list_version = datetime.utcnow().strftime("%Y-%m-%d")
    text = content.decode("utf-8-sig", errors="replace")
    reader = csv.DictReader(io.StringIO(text))
    entries: list[ParsedWatchlistEntry] = []
    for row in reader:
        entry = _parse_row(row, list_version)
        if entry:
            entries.append(entry)
    return entries


def _parse_row(row: dict[str, Any], list_version: str) -> ParsedWatchlistEntry | None:
    name = _build_primary_name(row)
    if not name:
        return None
    entry_type = (row.get("Individual, Entity, Ship") or row.get("Individual/Entity") or "").strip().lower()
    if entry_type.startswith("individual"):
        entry_type = "individual"
    elif entry_type.startswith("ship"):
        entry_type = "vessel"
    elif entry_type.startswith("aircraft"):
        entry_type = "aircraft"
    else:
        entry_type = "entity"

    aliases_raw = row.get("Aliases") or row.get("AKAs") or ""
    aliases = [a.strip() for a in aliases_raw.split(";") if a.strip()]

    dob = _parse_date(row.get("DOB") or row.get("Date of Birth") or "")
    nationality = (row.get("Nationality") or "").strip() or None
    passport = (row.get("Passport Number") or "").strip()
    nid = (row.get("National Identification Number") or "").strip()

    identifiers: dict[str, list[str]] = {}
    if passport:
        identifiers["passport"] = [passport]
    if nid:
        identifiers["nid"] = [nid]

    addresses_raw = row.get("Address") or ""
    addresses = (
        [{"address1": addresses_raw.strip()}] if addresses_raw.strip() else []
    )
    reason = (row.get("Other Information") or "").strip() or None

    return ParsedWatchlistEntry(
        list_source=LIST_SOURCE,
        list_version=list_version,
        entry_type=entry_type,
        primary_name=name,
        aliases=aliases,
        date_of_birth=dob,
        nationality=nationality,
        identifiers=identifiers,
        addresses=addresses,
        reason=reason,
        raw_record={"group_id": (row.get("Group ID") or "").strip() or None},
    )


def _build_primary_name(row: dict[str, Any]) -> str:
    parts = [
        (row.get(f"Name {i}") or "").strip()
        for i in range(1, 7)
    ]
    return " ".join(p for p in parts if p)


def _parse_date(value: str) -> date | None:
    if not value:
        return None
    for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%Y"):
        try:
            return datetime.strptime(value.strip(), fmt).date()
        except ValueError:
            continue
    return None
