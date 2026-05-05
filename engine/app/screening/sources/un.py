"""UN Security Council Consolidated Sanctions List adapter.

Feed: https://scsanctions.un.org/resources/xml/en/consolidated.xml — daily.

Distinct individual / entity nodes; each has multiple aliases. The XML
schema is unnamespaced.
"""
from __future__ import annotations

import logging
from datetime import date, datetime
from typing import Any

import httpx
from lxml import etree

from app.screening.sources.base import ParsedWatchlistEntry

logger = logging.getLogger("kestrel.screening.un")

LIST_SOURCE = "UN"
FEED_URL = "https://scsanctions.un.org/resources/xml/en/consolidated.xml"


async def fetch() -> bytes:
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(FEED_URL)
        response.raise_for_status()
        return response.content


def parse(content: bytes) -> list[ParsedWatchlistEntry]:
    root = etree.fromstring(content)
    list_version = (root.get("dateGenerated") or datetime.utcnow().strftime("%Y-%m-%d")).strip()

    entries: list[ParsedWatchlistEntry] = []
    for individual in root.iterfind(".//INDIVIDUAL"):
        entry = _parse_individual(individual, list_version)
        if entry:
            entries.append(entry)
    for entity in root.iterfind(".//ENTITY"):
        entry = _parse_entity(entity, list_version)
        if entry:
            entries.append(entry)
    return entries


def _parse_individual(node: Any, list_version: str) -> ParsedWatchlistEntry | None:
    parts = [
        (node.findtext("FIRST_NAME") or "").strip(),
        (node.findtext("SECOND_NAME") or "").strip(),
        (node.findtext("THIRD_NAME") or "").strip(),
    ]
    primary_name = " ".join(p for p in parts if p)
    if not primary_name:
        return None

    aliases = [
        (alias.findtext("ALIAS_NAME") or "").strip()
        for alias in node.iterfind("INDIVIDUAL_ALIAS")
        if (alias.findtext("ALIAS_NAME") or "").strip()
    ]
    dob = _first_individual_dob(node)
    nationality = (node.findtext(".//NATIONALITY/VALUE") or "").strip() or None
    identifiers = _collect_individual_documents(node)
    addresses = _collect_addresses(node, "INDIVIDUAL_ADDRESS")
    reason = (node.findtext("UN_LIST_TYPE") or "").strip() or None

    return ParsedWatchlistEntry(
        list_source=LIST_SOURCE,
        list_version=list_version,
        entry_type="individual",
        primary_name=primary_name,
        aliases=aliases,
        date_of_birth=dob,
        nationality=nationality,
        identifiers=identifiers,
        addresses=addresses,
        reason=reason,
        raw_record={"reference_number": (node.findtext("REFERENCE_NUMBER") or "").strip()},
    )


def _parse_entity(node: Any, list_version: str) -> ParsedWatchlistEntry | None:
    primary_name = (node.findtext("FIRST_NAME") or "").strip()
    if not primary_name:
        return None
    aliases = [
        (alias.findtext("ALIAS_NAME") or "").strip()
        for alias in node.iterfind("ENTITY_ALIAS")
        if (alias.findtext("ALIAS_NAME") or "").strip()
    ]
    addresses = _collect_addresses(node, "ENTITY_ADDRESS")
    reason = (node.findtext("UN_LIST_TYPE") or "").strip() or None
    return ParsedWatchlistEntry(
        list_source=LIST_SOURCE,
        list_version=list_version,
        entry_type="entity",
        primary_name=primary_name,
        aliases=aliases,
        addresses=addresses,
        reason=reason,
        raw_record={"reference_number": (node.findtext("REFERENCE_NUMBER") or "").strip()},
    )


def _first_individual_dob(node: Any) -> date | None:
    dob_text = (node.findtext(".//INDIVIDUAL_DATE_OF_BIRTH/DATE") or "").strip()
    return _parse_date(dob_text) if dob_text else None


def _collect_individual_documents(node: Any) -> dict[str, Any]:
    identifiers: dict[str, list[str]] = {}
    for doc in node.iterfind(".//INDIVIDUAL_DOCUMENT"):
        kind = (doc.findtext("TYPE_OF_DOCUMENT") or "").strip().lower()
        number = (doc.findtext("NUMBER") or "").strip()
        if not kind or not number:
            continue
        bucket = "passport" if "passport" in kind else "nid" if "national" in kind else kind
        identifiers.setdefault(bucket, []).append(number)
    return identifiers


def _collect_addresses(node: Any, child_tag: str) -> list[dict[str, Any]]:
    addresses: list[dict[str, Any]] = []
    for addr in node.iterfind(child_tag):
        addresses.append(
            {
                "city": (addr.findtext("CITY") or "").strip() or None,
                "country": (addr.findtext("COUNTRY") or "").strip() or None,
                "address1": (addr.findtext("STREET") or "").strip() or None,
            }
        )
    return [a for a in addresses if any(a.values())]


def _parse_date(value: str) -> date | None:
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%Y"):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    return None
