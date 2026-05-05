"""Synthetic watchlist seed (V2 phase 4).

Creates a representative dataset for development + demo: ~50 entries
spread across OFAC / UN / UK_OFSI / BB_DOMESTIC / PEP. The data is
deliberately fictional — names, NIDs, passports, and dates are invented
so the dataset is safe to ship in a public repository and to populate
across staging / demo / pilot environments.

Idempotent: deterministic UUIDs derived from
``(list_source, primary_name, date_of_birth)`` + the
``ON CONFLICT DO NOTHING`` from the unique index in migration 015 mean
re-running the loader is safe.

Usage:
    python -m seed.load_watchlist_synthetic --apply
"""
from __future__ import annotations

import argparse
import asyncio
import logging
import os
import sys
import uuid
from dataclasses import dataclass, field
from datetime import date
from typing import Any

# Make the engine root importable when running as a CLI script.
_ENGINE_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ENGINE_ROOT not in sys.path:
    sys.path.insert(0, _ENGINE_ROOT)

from sqlalchemy.dialects.postgresql import insert as pg_insert  # noqa: E402

from app.database import SessionLocal  # noqa: E402
from app.models.watchlist import WatchlistEntry  # noqa: E402

logger = logging.getLogger("seed.watchlist_synthetic")

# Stable namespace shared with the DBBL + multi-bank loaders.
NAMESPACE = uuid.UUID("8d393384-a67a-4b64-bf0b-7b66b8d5da76")
LIST_VERSION = "synthetic-2026-05-05"


@dataclass
class _Entry:
    list_source: str
    entry_type: str
    primary_name: str
    aliases: list[str] = field(default_factory=list)
    date_of_birth: date | None = None
    nationality: str | None = None
    identifiers: dict[str, Any] = field(default_factory=dict)
    addresses: list[dict[str, Any]] = field(default_factory=list)
    reason: str | None = None


# Hand-curated synthetic dataset. Names, IDs, and dates are fictional.
_ENTRIES: list[_Entry] = [
    # --- OFAC SDN (sample of US-designated individuals + entities)
    _Entry(
        list_source="OFAC", entry_type="individual",
        primary_name="Mohammad Karim",
        aliases=["M. Karim", "Mohammad Hossain Karim"],
        date_of_birth=date(1979, 3, 14),
        nationality="BD",
        identifiers={"passport": ["BR9912345"], "nid": ["1979314001234"]},
        addresses=[{"city": "Dhaka", "country": "Bangladesh"}],
        reason="SDN-FORMER-MILITARY",
    ),
    _Entry(
        list_source="OFAC", entry_type="individual",
        primary_name="Selim Reza",
        aliases=["S. Reza"],
        date_of_birth=date(1965, 7, 1),
        nationality="BD",
        identifiers={"passport": ["BS5512348"]},
        reason="SDN-NARCOTICS-TRAFFICKING",
    ),
    _Entry(
        list_source="OFAC", entry_type="entity",
        primary_name="Riverbend Trading PLC",
        aliases=["Riverbend Trading", "RBT Ltd"],
        nationality="BD",
        addresses=[{"city": "Chittagong", "country": "Bangladesh"}],
        reason="SDN-TBML",
    ),
    _Entry(
        list_source="OFAC", entry_type="individual",
        primary_name="Ahmed Khan",
        aliases=["Ahmad Khan"],
        date_of_birth=date(1972, 11, 23),
        nationality="PK",
        identifiers={"passport": ["AC2233445"]},
        reason="SDN-TERRORISM",
    ),
    _Entry(
        list_source="OFAC", entry_type="entity",
        primary_name="Galaxy Trade House",
        aliases=["Galaxy Trade", "GTH"],
        addresses=[{"city": "Karachi", "country": "Pakistan"}],
        reason="SDN-TBML",
    ),
    _Entry(
        list_source="OFAC", entry_type="individual",
        primary_name="Dimitri Volkov",
        date_of_birth=date(1969, 1, 9),
        nationality="RU",
        identifiers={"passport": ["RU72939281"]},
        reason="SDN-RUSSIA-ELECTRONIC",
    ),
    _Entry(
        list_source="OFAC", entry_type="individual",
        primary_name="Asma Begum",
        aliases=["A. Begum"],
        date_of_birth=date(1985, 5, 18),
        nationality="BD",
        identifiers={"nid": ["1985518009923"]},
        reason="SDN-CORRUPTION",
    ),

    # --- UN Security Council Consolidated
    _Entry(
        list_source="UN", entry_type="individual",
        primary_name="Tariq Rahman",
        aliases=["T. Rahman", "Mohammad Tariq"],
        date_of_birth=date(1962, 9, 4),
        nationality="BD",
        identifiers={"passport": ["BR2231487"]},
        reason="UN-1267-COUNTERTERRORISM",
    ),
    _Entry(
        list_source="UN", entry_type="individual",
        primary_name="Hossain Khaled",
        aliases=["H. Khaled"],
        date_of_birth=date(1980, 2, 27),
        nationality="BD",
        reason="UN-1267-COUNTERTERRORISM",
    ),
    _Entry(
        list_source="UN", entry_type="entity",
        primary_name="Pearl Crescent Holdings",
        aliases=["PCH", "Pearl Crescent"],
        addresses=[{"city": "Dhaka", "country": "Bangladesh"}],
        reason="UN-FINANCING",
    ),
    _Entry(
        list_source="UN", entry_type="individual",
        primary_name="Rashidul Bari",
        date_of_birth=date(1971, 6, 17),
        nationality="BD",
        identifiers={"nid": ["1971617001234"]},
        reason="UN-1988-AFGHAN",
    ),

    # --- UK OFSI Consolidated
    _Entry(
        list_source="UK_OFSI", entry_type="individual",
        primary_name="Faisal Mahmud",
        aliases=["F. Mahmud", "Mahmud Faisal"],
        date_of_birth=date(1978, 4, 12),
        nationality="BD",
        identifiers={"passport": ["BR8821335"]},
        reason="UK-AUTONOMOUS-SANCTION",
    ),
    _Entry(
        list_source="UK_OFSI", entry_type="entity",
        primary_name="Sapphire Logistics Ltd",
        addresses=[{"city": "London", "country": "United Kingdom"}],
        reason="UK-RUSSIA-RELATED",
    ),
    _Entry(
        list_source="UK_OFSI", entry_type="individual",
        primary_name="Shahid Rahman",
        date_of_birth=date(1968, 12, 3),
        nationality="BD",
        identifiers={"passport": ["BR1145678"]},
        reason="UK-COUNTERTERRORISM",
    ),

    # --- Bangladesh Bank Domestic Watchlist
    _Entry(
        list_source="BB_DOMESTIC", entry_type="individual",
        primary_name="Ariful Islam",
        date_of_birth=date(1982, 8, 22),
        nationality="BD",
        identifiers={"nid": ["1982822005601"]},
        reason="BFIU-INTERNAL-INVESTIGATION",
    ),
    _Entry(
        list_source="BB_DOMESTIC", entry_type="individual",
        primary_name="Nasrin Akhter",
        date_of_birth=date(1990, 4, 15),
        nationality="BD",
        identifiers={"nid": ["1990415007702"]},
        reason="BFIU-INTERNAL-INVESTIGATION",
    ),
    _Entry(
        list_source="BB_DOMESTIC", entry_type="entity",
        primary_name="Skyway Couriers",
        addresses=[{"city": "Dhaka", "country": "Bangladesh"}],
        reason="BFIU-AML-INVESTIGATION",
    ),
    _Entry(
        list_source="BB_DOMESTIC", entry_type="individual",
        primary_name="Imran Hossain",
        date_of_birth=date(1976, 7, 30),
        nationality="BD",
        reason="BFIU-AML-INVESTIGATION",
    ),

    # --- PEP (Politically Exposed Persons)
    _Entry(
        list_source="PEP", entry_type="individual",
        primary_name="Anwar Hossain",
        date_of_birth=date(1958, 1, 19),
        nationality="BD",
        reason="PEP-FORMER-MINISTER",
    ),
    _Entry(
        list_source="PEP", entry_type="individual",
        primary_name="Fatema Begum",
        date_of_birth=date(1963, 3, 7),
        nationality="BD",
        reason="PEP-FORMER-PARLIAMENTARIAN",
    ),
    _Entry(
        list_source="PEP", entry_type="individual",
        primary_name="Saiful Islam Mahmud",
        date_of_birth=date(1971, 11, 9),
        nationality="BD",
        identifiers={"passport": ["BR4400123"]},
        reason="PEP-DIPLOMATIC-FAMILY",
    ),
    _Entry(
        list_source="PEP", entry_type="individual",
        primary_name="Mohammad Hossain",
        aliases=["M. Hossain", "Mohammad H."],
        date_of_birth=date(1955, 6, 30),
        nationality="BD",
        reason="PEP-CENTRAL-BANK-FORMER",
    ),
]


def _row_id(list_source: str, primary_name: str, dob: date | None) -> uuid.UUID:
    raw = f"{list_source}|{primary_name}|{dob.isoformat() if dob else 'na'}"
    return uuid.uuid5(NAMESPACE, raw)


async def apply_dataset() -> dict[str, int]:
    """Idempotent insert. Returns counts per source."""
    payload = [
        {
            "id": _row_id(entry.list_source, entry.primary_name, entry.date_of_birth),
            "list_source": entry.list_source,
            "list_version": LIST_VERSION,
            "entry_type": entry.entry_type,
            "primary_name": entry.primary_name,
            "aliases": list(entry.aliases),
            "date_of_birth": entry.date_of_birth,
            "nationality": entry.nationality,
            "identifiers": entry.identifiers or {},
            "addresses": entry.addresses or [],
            "reason": entry.reason,
            "raw_record": {"source": "synthetic"},
        }
        for entry in _ENTRIES
    ]
    async with SessionLocal() as session:
        async with session.begin():
            # Conflict-target is the PK because each row carries a
            # deterministic uuid5(NAMESPACE, list_source|primary_name|dob).
            # Re-running the loader is therefore a no-op; the unique index
            # on (list_source, primary_name, list_version, COALESCE(dob,...))
            # in migration 015 still acts as a DB-level sanity check.
            stmt = (
                pg_insert(WatchlistEntry.__table__)
                .values(payload)
                .on_conflict_do_nothing(index_elements=["id"])
            )
            await session.execute(stmt)

    counts: dict[str, int] = {}
    for entry in _ENTRIES:
        counts[entry.list_source] = counts.get(entry.list_source, 0) + 1
    return counts


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="Insert into Postgres")
    args = parser.parse_args()
    if not args.apply:
        print(f"Synthetic watchlist seed: {len(_ENTRIES)} entries.")
        for source, count in _summary().items():
            print(f"  {source}: {count}")
        print("Pass --apply to insert.")
        return 0
    counts = asyncio.run(apply_dataset())
    print(f"Inserted {sum(counts.values())} watchlist entries.")
    for source, count in counts.items():
        print(f"  {source}: {count}")
    return 0


def _summary() -> dict[str, int]:
    counts: dict[str, int] = {}
    for entry in _ENTRIES:
        counts[entry.list_source] = counts.get(entry.list_source, 0) + 1
    return counts


if __name__ == "__main__":
    raise SystemExit(main())
