"""Synthetic KYC customer seed (V2 phase 5).

Per-tenant idempotent loader. Generates ~30 customers per bank tenant:
25 individuals + 5 businesses, including:

  - 2 individuals whose names match Phase-4 watchlist entries (one OFAC,
    one PEP) so the screening flow has real "found" results.
  - 1 business whose beneficial-owner list includes a watchlist match.
  - The remainder are clean.

Deterministic UUIDs derived from ``(org_id, customer_external_id)`` make
re-runs idempotent.

Usage:
    python -m seed.load_customers_synthetic --org-id <uuid> --apply
    python -m seed.load_customers_synthetic --apply-all  # every bank tenant
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

# Make engine root importable when running as a CLI script.
_ENGINE_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ENGINE_ROOT not in sys.path:
    sys.path.insert(0, _ENGINE_ROOT)

from sqlalchemy import select  # noqa: E402
from sqlalchemy.dialects.postgresql import insert as pg_insert  # noqa: E402

from app.database import SessionLocal  # noqa: E402
from app.models.customer import Customer  # noqa: E402
from app.models.org import Organization  # noqa: E402

logger = logging.getLogger("seed.customers_synthetic")
NAMESPACE = uuid.UUID("8d393384-a67a-4b64-bf0b-7b66b8d5da76")


@dataclass
class _CustomerRow:
    customer_external_id: str
    customer_type: str
    full_name: str
    date_of_birth: date | None = None
    nationality: str = "BD"
    nid: str | None = None
    passport: str | None = None
    phone: str | None = None
    email: str | None = None
    beneficial_owners: list[dict[str, Any]] = field(default_factory=list)


# Hand-curated dataset. The two flagged individuals (Mohammad Karim, Anwar
# Hossain) match Phase-4 synthetic watchlist entries so the screening flow
# returns real results when these customers are screened.
_CUSTOMERS: list[_CustomerRow] = [
    _CustomerRow("CUST-0001", "individual", "Mohammad Karim", date(1979, 3, 14), "BD", "1979314001234", "BR9912345", "+880 1711-555-001", "mkarim@example.test"),
    _CustomerRow("CUST-0002", "individual", "Anwar Hossain", date(1958, 1, 19), "BD", "1958119001234", None, "+880 1711-555-002"),
    _CustomerRow("CUST-0003", "individual", "Rahima Khatun", date(1985, 6, 22), "BD", "1985622003344", None, "+880 1711-555-003"),
    _CustomerRow("CUST-0004", "individual", "Kamrul Hasan", date(1992, 11, 8), "BD", "1992118005566", None, "+880 1711-555-004"),
    _CustomerRow("CUST-0005", "individual", "Shamima Akhter", date(1989, 4, 17), "BD", "1989417007788", None, "+880 1711-555-005"),
    _CustomerRow("CUST-0006", "individual", "Mizanur Rahman", date(1975, 9, 30), "BD", "1975930001122", None, "+880 1711-555-006"),
    _CustomerRow("CUST-0007", "individual", "Nazia Sultana", date(1995, 12, 3), "BD", "1995123003344", None, "+880 1711-555-007"),
    _CustomerRow("CUST-0008", "individual", "Faruk Ahmed", date(1970, 7, 14), "BD", "1970714005566", None, "+880 1711-555-008"),
    _CustomerRow("CUST-0009", "individual", "Sabiha Begum", date(1988, 2, 25), "BD", "1988225007788", None, "+880 1711-555-009"),
    _CustomerRow("CUST-0010", "individual", "Tariq Aziz", date(1983, 8, 11), "BD", "1983811001122", None, "+880 1711-555-010"),
    _CustomerRow("CUST-0011", "individual", "Lipi Akter", date(1991, 5, 19), "BD", "1991519003344", None, "+880 1711-555-011"),
    _CustomerRow("CUST-0012", "individual", "Sohel Rana", date(1977, 10, 6), "BD", "1977106005566", None, "+880 1711-555-012"),
    _CustomerRow("CUST-0013", "individual", "Munira Khan", date(1986, 3, 28), "BD", "1986328007788", None, "+880 1711-555-013"),
    _CustomerRow("CUST-0014", "individual", "Iqbal Hossain", date(1981, 1, 9), "BD", "1981109001122", None, "+880 1711-555-014"),
    _CustomerRow("CUST-0015", "individual", "Rabeya Yasmin", date(1994, 7, 21), "BD", "1994721003344", None, "+880 1711-555-015"),
    _CustomerRow("CUST-0016", "individual", "Saiful Islam", date(1972, 12, 14), "BD", "1972214005566", None, "+880 1711-555-016"),
    _CustomerRow("CUST-0017", "individual", "Khaleda Begum", date(1980, 9, 5), "BD", "1980905007788", None, "+880 1711-555-017"),
    _CustomerRow("CUST-0018", "individual", "Habibur Rashid", date(1968, 4, 23), "BD", "1968423001122", None, "+880 1711-555-018"),
    _CustomerRow("CUST-0019", "individual", "Sumi Akter", date(1996, 8, 30), "BD", "1996830003344", None, "+880 1711-555-019"),
    _CustomerRow("CUST-0020", "individual", "Mahmudul Hasan", date(1984, 11, 12), "BD", "1984112005566", None, "+880 1711-555-020"),
    _CustomerRow("CUST-0021", "individual", "Nasrin Sultana", date(1990, 6, 4), "BD", "1990604007788", None, "+880 1711-555-021"),
    _CustomerRow("CUST-0022", "individual", "Bakhtiar Hossain", date(1973, 2, 17), "BD", "1973217001122", None, "+880 1711-555-022"),
    _CustomerRow("CUST-0023", "individual", "Yasmin Akter", date(1987, 10, 28), "BD", "1987028003344", None, "+880 1711-555-023"),
    _CustomerRow("CUST-0024", "individual", "Roman Hossain", date(1993, 5, 10), "BD", "1993510005566", None, "+880 1711-555-024"),
    _CustomerRow("CUST-0025", "individual", "Bilkis Begum", date(1976, 12, 2), "BD", "1976212007788", None, "+880 1711-555-025"),
    # Businesses (5; one with a flagged beneficial owner)
    _CustomerRow(
        "CUST-B001", "business", "Padma Trading Ltd",
        beneficial_owners=[
            {
                "full_name": "Tariq Rahman",
                "nid": None,
                "passport": "BR2231487",
                "date_of_birth": "1962-09-04",
                "nationality": "BD",
                "ownership_pct": 60.0,
            },
            {
                "full_name": "Rasel Mahmud",
                "nationality": "BD",
                "ownership_pct": 40.0,
            },
        ],
    ),
    _CustomerRow(
        "CUST-B002", "business", "Jamuna Logistics PLC",
        beneficial_owners=[{"full_name": "Faisal Hossain", "nationality": "BD", "ownership_pct": 100.0}],
    ),
    _CustomerRow(
        "CUST-B003", "business", "Meghna Foods Co.",
        beneficial_owners=[
            {"full_name": "Selim Mahmud", "nationality": "BD", "ownership_pct": 55.0},
            {"full_name": "Khadija Begum", "nationality": "BD", "ownership_pct": 45.0},
        ],
    ),
    _CustomerRow(
        "CUST-B004", "business", "Karnaphuli Textiles Ltd",
        beneficial_owners=[{"full_name": "Atiqur Rahman", "nationality": "BD", "ownership_pct": 100.0}],
    ),
    _CustomerRow(
        "CUST-B005", "business", "Buriganga Holdings",
        beneficial_owners=[
            {"full_name": "Mahbub Alam", "nationality": "BD", "ownership_pct": 70.0},
            {"full_name": "Ruhul Amin", "nationality": "BD", "ownership_pct": 30.0},
        ],
    ),
]


def _row_id(org_id: uuid.UUID, external_id: str) -> uuid.UUID:
    return uuid.uuid5(NAMESPACE, f"customer|{org_id}|{external_id}")


async def apply_for_org(org_id: uuid.UUID) -> dict[str, int]:
    payload = [
        {
            "id": _row_id(org_id, customer.customer_external_id),
            "org_id": org_id,
            "customer_external_id": customer.customer_external_id,
            "customer_type": customer.customer_type,
            "full_name": customer.full_name,
            "nid": customer.nid,
            "passport": customer.passport,
            "date_of_birth": customer.date_of_birth,
            "nationality": customer.nationality,
            "phone": customer.phone,
            "email": customer.email,
            "address": {"city": "Dhaka", "country": "Bangladesh"},
            "metadata": {"source": "synthetic"},
            "beneficial_owners": list(customer.beneficial_owners or []),
            # Risk fields and screening_results are intentionally null —
            # the synthetic seed is "pre-onboarded" data; the operator can
            # rescreen via POST /customers/{id}/rescreen to populate them
            # against the live watchlist pool.
            "risk_score": None,
            "risk_level": None,
            "kyc_status": "pending",
            "screening_results": {},
        }
        for customer in _CUSTOMERS
    ]
    async with SessionLocal() as session:
        async with session.begin():
            stmt = (
                pg_insert(Customer.__table__)
                .values(payload)
                .on_conflict_do_nothing(index_elements=["id"])
            )
            await session.execute(stmt)
    return {
        "individuals": sum(1 for c in _CUSTOMERS if c.customer_type == "individual"),
        "businesses": sum(1 for c in _CUSTOMERS if c.customer_type == "business"),
    }


async def apply_for_all_banks() -> list[dict[str, Any]]:
    async with SessionLocal() as session:
        result = await session.execute(
            select(Organization.id, Organization.name).where(Organization.org_type == "bank")
        )
        banks = list(result.all())

    rows: list[dict[str, Any]] = []
    for org_id, name in banks:
        try:
            counts = await apply_for_org(org_id)
            rows.append({"org_id": str(org_id), "name": name, **counts})
        except Exception as exc:
            rows.append({"org_id": str(org_id), "name": name, "error": type(exc).__name__})
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--org-id", help="Apply to one specific org UUID")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--apply-all", action="store_true", help="Apply to every bank tenant")
    args = parser.parse_args()

    if not (args.apply or args.apply_all):
        print(f"Synthetic customer seed: {len(_CUSTOMERS)} rows per tenant.")
        print(
            f"  individuals: {sum(1 for c in _CUSTOMERS if c.customer_type == 'individual')}"
        )
        print(
            f"  businesses:  {sum(1 for c in _CUSTOMERS if c.customer_type == 'business')}"
        )
        print("Pass --apply --org-id <uuid> for one tenant or --apply-all for every bank tenant.")
        return 0

    if args.apply_all:
        rows = asyncio.run(apply_for_all_banks())
        for row in rows:
            print(row)
        return 0

    if args.org_id:
        org_id = uuid.UUID(args.org_id)
        counts = asyncio.run(apply_for_org(org_id))
        print(f"Applied to {org_id}: {counts}")
        return 0

    print("Pass --org-id <uuid> with --apply, or use --apply-all.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
