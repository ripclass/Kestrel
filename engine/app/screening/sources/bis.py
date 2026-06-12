"""US BIS denied-party / entity-list adapter (via the trade.gov CSL).

Feed: https://data.trade.gov/downloadable_consolidated_screening_list/v1/consolidated.csv

The US Consolidated Screening List (CSL) bundles the export-screening lists
of Commerce, State and Treasury into one daily CSV. We pull the whole file
and keep only the **Bureau of Industry and Security (BIS)** sublists —
Denied Persons List (DPL), Entity List (EL), Unverified List (UVL) — under
``LIST_SOURCE = "BIS"``. Everything else is dropped:
  * SDN rows are OFAC and already ingested by ``ofac.py`` — keeping them here
    would double-ingest the same designations under a different label.
  * DTC (AECA Debarred) and ISN (Nonproliferation) are State Department, out
    of scope for the BIS ask.

Pilot-driven: Sonali Bank is trade-finance heavy and screening LC
counterparties against BIS denied-party / entity lists is core
proliferation-financing control (FATF Rec 7 + BFIU PF guidance). Complements
the Phase-B TBML module.

CSV schema (27 cols, documented in trade.gov's CSL download instructions):
``source`` is a short code (DPL/EL/UVL/SDN/DTC/ISN); ``name`` is the primary
name; ``alt_names`` / ``addresses`` / ``dates_of_birth`` / ``nationalities`` /
``citizenships`` are semicolon-separated. We read by column NAME via
DictReader and match the BIS sublists defensively (code OR full-label
substring) so a distribution that ships full labels instead of codes still
parses — same robustness philosophy as the OFAC namespace sniff and the UK
preamble strip.
"""
from __future__ import annotations

import csv
import io
import logging
from datetime import date, datetime
from typing import Any

import httpx

from app.screening.sources.base import ParsedWatchlistEntry

logger = logging.getLogger("kestrel.screening.bis")

LIST_SOURCE = "BIS"
FEED_URL = "https://data.trade.gov/downloadable_consolidated_screening_list/v1/consolidated.csv"

# CSL `source` short codes that originate from BIS, mapped to a friendly label
# carried into `reason` so a match result shows WHICH BIS list fired.
_BIS_CODES: dict[str, str] = {
    "DPL": "BIS Denied Persons List",
    "EL": "BIS Entity List",
    "UVL": "BIS Unverified List",
    "MEU": "BIS Military End User List",
}
# Full-label fallbacks (some CSL distributions ship the long name, not the code).
_BIS_LABEL_HINTS: tuple[str, ...] = (
    "bureau of industry",
    "denied persons",
    "entity list",
    "unverified list",
    "military end user",
)


async def fetch() -> bytes:
    async with httpx.AsyncClient(timeout=90.0, follow_redirects=True) as client:
        response = await client.get(FEED_URL)
        response.raise_for_status()
        return response.content


def parse(content: bytes) -> list[ParsedWatchlistEntry]:
    list_version = datetime.utcnow().strftime("%Y-%m-%d")
    text = content.decode("utf-8-sig", errors="replace")
    reader = csv.DictReader(io.StringIO(text))

    entries: list[ParsedWatchlistEntry] = []
    for row in reader:
        sublist = _bis_sublist(row.get("source"))
        if sublist is None:
            continue  # not a BIS row — skip (SDN/DTC/ISN/etc.)
        entry = _parse_row(row, sublist, list_version)
        if entry:
            entries.append(entry)
    return entries


def _bis_sublist(source_value: str | None) -> str | None:
    """Return the friendly BIS sublist label if this row is BIS, else None.

    Accepts both the short code (``EL``) and a full label
    (``Entity List (EL) - Bureau of Industry and Security``)."""
    if not source_value:
        return None
    raw = source_value.strip()
    code = raw.upper()
    if code in _BIS_CODES:
        return _BIS_CODES[code]
    lowered = raw.lower()
    for hint in _BIS_LABEL_HINTS:
        if hint in lowered:
            # Prefer a known code embedded in the label, else use the raw label.
            for c, label in _BIS_CODES.items():
                if f"({c.lower()})" in lowered or label.lower() in lowered:
                    return label
            return raw
    return None


def _parse_row(
    row: dict[str, Any], sublist: str, list_version: str
) -> ParsedWatchlistEntry | None:
    primary_name = (row.get("name") or "").strip()
    if not primary_name:
        return None

    entry_type = _classify_entry_type(row.get("type"))
    aliases = _split_semicolons(row.get("alt_names"))
    dob = _first_date(_split_semicolons(row.get("dates_of_birth")))
    nationality = _first_nonempty(
        _split_semicolons(row.get("nationalities")) + _split_semicolons(row.get("citizenships"))
    )
    addresses = [
        {"address1": addr} for addr in _split_semicolons(row.get("addresses"))
    ]

    reason_bits = [sublist]
    programs = (row.get("programs") or "").strip()
    if programs:
        reason_bits.append(programs)
    license_req = (row.get("license_requirement") or "").strip()
    if license_req:
        reason_bits.append(f"licence: {license_req}")
    reason = " · ".join(reason_bits) or None

    return ParsedWatchlistEntry(
        list_source=LIST_SOURCE,
        list_version=list_version,
        entry_type=entry_type,
        primary_name=primary_name,
        aliases=aliases,
        date_of_birth=dob,
        nationality=nationality,
        identifiers={},  # the CSL delimited file carries no passport/NID columns
        addresses=addresses,
        reason=reason,
        raw_record={
            "source_code": (row.get("source") or "").strip() or None,
            "sublist": sublist,
            "entity_number": (row.get("entity_number") or "").strip() or None,
            "federal_register_notice": (row.get("federal_register_notice") or "").strip() or None,
            "standard_order": (row.get("standard_order") or "").strip() or None,
            "source_list_url": (row.get("source_list_url") or "").strip() or None,
        },
    )


def _classify_entry_type(raw: str | None) -> str:
    """CSL `type` flags individual / vessel; BIS entity-list rows are usually
    blank → companies. Default to ``entity`` (the dominant BIS shape)."""
    value = (raw or "").strip().lower()
    if value.startswith("individual"):
        return "individual"
    if value.startswith("vessel"):
        return "vessel"
    if value.startswith("aircraft"):
        return "aircraft"
    return "entity"


def _split_semicolons(value: str | None) -> list[str]:
    if not value:
        return []
    return [part.strip() for part in value.split(";") if part.strip()]


def _first_nonempty(values: list[str]) -> str | None:
    for value in values:
        if value:
            return value
    return None


def _first_date(values: list[str]) -> date | None:
    for value in values:
        parsed = _parse_date(value)
        if parsed:
            return parsed
    return None


def _parse_date(value: str) -> date | None:
    value = (value or "").strip()
    if not value:
        return None
    for fmt in ("%d %b %Y", "%d %B %Y", "%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%Y"):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    return None
