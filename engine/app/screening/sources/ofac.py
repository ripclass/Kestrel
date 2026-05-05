"""OFAC SDN List adapter (US Treasury).

Feed: https://www.treasury.gov/ofac/downloads/sdn.xml — daily refresh.

The XML root is ``sdnList``; each entry is ``sdnEntry`` with ``firstName`` /
``lastName`` (individuals) or ``sdnType="Entity"`` with ``firstName`` only.
We flatten aka entries into the aliases array.
"""
from __future__ import annotations

import logging
from datetime import date, datetime
from typing import Any

import httpx
from lxml import etree

from app.screening.sources.base import ParsedWatchlistEntry

logger = logging.getLogger("kestrel.screening.ofac")

LIST_SOURCE = "OFAC"
FEED_URL = "https://www.treasury.gov/ofac/downloads/sdn.xml"
_NS = {"sdn": "http://tempuri.org/sdnList.xsd"}


async def fetch() -> bytes:
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(FEED_URL)
        response.raise_for_status()
        return response.content


def parse(content: bytes) -> list[ParsedWatchlistEntry]:
    root = etree.fromstring(content)
    list_version = _extract_publish_date(root) or datetime.utcnow().strftime("%Y-%m-%d")

    entries: list[ParsedWatchlistEntry] = []
    for sdn in root.iterfind(".//sdn:sdnEntry", _NS):
        entry = _parse_entry(sdn, list_version)
        if entry:
            entries.append(entry)
    return entries


def _extract_publish_date(root: Any) -> str | None:
    info = root.find(".//sdn:publshInformation", _NS)
    if info is None:
        return None
    pub = info.findtext("sdn:Publish_Date", default=None, namespaces=_NS)
    return pub.strip() if pub else None


def _parse_entry(sdn: Any, list_version: str) -> ParsedWatchlistEntry | None:
    sdn_type = (sdn.findtext("sdn:sdnType", default="", namespaces=_NS) or "").strip().lower()
    entry_type = "individual" if sdn_type == "individual" else "entity"

    last = (sdn.findtext("sdn:lastName", default="", namespaces=_NS) or "").strip()
    first = (sdn.findtext("sdn:firstName", default="", namespaces=_NS) or "").strip()
    primary_name = " ".join(part for part in (first, last) if part).strip()
    if not primary_name:
        return None

    aliases: list[str] = []
    for aka in sdn.iterfind(".//sdn:aka", _NS):
        a_first = (aka.findtext("sdn:firstName", default="", namespaces=_NS) or "").strip()
        a_last = (aka.findtext("sdn:lastName", default="", namespaces=_NS) or "").strip()
        alias = " ".join(part for part in (a_first, a_last) if part).strip()
        if alias and alias != primary_name:
            aliases.append(alias)

    dob = _first_dob(sdn)
    nationality = _first_nationality(sdn)
    identifiers = _collect_identifiers(sdn)
    addresses = _collect_addresses(sdn)
    program = (sdn.findtext("sdn:programList/sdn:program", default="", namespaces=_NS) or "").strip()

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
        reason=program or None,
        raw_record={"sdn_type": sdn_type, "program": program},
    )


def _first_dob(sdn: Any) -> date | None:
    dob_text = sdn.findtext(".//sdn:dateOfBirthItem/sdn:dateOfBirth", default="", namespaces=_NS)
    if not dob_text:
        return None
    return _parse_date(dob_text)


def _first_nationality(sdn: Any) -> str | None:
    nat = sdn.findtext(".//sdn:nationality/sdn:country", default="", namespaces=_NS)
    return nat.strip() or None if nat else None


def _collect_identifiers(sdn: Any) -> dict[str, Any]:
    identifiers: dict[str, list[str]] = {}
    for item in sdn.iterfind(".//sdn:idList/sdn:id", _NS):
        kind = (item.findtext("sdn:idType", default="", namespaces=_NS) or "").strip().lower()
        number = (item.findtext("sdn:idNumber", default="", namespaces=_NS) or "").strip()
        if not kind or not number:
            continue
        bucket = "passport" if "passport" in kind else "nid" if "national" in kind else kind
        identifiers.setdefault(bucket, []).append(number)
    return identifiers


def _collect_addresses(sdn: Any) -> list[dict[str, Any]]:
    addresses: list[dict[str, Any]] = []
    for addr in sdn.iterfind(".//sdn:addressList/sdn:address", _NS):
        addresses.append(
            {
                "city": (addr.findtext("sdn:city", default="", namespaces=_NS) or "").strip() or None,
                "country": (addr.findtext("sdn:country", default="", namespaces=_NS) or "").strip() or None,
                "address1": (addr.findtext("sdn:address1", default="", namespaces=_NS) or "").strip() or None,
            }
        )
    return [a for a in addresses if any(a.values())]


def _parse_date(value: str) -> date | None:
    """OFAC dates can be 'DD MMM YYYY', 'YYYY', etc. Best-effort parse."""
    value = value.strip()
    for fmt in ("%d %b %Y", "%d %B %Y", "%Y-%m-%d", "%Y"):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    return None
