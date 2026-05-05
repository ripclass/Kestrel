"""Per-tenant demo seed for newly-signed-up bank workspaces (V2 phase 2.3).

Picks up `organizations.settings.demo_seed_pending = true` rows (set by the
bank-direct signup action in `web/src/app/actions/bank-signup.ts`) and seeds
each tenant with a realistic, idempotent dataset so the new CAMLCO lands
on a populated bank dashboard:

* ~25 entities (4 cross-bank flagged + 21 single-bank)
* ~30 internal accounts
* ~10,000 synthetic transactions over 180 days with a Bangladesh-tuned
  channel mix (40% NPSB / 25% BEFTN / 15% RTGS / 15% MFS / 5% cash+cheque)
* 12 alerts spanning critical / high / medium severity
* 3 STRs at different lifecycle stages (draft / flagged / submitted)
* 5 cases (2 standard / 1 proposal / 2 RFI)
* 4 cross-bank Match rows linking the new tenant to BRAC / City / Islami /
  Sonali so /intelligence/cross-bank lights up immediately

Idempotent: deterministic UUIDs derived from the new tenant's org_id, so
re-runs upsert in place. After successful apply, sets
`settings.demo_seed_pending=false` and records counts under
`settings.demo_seed_counts`.

Invocation:
    python -m seed.load_demo_bank                          # plan only
    python -m seed.load_demo_bank --org-id <uuid> --apply  # one tenant
    python -m seed.load_demo_bank --apply-pending          # all pending tenants
    python -m seed.load_demo_bank --apply-pending --scale 0.2  # ~2k txns each (dev)
"""
from __future__ import annotations

import argparse
import asyncio
import json
import logging
import random
from datetime import UTC, datetime, timedelta
from typing import Iterable
from urllib.parse import urlparse
from uuid import UUID, uuid4, uuid5

from sqlalchemy import select, text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database import SessionLocal
from app.models.account import Account
from app.models.alert import Alert
from app.models.case import Case
from app.models.entity import Entity
from app.models.match import Match
from app.models.org import Organization
from app.models.str_report import STRReport
from app.models.transaction import Transaction
from seed.organizations import build_organizations

logger = logging.getLogger("kestrel.seed.demo_bank")

# Shared NAMESPACE with dbbl + multi_bank loaders so any future cross-cutting
# helpers can derive consistent UUIDs.
NAMESPACE = UUID("8d393384-a67a-4b64-bf0b-7b66b8d5da76")

DEFAULT_TARGET_TRANSACTIONS = 10_000
DEFAULT_SEED_DAYS = 180
DEFAULT_BULK_INSERT_CHUNK = 500


# -----------------------------------------------------------------------------
# Deterministic UUID derivation per tenant
# -----------------------------------------------------------------------------

def _tenant_uuid(org_id: UUID, kind: str, value: str) -> UUID:
    return uuid5(NAMESPACE, f"demo-bank:{org_id}:{kind}:{value}")


def _peer_bank_orgs() -> dict[str, UUID]:
    """Slug → UUID for the four banks the new tenant overlaps with on the
    cross-bank dashboard. DBBL is omitted because DBBL has its own real
    fixture; we want the new tenant's "cross-bank context" to span peers."""
    out: dict[str, UUID] = {}
    for seed in build_organizations():
        if seed.slug in {"brac-bank", "city-bank", "islami-bank", "sonali-bank"}:
            out[seed.slug] = UUID(seed.id)
    return out


# -----------------------------------------------------------------------------
# Subject definitions
# -----------------------------------------------------------------------------

# 4 cross-bank flagged subjects. Each lists which peer bank also reports them.
CROSS_BANK_SUBJECTS: list[dict] = [
    {
        "key": "xb-mohammad-karim-phone",
        "entity_type": "phone",
        "value_template": "+8801712{tenant}001",
        "display_name": "Mohammad Karim",
        "risk_score": 92,
        "severity": "critical",
        "peers": ["brac-bank", "city-bank", "islami-bank"],
        "narrative": "Phone surfaces on STRs across BRAC, City, and Islami within a 30-day window with high-velocity NPSB cashouts.",
    },
    {
        "key": "xb-rashedul-alam-nid",
        "entity_type": "nid",
        "value_template": "199012{tenant}5601",
        "display_name": "Rashedul Alam",
        "risk_score": 81,
        "severity": "high",
        "peers": ["brac-bank", "sonali-bank"],
        "narrative": "Identical NID linked to structuring activity at BRAC and Sonali. Counterparty pattern matches mule typology.",
    },
    {
        "key": "xb-asma-begum-account",
        "entity_type": "account",
        "value_template": "5005{tenant}001202",
        "display_name": "Asma Begum",
        "risk_score": 74,
        "severity": "high",
        "peers": ["city-bank"],
        "narrative": "Counterparty account presents structuring breaks across two scheduled banks; thresholds tuned just under reportable limits.",
    },
    {
        "key": "xb-tanvir-hossain-phone",
        "entity_type": "phone",
        "value_template": "+8801712{tenant}004",
        "display_name": "Tanvir Hossain",
        "risk_score": 65,
        "severity": "medium",
        "peers": ["islami-bank"],
        "narrative": "Phone bridges fund movement between Islamic-banking deposit and counterparty via MFS top-up.",
    },
]

# 21 single-bank subjects. Mix of person/account/phone/business types.
# Risk scores tuned so the 12 alerts have the right severity distribution.
SINGLE_BANK_SUBJECTS: list[dict] = [
    # 3 critical (>=90)
    {"key": "sb-crit-01", "type": "account", "name": "Faridul Hoque (rapid cashout)", "value": "1010001", "risk": 91, "severity": "critical"},
    {"key": "sb-crit-02", "type": "phone",   "name": "Mahbub Rahman",                  "value": "+8801712000010", "risk": 90, "severity": "critical"},
    {"key": "sb-crit-03", "type": "account", "name": "Tahmina Sultana (fan-in)",       "value": "1010002", "risk": 92, "severity": "critical"},
    # 5 high (>=70)
    {"key": "sb-high-01", "type": "account", "name": "Ruhul Amin",                     "value": "1010003", "risk": 78, "severity": "high"},
    {"key": "sb-high-02", "type": "phone",   "name": "Nasrin Akhtar",                  "value": "+8801712000011", "risk": 76, "severity": "high"},
    {"key": "sb-high-03", "type": "account", "name": "Anwar Hossain (layering)",       "value": "1010004", "risk": 73, "severity": "high"},
    {"key": "sb-high-04", "type": "nid",     "name": "Shamima Nasreen",                "value": "199001234560001", "risk": 71, "severity": "high"},
    {"key": "sb-high-05", "type": "account", "name": "Khondoker Enterprise",           "value": "1010005", "risk": 70, "severity": "high"},
    # 4 medium (>=50)
    {"key": "sb-med-01",  "type": "account", "name": "Salma Khatun",                   "value": "1010006", "risk": 64, "severity": "medium"},
    {"key": "sb-med-02",  "type": "phone",   "name": "Bilkis Begum",                   "value": "+8801712000012", "risk": 60, "severity": "medium"},
    {"key": "sb-med-03",  "type": "account", "name": "Imran Khan (dormant spike)",     "value": "1010007", "risk": 58, "severity": "medium"},
    {"key": "sb-med-04",  "type": "account", "name": "Lutful Kabir",                   "value": "1010008", "risk": 54, "severity": "medium"},
    # 9 normal (low risk, no alerts)
    {"key": "sb-norm-01", "type": "account", "name": "Abdul Karim",                    "value": "1010009", "risk": 38, "severity": "low"},
    {"key": "sb-norm-02", "type": "account", "name": "Moushumi Akhter",                "value": "1010010", "risk": 35, "severity": "low"},
    {"key": "sb-norm-03", "type": "account", "name": "Sajjad Hossain",                 "value": "1010011", "risk": 32, "severity": "low"},
    {"key": "sb-norm-04", "type": "account", "name": "Rina Begum Trading",             "value": "1010012", "risk": 30, "severity": "low"},
    {"key": "sb-norm-05", "type": "account", "name": "Rezaul Karim",                   "value": "1010013", "risk": 28, "severity": "low"},
    {"key": "sb-norm-06", "type": "account", "name": "Mostafizur Rahman",              "value": "1010014", "risk": 26, "severity": "low"},
    {"key": "sb-norm-07", "type": "account", "name": "Sumon Trading House",            "value": "1010015", "risk": 24, "severity": "low"},
    {"key": "sb-norm-08", "type": "account", "name": "Nurul Huda",                     "value": "1010016", "risk": 22, "severity": "low"},
    {"key": "sb-norm-09", "type": "account", "name": "Halima Khatun",                  "value": "1010017", "risk": 20, "severity": "low"},
]

# Channel mix — must sum to 100. Roughly the V2 spec.
CHANNEL_MIX: list[tuple[str, int]] = [
    ("NPSB", 40),
    ("BEFTN", 25),
    ("RTGS", 15),
    ("MFS_BKASH", 10),
    ("MFS_NAGAD", 3),
    ("MFS_ROCKET", 2),
    ("CASH", 3),
    ("CHEQUE", 2),
]

CASE_VARIANTS: list[str] = ["standard", "standard", "proposal", "rfi", "rfi"]

STR_LIFECYCLE: list[tuple[str, str]] = [
    # (status, report_type)
    ("draft", "str"),
    ("flagged", "str"),
    ("submitted", "str"),
]


# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------

def _tenant_short(org_id: UUID) -> str:
    """Stable 6-digit derivation from org_id to keep generated phone/account
    values unique per tenant without growing the string."""
    h = uuid5(NAMESPACE, f"demo-bank-short:{org_id}").int
    return f"{h % 1_000_000:06d}"


def _populate_value(template: str, tenant_short: str) -> str:
    """The cross-bank subject canonical_value templates embed `{tenant}` so
    each new tenant gets a unique value but with the same shape."""
    return template.format(tenant=tenant_short[:3])


def _channel_choice(rng: random.Random) -> str:
    pool: list[str] = []
    for ch, weight in CHANNEL_MIX:
        pool.extend([ch] * weight)
    return rng.choice(pool)


def _amount_for(severity: str, rng: random.Random) -> float:
    band = {
        "critical": (4_000_000, 18_000_000),
        "high":     (800_000, 4_500_000),
        "medium":   (180_000, 950_000),
        "low":      (8_000, 180_000),
    }[severity]
    return float(rng.randint(*band))


# -----------------------------------------------------------------------------
# Upsert routines
# -----------------------------------------------------------------------------

async def _upsert_entities(
    session: AsyncSession,
    *,
    org_id: UUID,
    peer_orgs: dict[str, UUID],
    now: datetime,
) -> tuple[dict[str, UUID], dict[str, UUID]]:
    """Returns (cross_bank_uuids, single_bank_uuids), keyed by subject 'key'."""
    tenant_short = _tenant_short(org_id)
    cross_uuids: dict[str, UUID] = {}
    single_uuids: dict[str, UUID] = {}

    # Cross-bank entities — reporting_orgs spans the new tenant + peer banks
    for subject in CROSS_BANK_SUBJECTS:
        eid = _tenant_uuid(org_id, "entity", subject["key"])
        existing = await session.get(Entity, eid)
        if existing is None:
            existing = Entity(id=eid)
            session.add(existing)

        peer_uuids = [peer_orgs[slug] for slug in subject["peers"] if slug in peer_orgs]
        canonical = _populate_value(subject["value_template"], tenant_short)
        existing.entity_type = subject["entity_type"]
        existing.canonical_value = canonical
        existing.display_value = canonical
        existing.display_name = subject["display_name"]
        existing.risk_score = subject["risk_score"]
        existing.severity = subject["severity"]
        existing.confidence = 0.88
        existing.status = "active"
        existing.source = "synthetic_demo_bank_seed"
        existing.reporting_orgs = [org_id, *peer_uuids]
        existing.report_count = 1 + len(peer_uuids)
        existing.first_seen = now - timedelta(days=21)
        existing.last_seen = now - timedelta(hours=4)
        existing.total_exposure = _amount_for(subject["severity"], random.Random(subject["key"])) * (1 + len(peer_uuids))
        existing.tags = ["cross_bank", "demo_bank_seed"]
        existing.notes = subject["narrative"]
        existing.metadata_json = {
            "seed_source": "demo_bank",
            "tenant_org_id": str(org_id),
            "topology": f"{1 + len(peer_uuids)}-bank",
        }
        cross_uuids[subject["key"]] = eid

    # Single-bank entities
    for subject in SINGLE_BANK_SUBJECTS:
        eid = _tenant_uuid(org_id, "entity", subject["key"])
        existing = await session.get(Entity, eid)
        if existing is None:
            existing = Entity(id=eid)
            session.add(existing)

        existing.entity_type = subject["type"]
        # Per-tenant uniqueness: replace the trailing characters with the full
        # 6-char tenant short so two tenants never collide on the
        # (entity_type, canonical_value) UNIQUE constraint.
        if subject["type"] == "account":
            canonical = f"{tenant_short}-{subject['value']}"
        else:
            canonical = subject["value"][:-6] + tenant_short
        existing.canonical_value = canonical
        existing.display_value = canonical
        existing.display_name = subject["name"]
        existing.risk_score = subject["risk"]
        existing.severity = subject["severity"]
        existing.confidence = 0.78
        existing.status = "active"
        existing.source = "synthetic_demo_bank_seed"
        existing.reporting_orgs = [org_id]
        existing.report_count = 1
        existing.first_seen = now - timedelta(days=14)
        existing.last_seen = now - timedelta(hours=12)
        existing.total_exposure = _amount_for(subject["severity"], random.Random(subject["key"]))
        existing.tags = ["single_bank", "demo_bank_seed"]
        existing.notes = f"Synthetic single-bank subject for tenant demo seed"
        existing.metadata_json = {
            "seed_source": "demo_bank",
            "tenant_org_id": str(org_id),
            "topology": "1-bank",
        }
        single_uuids[subject["key"]] = eid

    await session.flush()
    return cross_uuids, single_uuids


async def _upsert_accounts(
    session: AsyncSession,
    *,
    org_id: UUID,
    bank_code: str,
    cross_subjects: Iterable[dict],
    single_subjects: Iterable[dict],
    cross_uuids: dict[str, UUID],
    single_uuids: dict[str, UUID],
) -> tuple[dict[str, UUID], list[UUID]]:
    """Returns (subject_key → primary_account_uuid, list_of_counterparty_account_uuids).
    One main account per subject + one shared pool of counterparty accounts."""
    primary: dict[str, UUID] = {}
    tenant_short = _tenant_short(org_id)

    for subject in cross_subjects:
        acct_uuid = _tenant_uuid(org_id, "account", f"primary:{subject['key']}")
        existing = await session.get(Account, acct_uuid)
        if existing is None:
            existing = Account(id=acct_uuid)
            session.add(existing)
        existing.org_id = org_id
        existing.account_number = str(_tenant_uuid(org_id, "acct-num", subject["key"]).int)[:13]
        existing.account_name = subject["display_name"]
        existing.bank_code = bank_code
        existing.account_type = "current"
        existing.risk_tier = "watch"
        existing.metadata_json = {
            "seed_source": "demo_bank",
            "entity_id": str(cross_uuids[subject["key"]]),
            "subject_key": subject["key"],
            "topology": "cross_bank",
        }
        primary[subject["key"]] = acct_uuid

    for subject in single_subjects:
        acct_uuid = _tenant_uuid(org_id, "account", f"primary:{subject['key']}")
        existing = await session.get(Account, acct_uuid)
        if existing is None:
            existing = Account(id=acct_uuid)
            session.add(existing)
        existing.org_id = org_id
        existing.account_number = str(_tenant_uuid(org_id, "acct-num", subject["key"]).int)[:13]
        existing.account_name = subject["name"]
        existing.bank_code = bank_code
        risk = subject["risk"]
        existing.risk_tier = "watch" if risk >= 70 else "normal"
        existing.account_type = "current" if subject["type"] != "person" else "savings"
        existing.metadata_json = {
            "seed_source": "demo_bank",
            "entity_id": str(single_uuids[subject["key"]]),
            "subject_key": subject["key"],
            "topology": "single_bank",
        }
        primary[subject["key"]] = acct_uuid

    # Shared counterparty pool — 8 internal counterparty accounts that
    # transactions cycle through. Realistic for an SME-heavy bank.
    counterparties: list[UUID] = []
    for n in range(8):
        acct_uuid = _tenant_uuid(org_id, "account", f"counterparty:{n:02d}")
        existing = await session.get(Account, acct_uuid)
        if existing is None:
            existing = Account(id=acct_uuid)
            session.add(existing)
        existing.org_id = org_id
        existing.account_number = str(_tenant_uuid(org_id, "acct-num-cp", f"cp{n}").int)[:13]
        existing.account_name = f"Counterparty pool {n + 1}"
        existing.bank_code = bank_code
        existing.account_type = "synthetic"
        existing.risk_tier = "normal"
        existing.metadata_json = {"seed_source": "demo_bank", "kind": "counterparty"}
        counterparties.append(acct_uuid)

    await session.flush()
    return primary, counterparties


async def _bulk_insert_transactions(
    session: AsyncSession,
    *,
    org_id: UUID,
    primary_accounts: dict[str, UUID],
    counterparties: list[UUID],
    cross_uuids: dict[str, UUID],
    single_uuids: dict[str, UUID],
    target_count: int,
    seed_days: int,
    rng: random.Random,
) -> int:
    """Bulk-insert ~target_count transactions over the trailing seed_days window.
    Uses ON CONFLICT DO NOTHING so re-runs are idempotent per (deterministic) UUID."""
    now = datetime.now(UTC)
    earliest = now - timedelta(days=seed_days)

    # Compose subject pool with weighted txn-volume per severity. Higher-risk
    # subjects get more transactions; that's where the alerts come from.
    weight_map = {"critical": 80, "high": 60, "medium": 40, "low": 18}
    subject_pool: list[tuple[str, str, UUID]] = []  # (subject_key, severity, entity_uuid)
    for s in CROSS_BANK_SUBJECTS:
        subject_pool.extend([(s["key"], s["severity"], cross_uuids[s["key"]])] * weight_map[s["severity"]])
    for s in SINGLE_BANK_SUBJECTS:
        subject_pool.extend([(s["key"], s["severity"], single_uuids[s["key"]])] * weight_map[s["severity"]])

    rows: list[dict] = []
    for n in range(target_count):
        subject_key, severity, entity_uuid = rng.choice(subject_pool)
        primary_uuid = primary_accounts[subject_key]
        cp_uuid = rng.choice(counterparties)
        is_credit = rng.random() < 0.55  # 55% credits, 45% debits

        # Spread time-of-day so behavior looks human
        delta_seconds = rng.randint(0, seed_days * 86_400)
        posted_at = earliest + timedelta(seconds=delta_seconds)

        tx_uuid = _tenant_uuid(org_id, "transaction", f"{subject_key}:{n}")
        rows.append({
            "id": tx_uuid,
            "org_id": org_id,
            "run_id": None,
            "posted_at": posted_at,
            "src_account_id": cp_uuid if is_credit else primary_uuid,
            "dst_account_id": primary_uuid if is_credit else cp_uuid,
            "amount": _amount_for(severity, rng),
            "currency": "BDT",
            "channel": _channel_choice(rng),
            "tx_type": "credit" if is_credit else "debit",
            "description": f"Synthetic demo · {subject_key}",
            "balance_after": float(rng.randint(50_000, 8_000_000)),
            "metadata": {
                "seed_source": "demo_bank",
                "entity_id": str(entity_uuid),
                "subject_key": subject_key,
            },
        })

    inserted = 0
    for i in range(0, len(rows), DEFAULT_BULK_INSERT_CHUNK):
        chunk = rows[i:i + DEFAULT_BULK_INSERT_CHUNK]
        stmt = pg_insert(Transaction).values(chunk).on_conflict_do_nothing(index_elements=["id"])
        result = await session.execute(stmt)
        inserted += (result.rowcount or 0)

    await session.flush()
    return inserted


async def _upsert_str_reports(
    session: AsyncSession,
    *,
    org_id: UUID,
    bank_code: str,
    bank_name: str,
    cross_uuids: dict[str, UUID],
    now: datetime,
) -> dict[str, UUID]:
    """3 STRs at different lifecycle stages, each linked to one of the
    top-3 cross-bank subjects."""
    out: dict[str, UUID] = {}
    # Use first 3 cross-bank subjects (highest risk first)
    tenant_short = _tenant_short(org_id)
    for (status, report_type), subject in zip(STR_LIFECYCLE, CROSS_BANK_SUBJECTS[:3]):
        ref = f"STR-{bank_code}-{tenant_short[:4]}-{subject['key'][-4:].upper()}"
        sid = _tenant_uuid(org_id, "str-report", f"{status}:{subject['key']}")
        row = await session.get(STRReport, sid)
        if row is None:
            row = STRReport(id=sid)
            session.add(row)
        row.org_id = org_id
        row.report_ref = ref
        row.report_type = report_type
        row.status = status
        row.subject_name = subject["display_name"]
        canonical = _populate_value(subject["value_template"], tenant_short)
        row.subject_account = canonical if subject["entity_type"] == "account" else canonical
        row.subject_bank = bank_name
        row.subject_phone = canonical if subject["entity_type"] == "phone" else None
        row.subject_nid = canonical if subject["entity_type"] == "nid" else None
        row.subject_wallet = None
        row.total_amount = _amount_for(subject["severity"], random.Random(f"str:{subject['key']}"))
        row.currency = "BDT"
        row.transaction_count = random.Random(f"str-tx:{subject['key']}").randint(8, 25)
        row.primary_channel = "NPSB"
        row.channels = ["NPSB", "BEFTN", "MFS_BKASH"]
        row.category = "money_laundering"
        row.narrative = subject["narrative"]
        row.auto_risk_score = subject["risk_score"]
        row.matched_entity_ids = [cross_uuids[subject["key"]]]
        row.cross_bank_hit = True
        row.metadata_json = {
            "seed_source": "demo_bank",
            "tenant_org_id": str(org_id),
            "subject_key": subject["key"],
        }
        # Stagger reported_at so the STR list isn't all the same day
        days_ago = {"draft": 1, "flagged": 4, "submitted": 12}[status]
        row.reported_at = now - timedelta(days=days_ago, hours=random.Random(f"str-h:{subject['key']}").randint(0, 23))
        row.date_range_start = (row.reported_at - timedelta(days=21)).date()
        row.date_range_end = row.reported_at.date()
        out[status] = sid

    await session.flush()
    return out


async def _upsert_alerts(
    session: AsyncSession,
    *,
    org_id: UUID,
    cross_uuids: dict[str, UUID],
    single_uuids: dict[str, UUID],
    now: datetime,
) -> list[UUID]:
    """12 alerts: 3 critical + 5 high + 4 medium. Highest-risk subjects get
    alerts attributed to them so the dashboard immediately surfaces risk."""
    alert_ids: list[UUID] = []

    # 3 critical — pulled from cross-bank top-2 + single-bank crit-01
    critical_targets: list[tuple[str, str, UUID, int]] = [
        ("xb-mohammad-karim-phone", "critical", cross_uuids["xb-mohammad-karim-phone"], 92),
        ("xb-rashedul-alam-nid", "critical", cross_uuids["xb-rashedul-alam-nid"], 90),
        ("sb-crit-01", "critical", single_uuids["sb-crit-01"], 91),
    ]
    # 5 high
    high_targets: list[tuple[str, str, UUID, int]] = [
        ("xb-asma-begum-account", "high", cross_uuids["xb-asma-begum-account"], 74),
        ("sb-crit-02", "high", single_uuids["sb-crit-02"], 86),
        ("sb-crit-03", "high", single_uuids["sb-crit-03"], 82),
        ("sb-high-01", "high", single_uuids["sb-high-01"], 78),
        ("sb-high-02", "high", single_uuids["sb-high-02"], 76),
    ]
    # 4 medium
    medium_targets: list[tuple[str, str, UUID, int]] = [
        ("xb-tanvir-hossain-phone", "medium", cross_uuids["xb-tanvir-hossain-phone"], 65),
        ("sb-high-03", "medium", single_uuids["sb-high-03"], 68),
        ("sb-med-01", "medium", single_uuids["sb-med-01"], 64),
        ("sb-med-03", "medium", single_uuids["sb-med-03"], 58),
    ]

    rule_pool = ["rapid_cashout", "structuring", "fan_in_burst", "first_time_high_value", "dormant_spike", "layering", "proximity_to_bad", "fan_out_burst"]

    for subject_key, severity, entity_uuid, risk in critical_targets + high_targets + medium_targets:
        alert_uuid = _tenant_uuid(org_id, "alert", f"{severity}:{subject_key}")
        existing = await session.get(Alert, alert_uuid)
        if existing is None:
            existing = Alert(id=alert_uuid)
            session.add(existing)
        existing.org_id = org_id
        existing.source_type = "scan"
        existing.source_id = None
        existing.entity_id = entity_uuid
        existing.title = f"{subject_key.replace('-', ' ').title()} pattern alert"
        existing.description = f"Synthetic demo alert raised on subject_key={subject_key} during seed."
        existing.alert_type = "pattern_scan"
        existing.risk_score = risk
        existing.severity = severity
        existing.status = "open"
        existing.reasons = [
            {"rule": rule_pool[hash(subject_key) % len(rule_pool)], "score": risk, "reason_text": f"Demo seed reason for {subject_key}"},
        ]
        existing.assigned_to = None
        existing.case_id = None
        existing.resolved_by = None
        existing.resolved_at = None
        alert_ids.append(alert_uuid)

    await session.flush()
    return alert_ids


async def _upsert_matches(
    session: AsyncSession,
    *,
    org_id: UUID,
    peer_orgs: dict[str, UUID],
    cross_uuids: dict[str, UUID],
    str_lookup: dict[str, UUID],
    now: datetime,
) -> int:
    """One Match row per cross-bank subject. involved_org_ids spans the
    new tenant + the peer banks listed on each subject."""
    count = 0
    for subject in CROSS_BANK_SUBJECTS:
        match_uuid = _tenant_uuid(org_id, "match", subject["key"])
        existing = await session.get(Match, match_uuid)
        if existing is None:
            existing = Match(id=match_uuid)
            session.add(existing)
        existing.entity_id = cross_uuids[subject["key"]]
        existing.match_key = _populate_value(subject["value_template"], _tenant_short(org_id))
        existing.match_type = subject["entity_type"]
        peer_uuids = [peer_orgs[slug] for slug in subject["peers"] if slug in peer_orgs]
        existing.involved_org_ids = [org_id, *peer_uuids]
        # Link to the new tenant's STRs where applicable (only the top-3 subjects have STRs)
        existing.involved_str_ids = [sid for sid in str_lookup.values()] if subject["key"] in {s["key"] for s in CROSS_BANK_SUBJECTS[:3]} else []
        existing.match_count = 1 + len(peer_uuids)
        existing.total_exposure = _amount_for(subject["severity"], random.Random(f"match:{subject['key']}")) * existing.match_count
        existing.risk_score = subject["risk_score"]
        existing.severity = subject["severity"]
        existing.status = "investigating"
        existing.notes = [{"seed_source": "demo_bank", "tenant_org_id": str(org_id)}]
        existing.detected_at = now - timedelta(days=random.Random(f"match-d:{subject['key']}").randint(1, 12))
        count += 1
    await session.flush()
    return count


async def _upsert_cases(
    session: AsyncSession,
    *,
    org_id: UUID,
    cross_uuids: dict[str, UUID],
    single_uuids: dict[str, UUID],
    alert_ids: list[UUID],
    now: datetime,
) -> int:
    """5 cases: variant distribution 2 standard / 1 proposal / 2 RFI."""
    # Pick 5 highest-risk subjects to attach cases to
    case_subjects = [
        ("xb-mohammad-karim-phone", "critical", cross_uuids["xb-mohammad-karim-phone"], "fraud"),
        ("sb-crit-01", "critical", single_uuids["sb-crit-01"], "fraud"),
        ("xb-rashedul-alam-nid", "high", cross_uuids["xb-rashedul-alam-nid"], "money_laundering"),
        ("sb-crit-03", "high", single_uuids["sb-crit-03"], "fraud"),
        ("xb-asma-begum-account", "high", cross_uuids["xb-asma-begum-account"], "money_laundering"),
    ]

    tenant_short = _tenant_short(org_id)
    count = 0
    for index, ((subject_key, severity, entity_uuid, category), variant) in enumerate(zip(case_subjects, CASE_VARIANTS)):
        case_uuid = _tenant_uuid(org_id, "case", f"{variant}:{subject_key}")
        existing = await session.get(Case, case_uuid)
        if existing is None:
            existing = Case(id=case_uuid)
            session.add(existing)
        existing.org_id = org_id
        existing.case_ref = f"KST-DEMO-{tenant_short[:4]}-{subject_key[-4:].upper()}"
        existing.title = f"{variant.upper()} · investigation on {subject_key}"
        existing.summary = f"Synthetic {variant} case from demo seed for tenant {tenant_short}."
        existing.category = category
        existing.severity = severity
        existing.status = "investigating"
        existing.assigned_to = None
        existing.linked_alert_ids = [alert_ids[index]] if index < len(alert_ids) else []
        existing.linked_entity_ids = [entity_uuid]
        existing.total_exposure = _amount_for(severity, random.Random(f"case:{subject_key}"))
        existing.recovered = 0.0
        existing.timeline = [
            {
                "type": "note",
                "timestamp": now.isoformat(),
                "content": f"Synthetic {variant} case opened from demo seed.",
            }
        ]
        existing.tags = ["demo_bank_seed", variant]
        existing.due_date = (now + timedelta(days=14)).date() if variant in ("rfi", "proposal") else None
        existing.closed_at = None
        existing.variant = variant
        count += 1

    await session.flush()
    return count


# -----------------------------------------------------------------------------
# Org-level orchestration
# -----------------------------------------------------------------------------

async def _resolve_bank(session: AsyncSession, org_id: UUID) -> Organization:
    org = await session.get(Organization, org_id)
    if org is None:
        raise ValueError(f"organization {org_id} does not exist")
    if org.org_type != "bank":
        raise ValueError(f"organization {org_id} is not a bank (org_type={org.org_type})")
    return org


def _bank_code_for(org: Organization) -> str:
    if org.bank_code:
        return org.bank_code
    # Self-serve signups don't set bank_code; derive a stable 6-char code from the slug
    base = "".join(c for c in (org.slug or org.name).upper() if c.isalnum())
    return (base[:6] or "DEMO")


async def apply_for_org(
    session: AsyncSession,
    org_id: UUID,
    *,
    scale: float = 1.0,
    rng_seed: int | None = None,
) -> dict[str, object]:
    """Idempotent demo seed for one bank tenant."""
    org = await _resolve_bank(session, org_id)
    bank_code = _bank_code_for(org)
    bank_name = org.name
    peer_orgs = _peer_bank_orgs()
    now = datetime.now(UTC)
    rng = random.Random(rng_seed if rng_seed is not None else int(uuid5(NAMESPACE, f"demo-bank-rng:{org_id}").int % (2**31)))

    cross_uuids, single_uuids = await _upsert_entities(session, org_id=org_id, peer_orgs=peer_orgs, now=now)
    primary_accounts, counterparties = await _upsert_accounts(
        session,
        org_id=org_id,
        bank_code=bank_code,
        cross_subjects=CROSS_BANK_SUBJECTS,
        single_subjects=SINGLE_BANK_SUBJECTS,
        cross_uuids=cross_uuids,
        single_uuids=single_uuids,
    )

    target_txns = max(int(DEFAULT_TARGET_TRANSACTIONS * scale), 100)
    txn_count = await _bulk_insert_transactions(
        session,
        org_id=org_id,
        primary_accounts=primary_accounts,
        counterparties=counterparties,
        cross_uuids=cross_uuids,
        single_uuids=single_uuids,
        target_count=target_txns,
        seed_days=DEFAULT_SEED_DAYS,
        rng=rng,
    )

    str_lookup = await _upsert_str_reports(
        session, org_id=org_id, bank_code=bank_code, bank_name=bank_name,
        cross_uuids=cross_uuids, now=now,
    )
    alert_ids = await _upsert_alerts(
        session, org_id=org_id, cross_uuids=cross_uuids, single_uuids=single_uuids, now=now,
    )
    match_count = await _upsert_matches(
        session, org_id=org_id, peer_orgs=peer_orgs, cross_uuids=cross_uuids,
        str_lookup=str_lookup, now=now,
    )
    case_count = await _upsert_cases(
        session, org_id=org_id, cross_uuids=cross_uuids, single_uuids=single_uuids,
        alert_ids=alert_ids, now=now,
    )

    counts = {
        "entities": len(cross_uuids) + len(single_uuids),
        "cross_bank_entities": len(cross_uuids),
        "accounts": len(primary_accounts) + len(counterparties),
        "transactions": txn_count,
        "str_reports": len(str_lookup),
        "alerts": len(alert_ids),
        "matches": match_count,
        "cases": case_count,
    }

    # Mark the tenant seeded; preserve other settings keys
    settings_dict = dict(org.settings or {})
    settings_dict["demo_seed_pending"] = False
    settings_dict["demo_seed_applied_at"] = now.isoformat()
    settings_dict["demo_seed_counts"] = counts
    org.settings = settings_dict

    await session.flush()
    return {**counts, "tenant_org_id": str(org_id), "applied_at": now.isoformat()}


async def apply_pending_orgs(scale: float = 1.0) -> list[dict[str, object]]:
    """Find every bank tenant with `settings.demo_seed_pending=true` and seed them."""
    results: list[dict[str, object]] = []
    async with SessionLocal() as session:
        # Use jsonb path — settings is JSONB on organizations
        rows = await session.execute(
            select(Organization.id).where(
                Organization.org_type == "bank",
                text("settings ->> 'demo_seed_pending' = 'true'"),
            )
        )
        pending_ids = [row[0] for row in rows.all()]
        if not pending_ids:
            return []

        for org_id in pending_ids:
            try:
                # Apply within a single transaction per tenant so failures don't
                # leave the org in a half-seeded state with the flag still true.
                result = await apply_for_org(session, org_id, scale=scale)
                await session.commit()
                logger.info("demo_bank_seed.applied", extra={"org_id": str(org_id), "counts": result})
                results.append(result)
            except Exception as exc:
                await session.rollback()
                logger.exception("demo_bank_seed.failed", extra={"org_id": str(org_id)})
                results.append({"tenant_org_id": str(org_id), "error": str(exc)})
    return results


# -----------------------------------------------------------------------------
# CLI
# -----------------------------------------------------------------------------

def build_load_plan() -> dict[str, object]:
    return {
        "cross_bank_subjects": len(CROSS_BANK_SUBJECTS),
        "single_bank_subjects": len(SINGLE_BANK_SUBJECTS),
        "expected_alerts": 12,
        "expected_alerts_by_severity": {"critical": 3, "high": 5, "medium": 4},
        "expected_str_reports": 3,
        "expected_str_lifecycle": ["draft", "flagged", "submitted"],
        "expected_cases": 5,
        "expected_case_variants": ["standard", "standard", "proposal", "rfi", "rfi"],
        "expected_matches": 4,
        "default_target_transactions": DEFAULT_TARGET_TRANSACTIONS,
        "seed_days": DEFAULT_SEED_DAYS,
        "channel_mix_pct": dict(CHANNEL_MIX),
    }


def _database_target_hint() -> dict[str, object]:
    parsed = urlparse(get_settings().database_url.replace("+asyncpg", ""))
    return {"host": parsed.hostname, "port": parsed.port, "database": parsed.path.lstrip("/")}


def main() -> None:
    parser = argparse.ArgumentParser(description="Apply the demo bank seed for newly-signed-up tenants.")
    parser.add_argument("--org-id", type=str, default=None, help="Apply seed for this single bank tenant.")
    parser.add_argument("--apply-pending", action="store_true", help="Find every org with settings.demo_seed_pending=true and seed each.")
    parser.add_argument("--apply", action="store_true", help="Actually write rows. Without this and --apply-pending, prints the plan only.")
    parser.add_argument("--scale", type=float, default=1.0, help="Scale factor for transaction volume (1.0 = ~10k, 0.2 = ~2k).")
    args = parser.parse_args()

    if not args.apply and not args.apply_pending:
        print(json.dumps(build_load_plan(), indent=2))
        return

    async def _run() -> object:
        if args.apply_pending:
            return await apply_pending_orgs(scale=args.scale)
        if not args.org_id:
            raise SystemExit("--apply requires --org-id <uuid>, or use --apply-pending instead.")
        async with SessionLocal() as session:
            result = await apply_for_org(session, UUID(args.org_id), scale=args.scale)
            await session.commit()
            return result

    try:
        result = asyncio.run(_run())
    except (ConnectionRefusedError, OSError, SQLAlchemyError) as exc:
        target = _database_target_hint()
        raise SystemExit(
            "Cannot connect to the configured database for demo bank seed. "
            f"Target: host={target['host']} port={target['port']} database={target['database']}. "
            "Set DATABASE_URL and rerun."
        ) from exc

    print(json.dumps(result, indent=2, default=str))


if __name__ == "__main__":
    main()
