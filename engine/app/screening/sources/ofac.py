"""OFAC SDN List adapter (US Treasury).

Feed: https://sanctionslistservice.ofac.treas.gov/api/PublicationPreview/exports/SDN.XML
— daily refresh. The legacy ``www.treasury.gov/ofac/downloads/sdn.xml`` URL
was retired when OFAC consolidated distribution under the Sanctions List
Service. The new endpoint returns a 302 redirect to a presigned S3 URL,
so the fetch must follow redirects.

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
FEED_URL = "https://sanctionslistservice.ofac.treas.gov/api/PublicationPreview/exports/SDN.XML"


async def fetch() -> bytes:
    async with httpx.AsyncClient(timeout=60.0, follow_redirects=True) as client:
        response = await client.get(FEED_URL)
        response.raise_for_status()
        return response.content


def parse(content: bytes) -> list[ParsedWatchlistEntry]:
    """Parse the OFAC SDN XML.

    The default namespace on ``<sdnList>`` changed when OFAC migrated to
    the Sanctions List Service host (see the May 2024 announcement).
    Rather than hardcode the URI, we sniff it from ``root.nsmap[None]``
    at parse time — works against the legacy ``http://tempuri.org/...``
    namespace AND the new ``https://sanctionslistservice...`` one
    without any further changes."""
    root = etree.fromstring(content)
    ns_uri = root.nsmap.get(None)
    ns = {"sdn": ns_uri} if ns_uri else {}
    list_version = _extract_publish_date(root, ns) or datetime.utcnow().strftime("%Y-%m-%d")

    sdn_xpath = ".//sdn:sdnEntry" if ns else ".//sdnEntry"
    entries: list[ParsedWatchlistEntry] = []
    for sdn in root.iterfind(sdn_xpath, ns):
        entry = _parse_entry(sdn, list_version, ns)
        if entry:
            entries.append(entry)
    return entries


def _xp(rel: str, ns: dict) -> str:
    """Prefix every path segment with sdn: when the namespace exists.
    A no-op when the XML is unnamespaced (lets unit tests run without
    constructing a namespaced XML fixture)."""
    if not ns:
        return rel
    parts = rel.split("/")
    return "/".join(("" if p in ("", ".") else f"sdn:{p}") for p in parts) if "/" in rel else f"sdn:{rel}"


def _extract_publish_date(root: Any, ns: dict) -> str | None:
    info = root.find(_xp("publshInformation", ns) if ns else ".//publshInformation", ns)
    if info is None:
        return None
    pub = info.findtext(_xp("Publish_Date", ns), namespaces=ns)
    return pub.strip() if pub else None


def _parse_entry(sdn: Any, list_version: str, ns: dict) -> ParsedWatchlistEntry | None:
    sdn_type = (sdn.findtext(_xp("sdnType", ns), default="", namespaces=ns) or "").strip().lower()
    entry_type = "individual" if sdn_type == "individual" else "entity"

    last = (sdn.findtext(_xp("lastName", ns), default="", namespaces=ns) or "").strip()
    first = (sdn.findtext(_xp("firstName", ns), default="", namespaces=ns) or "").strip()
    primary_name = " ".join(part for part in (first, last) if part).strip()
    if not primary_name:
        return None

    aliases: list[str] = []
    aka_path = ".//sdn:aka" if ns else ".//aka"
    for aka in sdn.iterfind(aka_path, ns):
        a_first = (aka.findtext(_xp("firstName", ns), default="", namespaces=ns) or "").strip()
        a_last = (aka.findtext(_xp("lastName", ns), default="", namespaces=ns) or "").strip()
        alias = " ".join(part for part in (a_first, a_last) if part).strip()
        if alias and alias != primary_name:
            aliases.append(alias)

    dob = _first_dob(sdn, ns)
    nationality = _first_nationality(sdn, ns)
    identifiers = _collect_identifiers(sdn, ns)
    addresses = _collect_addresses(sdn, ns)
    program_path = "sdn:programList/sdn:program" if ns else "programList/program"
    program = (sdn.findtext(program_path, default="", namespaces=ns) or "").strip()

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


def _first_dob(sdn: Any, ns: dict) -> date | None:
    path = ".//sdn:dateOfBirthItem/sdn:dateOfBirth" if ns else ".//dateOfBirthItem/dateOfBirth"
    dob_text = sdn.findtext(path, default="", namespaces=ns)
    if not dob_text:
        return None
    return _parse_date(dob_text)


def _first_nationality(sdn: Any, ns: dict) -> str | None:
    path = ".//sdn:nationality/sdn:country" if ns else ".//nationality/country"
    nat = sdn.findtext(path, default="", namespaces=ns)
    return nat.strip() or None if nat else None


def _collect_identifiers(sdn: Any, ns: dict) -> dict[str, Any]:
    identifiers: dict[str, list[str]] = {}
    path = ".//sdn:idList/sdn:id" if ns else ".//idList/id"
    for item in sdn.iterfind(path, ns):
        kind = (item.findtext(_xp("idType", ns), default="", namespaces=ns) or "").strip().lower()
        number = (item.findtext(_xp("idNumber", ns), default="", namespaces=ns) or "").strip()
        if not kind or not number:
            continue
        bucket = "passport" if "passport" in kind else "nid" if "national" in kind else kind
        identifiers.setdefault(bucket, []).append(number)
    return identifiers


def _collect_addresses(sdn: Any, ns: dict) -> list[dict[str, Any]]:
    addresses: list[dict[str, Any]] = []
    path = ".//sdn:addressList/sdn:address" if ns else ".//addressList/address"
    for addr in sdn.iterfind(path, ns):
        addresses.append(
            {
                "city": (addr.findtext(_xp("city", ns), default="", namespaces=ns) or "").strip() or None,
                "country": (addr.findtext(_xp("country", ns), default="", namespaces=ns) or "").strip() or None,
                "address1": (addr.findtext(_xp("address1", ns), default="", namespaces=ns) or "").strip() or None,
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
