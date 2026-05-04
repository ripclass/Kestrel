"""Multi-bank synthetic seed for cross-bank intelligence demos (V2 phase 1.2).

Currently DBBL is the only bank with populated transactional data on prod
(`load_dbbl_synthetic.py`). This module adds ~30 transactions and ~8 entities
to each of BRAC, City, Islami, Sonali — with explicit cross-bank overlap so
the cross-bank intelligence dashboard (V2 phase 1.1) has live data to render
on prod.

Idempotent: deterministic UUIDs from the same NAMESPACE used by the DBBL
loader so repeat applications upsert in-place rather than duplicating rows.
The marquee 5-bank entity also adds DBBL to its reporting_orgs (without
adding new DBBL transactions, since DBBL is already populated).

Cross-bank topology built into the dataset:
    * 1 marquee entity reported by all 5 banks (the "this account is
      flagged at 5 institutions" demo).
    * 2 entities reported by 3 banks each.
    * 3 entities reported by 2 banks each.
    * Plus per-bank single-institution entities to fill each bank to
      ~8 entity-bank pairs.

Run:  python -m seed.load_multi_bank_synthetic --apply
"""
from __future__ import annotations

import argparse
import asyncio
import json
import random
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Iterable
from urllib.parse import urlparse
from uuid import UUID, uuid5

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from app.config import get_settings
from app.database import SessionLocal
from app.models.account import Account
from app.models.alert import Alert
from app.models.entity import Entity
from app.models.match import Match
from app.models.org import Organization
from app.models.str_report import STRReport
from app.models.transaction import Transaction
from seed.organizations import build_organizations

# Shared UUID namespace with the DBBL loader so re-runs upsert in place.
NAMESPACE = UUID("8d393384-a67a-4b64-bf0b-7b66b8d5da76")

# Fixed-seed RNG so amounts/dates are deterministic across runs.
RNG_SEED = 20260504


def _stable_uuid(kind: str, value: str) -> UUID:
    return uuid5(NAMESPACE, f"{kind}:multi:{value}")


# -----------------------------------------------------------------------------
# Dataset definition
# -----------------------------------------------------------------------------

@dataclass(frozen=True)
class CrossBankEntity:
    """An entity that's reported by 2+ banks. The matcher would normally
    populate this when 2+ STRs converge on the same identifier; we insert
    the rows directly so the cross-bank dashboard has data without needing
    to trigger the pipeline."""
    key: str                  # stable identifier for UUID derivation
    entity_type: str          # account | phone | nid | wallet | person
    canonical_value: str
    display_value: str
    display_name: str
    risk_score: int
    severity: str             # critical | high | medium | low
    bank_slugs: list[str]     # which banks report this entity (slugs from organizations.py)
    narrative_hook: str


@dataclass(frozen=True)
class SingleBankEntity:
    """An entity reported by only one bank. Padding to bring each bank
    to ~8 entities total."""
    key: str
    entity_type: str
    canonical_value: str
    display_value: str
    display_name: str
    risk_score: int
    severity: str
    bank_slug: str
    narrative_hook: str


def _cross_bank_entities() -> list[CrossBankEntity]:
    return [
        # Marquee 5-bank entity
        CrossBankEntity(
            key="marquee-5bank-phone",
            entity_type="phone",
            canonical_value="+8801711555001",
            display_value="+880 1711-555-001",
            display_name="Mohammad Karim (5-bank flag)",
            risk_score=94,
            severity="critical",
            bank_slugs=["brac-bank", "city-bank", "dutch-bangla-bank", "islami-bank", "sonali-bank"],
            narrative_hook="Subject phone surfaces on STRs from five reporting institutions over the trailing 30 days. Concurrent activity across NPSB, BEFTN, and MFS rails.",
        ),
        # Two 3-bank entities
        CrossBankEntity(
            key="3bank-nid-rapid-cashout",
            entity_type="nid",
            canonical_value="1234567890123",
            display_value="1234567890123",
            display_name="Rashedul Alam (NID — 3-bank)",
            risk_score=82,
            severity="high",
            bank_slugs=["brac-bank", "city-bank", "islami-bank"],
            narrative_hook="Identical NID linked to high-velocity cashout patterns at three banks within a 14-day window.",
        ),
        CrossBankEntity(
            key="3bank-phone-layering",
            entity_type="phone",
            canonical_value="+8801711555002",
            display_value="+880 1711-555-002",
            display_name="Selim Reza (layering ring)",
            risk_score=78,
            severity="high",
            bank_slugs=["city-bank", "sonali-bank", "dutch-bangla-bank"],
            narrative_hook="Same handset-number observed routing layered transfers across three institutions on the same business day.",
        ),
        # Three 2-bank entities
        CrossBankEntity(
            key="2bank-account-structuring",
            entity_type="account",
            canonical_value="2001045555701",
            display_value="2001045555701",
            display_name="Asma Begum (structuring)",
            risk_score=71,
            severity="high",
            bank_slugs=["brac-bank", "sonali-bank"],
            narrative_hook="Counterparty account presents structuring breaks across two scheduled banks; thresholds tuned just under reportable limits.",
        ),
        CrossBankEntity(
            key="2bank-phone-mfs-bridge",
            entity_type="phone",
            canonical_value="+8801711555003",
            display_value="+880 1711-555-003",
            display_name="Tanvir Hossain (MFS bridge)",
            risk_score=66,
            severity="medium",
            bank_slugs=["islami-bank", "dutch-bangla-bank"],
            narrative_hook="Phone number bridges fund movement between an Islamic-banking deposit and a DBBL counterparty via MFS top-up.",
        ),
        CrossBankEntity(
            key="2bank-nid-tbml",
            entity_type="nid",
            canonical_value="9876543210987",
            display_value="9876543210987",
            display_name="Habibur Rahman (TBML)",
            risk_score=63,
            severity="medium",
            bank_slugs=["city-bank", "brac-bank"],
            narrative_hook="NID linked to LC-backed transactions with declared-vs-invoice value gaps at two reporting banks.",
        ),
    ]


def _single_bank_entities() -> list[SingleBankEntity]:
    """Pad each new bank to ~8 entities. Mix of account / phone / NID / person
    types to keep dossiers realistic."""
    return [
        # BRAC
        SingleBankEntity("brac-acc-001", "account", "1501023401001", "1501023401001", "Sumi Akhter", 54, "medium", "brac-bank", "Single-bank BRAC current-account anomaly"),
        SingleBankEntity("brac-phn-001", "phone", "+8801711560011", "+880 1711-560-011", "Faisal Ahmed", 48, "medium", "brac-bank", "BRAC-only handset flagged on rapid-cashout heuristic"),
        SingleBankEntity("brac-acc-002", "account", "1501023401002", "1501023401002", "Razia Sultana", 41, "medium", "brac-bank", "Dormant-spike on BRAC SME current account"),
        SingleBankEntity("brac-prs-001", "person", "rakibul-hasan-brac", "Rakibul Hasan", "Rakibul Hasan", 35, "low", "brac-bank", "BRAC-only adverse-media subject"),
        # City
        SingleBankEntity("city-acc-001", "account", "2701088802001", "2701088802001", "Mehedi Hasan", 58, "medium", "city-bank", "City Bank fan-in burst on dormant account"),
        SingleBankEntity("city-phn-001", "phone", "+8801711560012", "+880 1711-560-012", "Sharmin Akter", 51, "medium", "city-bank", "City Bank only — high-velocity MFS top-ups"),
        SingleBankEntity("city-acc-002", "account", "2701088802002", "2701088802002", "Imran Khan", 44, "medium", "city-bank", "City Bank first-time high-value triggered"),
        SingleBankEntity("city-prs-001", "person", "nazmul-haque-city", "Nazmul Haque", "Nazmul Haque", 36, "low", "city-bank", "City Bank PEP-adjacent screening hit"),
        # Islami
        SingleBankEntity("ibbl-acc-001", "account", "3201055503001", "3201055503001", "Zahirul Islam", 56, "medium", "islami-bank", "IBBL — structuring on Islamic-banking deposit"),
        SingleBankEntity("ibbl-phn-001", "phone", "+8801711560013", "+880 1711-560-013", "Sabina Yasmin", 49, "medium", "islami-bank", "IBBL — handset flagged on layering"),
        SingleBankEntity("ibbl-acc-002", "account", "3201055503002", "3201055503002", "Aminul Islam", 42, "medium", "islami-bank", "IBBL — proximity to flagged on Mudaraba account"),
        SingleBankEntity("ibbl-acc-003", "account", "3201055503003", "3201055503003", "Munira Begum", 38, "low", "islami-bank", "IBBL — borderline first-time-high-value"),
        SingleBankEntity("ibbl-prs-001", "person", "khaled-mahmud-ibbl", "Khaled Mahmud", "Khaled Mahmud", 33, "low", "islami-bank", "IBBL — adverse-media subject"),
        # Sonali
        SingleBankEntity("sonali-acc-001", "account", "1101011104001", "1101011104001", "Touhidul Alam", 59, "medium", "sonali-bank", "Sonali — fan-out burst on government salary account"),
        SingleBankEntity("sonali-phn-001", "phone", "+8801711560014", "+880 1711-560-014", "Bilkis Begum", 47, "medium", "sonali-bank", "Sonali — handset on rapid-cashout heuristic"),
        SingleBankEntity("sonali-acc-002", "account", "1101011104002", "1101011104002", "Faridul Hoque", 45, "medium", "sonali-bank", "Sonali — dormant-spike on remittance account"),
        SingleBankEntity("sonali-acc-003", "account", "1101011104003", "1101011104003", "Salma Khatun", 39, "low", "sonali-bank", "Sonali — first-time-high-value (just above threshold)"),
        SingleBankEntity("sonali-prs-001", "person", "ashraf-uddin-sonali", "Ashraf Uddin", "Ashraf Uddin", 31, "low", "sonali-bank", "Sonali — adverse-media subject"),
    ]


# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------

def _bank_orgs() -> dict[str, dict[str, str]]:
    """Map bank slug → {id, name, bank_code} for the 5 reporting banks."""
    return {
        seed.slug: {"id": seed.id, "name": seed.name, "bank_code": seed.bank_code or ""}
        for seed in build_organizations()
        if seed.org_type == "bank"
    }


def _channel_for_bank(bank_slug: str, rng: random.Random) -> str:
    """Pick a realistic channel weighted by what each bank actually emphasises."""
    # General Bangladesh banking mix
    pool = ["NPSB", "NPSB", "BEFTN", "BEFTN", "RTGS", "MFS", "CASH", "CHEQUE"]
    if bank_slug == "islami-bank":
        pool = pool + ["LC", "LC"]  # Islami over-indexes on trade finance
    if bank_slug == "sonali-bank":
        pool = pool + ["DRAFT", "BEFTN"]  # Sonali over-indexes on government settlement
    return rng.choice(pool)


def _bdt_amount(severity: str, rng: random.Random) -> float:
    """Realistic BDT amounts by severity. Returns a float number-of-BDT."""
    band = {
        "critical": (4_000_000, 18_000_000),
        "high": (800_000, 4_500_000),
        "medium": (180_000, 950_000),
        "low": (45_000, 180_000),
    }
    lo, hi = band.get(severity, (50_000, 200_000))
    return float(rng.randint(lo, hi))


# -----------------------------------------------------------------------------
# Upsert routines
# -----------------------------------------------------------------------------

async def _upsert_cross_bank_entities(
    session,
    *,
    entities: list[CrossBankEntity],
    banks: dict[str, dict[str, str]],
    now: datetime,
) -> dict[str, UUID]:
    """Returns key → entity UUID."""
    out: dict[str, UUID] = {}
    for entity in entities:
        eid = _stable_uuid("entity", entity.key)
        existing = await session.get(Entity, eid)
        if existing is None:
            existing = Entity(id=eid)
            session.add(existing)

        org_uuids = [UUID(banks[slug]["id"]) for slug in entity.bank_slugs if slug in banks]

        existing.entity_type = entity.entity_type
        existing.canonical_value = entity.canonical_value
        existing.display_value = entity.display_value
        existing.display_name = entity.display_name
        existing.risk_score = entity.risk_score
        existing.severity = entity.severity
        existing.confidence = 0.92
        existing.status = "active"
        existing.source = "synthetic_multi_bank_seed"
        existing.reporting_orgs = org_uuids
        existing.report_count = len(org_uuids)
        existing.first_seen = now - timedelta(days=21)
        existing.last_seen = now - timedelta(hours=4)
        existing.total_exposure = _bdt_amount(entity.severity, random.Random(entity.key)) * len(org_uuids)
        existing.tags = ["cross_bank", "multi_bank_seed"]
        existing.notes = entity.narrative_hook
        existing.metadata_json = {
            "seed_source": "multi_bank_synthetic",
            "topology": f"{len(org_uuids)}-bank",
        }
        out[entity.key] = eid
    await session.flush()
    return out


async def _upsert_single_bank_entities(
    session,
    *,
    entities: list[SingleBankEntity],
    banks: dict[str, dict[str, str]],
    now: datetime,
) -> dict[str, UUID]:
    out: dict[str, UUID] = {}
    for entity in entities:
        eid = _stable_uuid("entity", entity.key)
        existing = await session.get(Entity, eid)
        if existing is None:
            existing = Entity(id=eid)
            session.add(existing)

        org_uuid = UUID(banks[entity.bank_slug]["id"])

        existing.entity_type = entity.entity_type
        existing.canonical_value = entity.canonical_value
        existing.display_value = entity.display_value
        existing.display_name = entity.display_name
        existing.risk_score = entity.risk_score
        existing.severity = entity.severity
        existing.confidence = 0.78
        existing.status = "active"
        existing.source = "synthetic_multi_bank_seed"
        existing.reporting_orgs = [org_uuid]
        existing.report_count = 1
        existing.first_seen = now - timedelta(days=14)
        existing.last_seen = now - timedelta(hours=12)
        existing.total_exposure = _bdt_amount(entity.severity, random.Random(entity.key))
        existing.tags = ["single_bank", "multi_bank_seed"]
        existing.notes = entity.narrative_hook
        existing.metadata_json = {
            "seed_source": "multi_bank_synthetic",
            "topology": "1-bank",
            "bank_slug": entity.bank_slug,
        }
        out[entity.key] = eid
    await session.flush()
    return out


async def _upsert_accounts_and_transactions(
    session,
    *,
    cross_bank_entities: list[CrossBankEntity],
    single_bank_entities: list[SingleBankEntity],
    cross_bank_uuids: dict[str, UUID],
    single_bank_uuids: dict[str, UUID],
    banks: dict[str, dict[str, str]],
    now: datetime,
) -> tuple[int, int]:
    """For each (entity, bank) pair, materialise an Account + a few transactions
    so the modifier-condition graph lookups have something to walk. Skips DBBL —
    DBBL already has its own loader."""
    rng = random.Random(RNG_SEED)
    accounts_created = 0
    txns_created = 0

    pairs: list[tuple[str, str, str, UUID, str, int]] = []  # (entity_key, bank_slug, type, entity_uuid, name, risk)
    for entity in cross_bank_entities:
        for bank_slug in entity.bank_slugs:
            if bank_slug == "dutch-bangla-bank":
                continue  # don't double-up DBBL
            pairs.append((entity.key, bank_slug, entity.entity_type, cross_bank_uuids[entity.key], entity.display_name, entity.risk_score))
    for entity in single_bank_entities:
        pairs.append((entity.key, entity.bank_slug, entity.entity_type, single_bank_uuids[entity.key], entity.display_name, entity.risk_score))

    for entity_key, bank_slug, entity_type, entity_uuid, display_name, risk in pairs:
        org_uuid = UUID(banks[bank_slug]["id"])
        bank_code = banks[bank_slug]["bank_code"]

        acct_key = f"{bank_slug}:{entity_key}"
        acct_uuid = _stable_uuid("account", acct_key)
        acct = await session.get(Account, acct_uuid)
        if acct is None:
            acct = Account(id=acct_uuid)
            session.add(acct)
        acct.org_id = org_uuid
        acct.account_number = str(_stable_uuid("acct-number", acct_key).int)[:13]
        acct.account_name = display_name
        acct.bank_code = bank_code
        acct.account_type = "current"
        acct.risk_tier = "watch" if risk >= 70 else "normal"
        # Critical: the graph-lookup modifiers need entity_id in metadata to fire from scan #2 onward
        acct.metadata_json = {
            "seed_source": "multi_bank_synthetic",
            "entity_id": str(entity_uuid),
            "entity_key": entity_key,
        }
        accounts_created += 1

    await session.flush()

    # Generate ~3-4 transactions per (entity, bank) pair
    base_severity_map = {ent.key: ent.severity for ent in cross_bank_entities}
    base_severity_map.update({ent.key: ent.severity for ent in single_bank_entities})

    for entity_key, bank_slug, _, _, _, risk in pairs:
        org_uuid = UUID(banks[bank_slug]["id"])
        acct_uuid = _stable_uuid("account", f"{bank_slug}:{entity_key}")
        severity = base_severity_map.get(entity_key, "low")

        # Counterparty account inside the same bank for simplicity
        counterparty_uuid = _stable_uuid("account", f"{bank_slug}:{entity_key}:counterparty")
        cp = await session.get(Account, counterparty_uuid)
        if cp is None:
            cp = Account(id=counterparty_uuid)
            session.add(cp)
        cp.org_id = org_uuid
        cp.account_number = str(_stable_uuid("acct-number", f"{bank_slug}:{entity_key}:counterparty").int)[:13]
        cp.account_name = f"Counterparty for {entity_key}"
        cp.bank_code = banks[bank_slug]["bank_code"]
        cp.account_type = "synthetic"
        cp.risk_tier = "watch"
        cp.metadata_json = {"seed_source": "multi_bank_synthetic", "counterparty_for": entity_key}
        accounts_created += 1

        for n in range(rng.randint(3, 4)):
            tx_key = f"{bank_slug}:{entity_key}:{n}"
            tx_uuid = _stable_uuid("transaction", tx_key)
            tx = await session.get(Transaction, tx_uuid)
            if tx is None:
                tx = Transaction(id=tx_uuid)
                session.add(tx)
            tx.org_id = org_uuid
            tx.run_id = None
            tx.posted_at = now - timedelta(days=rng.randint(1, 28), hours=rng.randint(0, 23))
            is_credit = (n % 2 == 0)
            if is_credit:
                tx.src_account_id = counterparty_uuid
                tx.dst_account_id = acct_uuid
            else:
                tx.src_account_id = acct_uuid
                tx.dst_account_id = counterparty_uuid
            tx.amount = _bdt_amount(severity, rng)
            tx.currency = "BDT"
            tx.channel = _channel_for_bank(bank_slug, rng)
            tx.tx_type = "credit" if is_credit else "debit"
            tx.description = f"Synthetic multi-bank seed · {bank_slug} · {entity_key}"
            tx.balance_after = float(rng.randint(100_000, 5_000_000))
            tx.metadata_json = {
                "seed_source": "multi_bank_synthetic",
                "entity_id": str(_stable_uuid("entity", entity_key)),
                "entity_key": entity_key,
            }
            txns_created += 1

    await session.flush()
    return accounts_created, txns_created


async def _upsert_str_reports(
    session,
    *,
    cross_bank_entities: list[CrossBankEntity],
    single_bank_entities: list[SingleBankEntity],
    cross_bank_uuids: dict[str, UUID],
    single_bank_uuids: dict[str, UUID],
    banks: dict[str, dict[str, str]],
    now: datetime,
) -> int:
    """One STR per (entity, bank) pair. Cross-bank entities get cross_bank_hit=True."""
    count = 0

    for entity in cross_bank_entities:
        for bank_slug in entity.bank_slugs:
            org_uuid = UUID(banks[bank_slug]["id"])
            ref = f"STR-{banks[bank_slug]['bank_code']}-{entity.key[:8].upper()}"
            uid = _stable_uuid("str-report", f"{bank_slug}:{entity.key}")
            row = await session.get(STRReport, uid)
            if row is None:
                row = STRReport(id=uid)
                session.add(row)
            row.org_id = org_uuid
            row.report_ref = ref
            row.status = "flagged" if entity.risk_score >= 70 else "submitted"
            row.report_type = "str"
            row.subject_name = entity.display_name
            row.subject_account = entity.canonical_value if entity.entity_type == "account" else (entity.display_value or "—")
            row.subject_bank = banks[bank_slug]["name"]
            row.subject_phone = entity.canonical_value if entity.entity_type == "phone" else None
            row.subject_nid = entity.canonical_value if entity.entity_type == "nid" else None
            row.subject_wallet = None
            row.total_amount = _bdt_amount(entity.severity, random.Random(f"{entity.key}:{bank_slug}"))
            row.currency = "BDT"
            row.transaction_count = 4
            row.primary_channel = _channel_for_bank(bank_slug, random.Random(f"{entity.key}:{bank_slug}:ch"))
            row.channels = ["NPSB", "BEFTN", "MFS"]
            row.category = "money_laundering"
            row.narrative = entity.narrative_hook
            row.auto_risk_score = entity.risk_score
            row.matched_entity_ids = [cross_bank_uuids[entity.key]]
            row.cross_bank_hit = True
            row.metadata_json = {
                "seed_source": "multi_bank_synthetic",
                "topology": f"{len(entity.bank_slugs)}-bank",
                "entity_key": entity.key,
            }
            row.reported_at = now - timedelta(days=random.Random(f"{entity.key}:{bank_slug}:dt").randint(1, 25))
            count += 1

    for entity in single_bank_entities:
        org_uuid = UUID(banks[entity.bank_slug]["id"])
        ref = f"STR-{banks[entity.bank_slug]['bank_code']}-{entity.key[:8].upper()}"
        uid = _stable_uuid("str-report", f"{entity.bank_slug}:{entity.key}")
        row = await session.get(STRReport, uid)
        if row is None:
            row = STRReport(id=uid)
            session.add(row)
        row.org_id = org_uuid
        row.report_ref = ref
        row.status = "submitted"
        row.report_type = "str"
        row.subject_name = entity.display_name
        row.subject_account = entity.canonical_value if entity.entity_type == "account" else (entity.display_value or "—")
        row.subject_bank = banks[entity.bank_slug]["name"]
        row.subject_phone = entity.canonical_value if entity.entity_type == "phone" else None
        row.subject_nid = entity.canonical_value if entity.entity_type == "nid" else None
        row.total_amount = _bdt_amount(entity.severity, random.Random(entity.key))
        row.currency = "BDT"
        row.transaction_count = 3
        row.primary_channel = _channel_for_bank(entity.bank_slug, random.Random(f"{entity.key}:ch"))
        row.channels = ["NPSB", "BEFTN"]
        row.category = "fraud"
        row.narrative = entity.narrative_hook
        row.auto_risk_score = entity.risk_score
        row.matched_entity_ids = [single_bank_uuids[entity.key]]
        row.cross_bank_hit = False
        row.metadata_json = {"seed_source": "multi_bank_synthetic", "topology": "1-bank", "entity_key": entity.key}
        row.reported_at = now - timedelta(days=random.Random(f"{entity.key}:dt").randint(1, 20))
        count += 1

    await session.flush()
    return count


async def _upsert_matches_and_alerts(
    session,
    *,
    cross_bank_entities: list[CrossBankEntity],
    cross_bank_uuids: dict[str, UUID],
    banks: dict[str, dict[str, str]],
    now: datetime,
) -> tuple[int, int]:
    """Insert one Match row per cross-bank entity (the matcher would
    eventually do this from STRs, but inserting directly makes the
    cross-bank dashboard immediately populated). Plus one cross_bank-source
    Alert per Match per involved bank."""
    matches_created = 0
    alerts_created = 0

    for entity in cross_bank_entities:
        match_uuid = _stable_uuid("match", entity.key)
        m = await session.get(Match, match_uuid)
        if m is None:
            m = Match(id=match_uuid)
            session.add(m)
        m.entity_id = cross_bank_uuids[entity.key]
        m.match_key = entity.canonical_value
        m.match_type = entity.entity_type
        m.involved_org_ids = [UUID(banks[slug]["id"]) for slug in entity.bank_slugs if slug in banks]
        m.involved_str_ids = [
            _stable_uuid("str-report", f"{slug}:{entity.key}") for slug in entity.bank_slugs
        ]
        m.match_count = len(entity.bank_slugs)
        m.total_exposure = _bdt_amount(entity.severity, random.Random(entity.key)) * len(entity.bank_slugs)
        m.risk_score = entity.risk_score
        m.severity = entity.severity
        m.status = "investigating"
        m.notes = [{"seed_source": "multi_bank_synthetic"}]
        m.detected_at = now - timedelta(days=random.Random(entity.key).randint(1, 12))
        matches_created += 1

        # One cross_bank alert per involved bank — that's how the audit log
        # shows the alert was raised within each bank's tenant
        for slug in entity.bank_slugs:
            alert_uuid = _stable_uuid("alert", f"crossbank:{entity.key}:{slug}")
            a = await session.get(Alert, alert_uuid)
            if a is None:
                a = Alert(id=alert_uuid)
                session.add(a)
            a.org_id = UUID(banks[slug]["id"])
            a.source_type = "cross_bank"
            a.source_id = match_uuid
            a.entity_id = cross_bank_uuids[entity.key]
            a.title = f"Cross-bank match: {entity.display_name}"
            a.description = entity.narrative_hook
            a.alert_type = "cross_bank_match"
            a.risk_score = entity.risk_score
            a.severity = entity.severity
            a.status = "open"
            a.reasons = [{"rule": "cross_bank_match", "score": entity.risk_score, "reason_text": f"Reported by {len(entity.bank_slugs)} institutions"}]
            alerts_created += 1

    await session.flush()
    return matches_created, alerts_created


# -----------------------------------------------------------------------------
# Entry points
# -----------------------------------------------------------------------------

def build_load_plan() -> dict[str, object]:
    cross = _cross_bank_entities()
    single = _single_bank_entities()
    bank_pair_count = sum(len(e.bank_slugs) for e in cross) + len(single)
    return {
        "cross_bank_entities": len(cross),
        "single_bank_entities": len(single),
        "entity_bank_pairs": bank_pair_count,
        "expected_str_reports": bank_pair_count,
        "expected_matches": len(cross),
        "expected_alerts": sum(len(e.bank_slugs) for e in cross),
        "topology": {
            "5_bank": sum(1 for e in cross if len(e.bank_slugs) == 5),
            "3_bank": sum(1 for e in cross if len(e.bank_slugs) == 3),
            "2_bank": sum(1 for e in cross if len(e.bank_slugs) == 2),
        },
    }


async def apply() -> dict[str, object]:
    cross = _cross_bank_entities()
    single = _single_bank_entities()
    banks = _bank_orgs()
    now = datetime.now(tz=UTC)

    async with SessionLocal() as session:
        cross_uuids = await _upsert_cross_bank_entities(session, entities=cross, banks=banks, now=now)
        single_uuids = await _upsert_single_bank_entities(session, entities=single, banks=banks, now=now)
        accts, txns = await _upsert_accounts_and_transactions(
            session,
            cross_bank_entities=cross,
            single_bank_entities=single,
            cross_bank_uuids=cross_uuids,
            single_bank_uuids=single_uuids,
            banks=banks,
            now=now,
        )
        strs = await _upsert_str_reports(
            session,
            cross_bank_entities=cross,
            single_bank_entities=single,
            cross_bank_uuids=cross_uuids,
            single_bank_uuids=single_uuids,
            banks=banks,
            now=now,
        )
        matches, alerts = await _upsert_matches_and_alerts(
            session,
            cross_bank_entities=cross,
            cross_bank_uuids=cross_uuids,
            banks=banks,
            now=now,
        )
        await session.commit()

    return {
        "cross_bank_entities": len(cross_uuids),
        "single_bank_entities": len(single_uuids),
        "accounts": accts,
        "transactions": txns,
        "str_reports": strs,
        "matches": matches,
        "alerts": alerts,
        "applied_at": now.isoformat(),
    }


def _database_target_hint() -> dict[str, object]:
    parsed = urlparse(get_settings().database_url.replace("+asyncpg", ""))
    return {"host": parsed.hostname, "port": parsed.port, "database": parsed.path.lstrip("/")}


def main() -> None:
    parser = argparse.ArgumentParser(description="Apply the multi-bank cross-bank synthetic seed.")
    parser.add_argument("--apply", action="store_true", help="Actually write rows. Without this, prints the load plan only.")
    args = parser.parse_args()

    if not args.apply:
        print(json.dumps(build_load_plan(), indent=2))
        return

    try:
        result = asyncio.run(apply())
    except (ConnectionRefusedError, OSError, SQLAlchemyError) as exc:
        target = _database_target_hint()
        raise SystemExit(
            "Cannot connect to the configured database. "
            f"Target: host={target['host']} port={target['port']} database={target['database']}. "
            "Set DATABASE_URL and rerun `python -m seed.multi_bank_synthetic --apply`."
        ) from exc
    print(json.dumps(result, indent=2, default=str))


if __name__ == "__main__":
    main()
