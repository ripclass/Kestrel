"""Emit the multi-bank seed as raw SQL UPSERTs so it can be applied via the
Supabase MCP / SQL editor without needing a local DATABASE_URL.

Usage:  python -m seed.multi_bank_to_sql > multi_bank_seed.sql
"""
from __future__ import annotations

import json
import random
from datetime import UTC, datetime, timedelta
from uuid import UUID

from seed.multi_bank_synthetic import (
    NAMESPACE,
    RNG_SEED,
    _bank_orgs,
    _bdt_amount,
    _channel_for_bank,
    _cross_bank_entities,
    _single_bank_entities,
    _stable_uuid,
)


def _q(value: object) -> str:
    """Format a value for SQL. Strings get single-quoted; arrays use ARRAY[...]
    or '{...}'::uuid[]; dicts go through json.dumps + ::jsonb."""
    if value is None:
        return "NULL"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, datetime):
        return f"'{value.astimezone(UTC).isoformat()}'::timestamptz"
    if isinstance(value, UUID):
        return f"'{value}'::uuid"
    if isinstance(value, list):
        if not value:
            return "'{}'::text[]"
        if all(isinstance(v, UUID) for v in value):
            inner = ",".join(f'"{v}"' for v in value)
            return f"'{{{inner}}}'::uuid[]"
        if all(isinstance(v, str) for v in value):
            inner = ",".join(f'"{v}"' for v in value)
            return f"'{{{inner}}}'::text[]"
        if all(isinstance(v, dict) for v in value):
            return f"'{json.dumps(value).replace(chr(39), chr(39) + chr(39))}'::jsonb"
        raise TypeError(f"Mixed list type: {value!r}")
    if isinstance(value, dict):
        return f"'{json.dumps(value).replace(chr(39), chr(39) + chr(39))}'::jsonb"
    if isinstance(value, str):
        escaped = value.replace("'", "''")
        return f"'{escaped}'"
    raise TypeError(f"Unsupported SQL value type: {type(value).__name__}")


def _upsert(table: str, row: dict[str, object], pk: str = "id") -> str:
    cols = list(row.keys())
    values = ",".join(_q(row[c]) for c in cols)
    update_clause = ",".join(f"{c}=EXCLUDED.{c}" for c in cols if c != pk)
    return (
        f"INSERT INTO public.{table} ({','.join(cols)}) VALUES ({values}) "
        f"ON CONFLICT ({pk}) DO UPDATE SET {update_clause};"
    )


def emit_sql() -> str:
    cross = _cross_bank_entities()
    single = _single_bank_entities()
    banks = _bank_orgs()
    now = datetime.now(tz=UTC)
    rng = random.Random(RNG_SEED)

    statements: list[str] = ["-- Multi-bank synthetic seed (V2 phase 1.2). Idempotent UPSERTs.", "BEGIN;"]

    # --- Cross-bank entities ---
    cross_uuids: dict[str, UUID] = {}
    for e in cross:
        eid = _stable_uuid("entity", e.key)
        cross_uuids[e.key] = eid
        org_uuids = [UUID(banks[s]["id"]) for s in e.bank_slugs if s in banks]
        statements.append(_upsert("entities", {
            "id": eid,
            "entity_type": e.entity_type,
            "canonical_value": e.canonical_value,
            "display_value": e.display_value,
            "display_name": e.display_name,
            "risk_score": e.risk_score,
            "severity": e.severity,
            "confidence": 0.92,
            "status": "active",
            "source": "synthetic_multi_bank_seed",
            "reporting_orgs": org_uuids,
            "report_count": len(org_uuids),
            "first_seen": now - timedelta(days=21),
            "last_seen": now - timedelta(hours=4),
            "total_exposure": _bdt_amount(e.severity, random.Random(e.key)) * len(org_uuids),
            "tags": ["cross_bank", "multi_bank_seed"],
            "notes": e.narrative_hook,
            "metadata": {"seed_source": "multi_bank_synthetic", "topology": f"{len(org_uuids)}-bank"},
        }))

    # --- Single-bank entities ---
    single_uuids: dict[str, UUID] = {}
    for e in single:
        eid = _stable_uuid("entity", e.key)
        single_uuids[e.key] = eid
        org_uuid = UUID(banks[e.bank_slug]["id"])
        statements.append(_upsert("entities", {
            "id": eid,
            "entity_type": e.entity_type,
            "canonical_value": e.canonical_value,
            "display_value": e.display_value,
            "display_name": e.display_name,
            "risk_score": e.risk_score,
            "severity": e.severity,
            "confidence": 0.78,
            "status": "active",
            "source": "synthetic_multi_bank_seed",
            "reporting_orgs": [org_uuid],
            "report_count": 1,
            "first_seen": now - timedelta(days=14),
            "last_seen": now - timedelta(hours=12),
            "total_exposure": _bdt_amount(e.severity, random.Random(e.key)),
            "tags": ["single_bank", "multi_bank_seed"],
            "notes": e.narrative_hook,
            "metadata": {"seed_source": "multi_bank_synthetic", "topology": "1-bank", "bank_slug": e.bank_slug},
        }))

    # --- Accounts (entity-bank pairs, skip DBBL for cross-bank) ---
    pairs: list[tuple[str, str, UUID, str, int, str]] = []
    for e in cross:
        for slug in e.bank_slugs:
            if slug == "dutch-bangla-bank":
                continue
            pairs.append((e.key, slug, cross_uuids[e.key], e.display_name, e.risk_score, e.severity))
    for e in single:
        pairs.append((e.key, e.bank_slug, single_uuids[e.key], e.display_name, e.risk_score, e.severity))

    for entity_key, slug, entity_uuid, display_name, risk, _ in pairs:
        org_uuid = UUID(banks[slug]["id"])
        bank_code = banks[slug]["bank_code"]
        acct_key = f"{slug}:{entity_key}"
        acct_uuid = _stable_uuid("account", acct_key)
        statements.append(_upsert("accounts", {
            "id": acct_uuid,
            "org_id": org_uuid,
            "account_number": str(_stable_uuid("acct-number", acct_key).int)[:13],
            "account_name": display_name,
            "bank_code": bank_code,
            "account_type": "current",
            "risk_tier": "watch" if risk >= 70 else "normal",
            "metadata": {"seed_source": "multi_bank_synthetic", "entity_id": str(entity_uuid), "entity_key": entity_key},
        }))

        # Counterparty account
        cp_uuid = _stable_uuid("account", f"{slug}:{entity_key}:counterparty")
        statements.append(_upsert("accounts", {
            "id": cp_uuid,
            "org_id": org_uuid,
            "account_number": str(_stable_uuid("acct-number", f"{slug}:{entity_key}:counterparty").int)[:13],
            "account_name": f"Counterparty for {entity_key}",
            "bank_code": bank_code,
            "account_type": "synthetic",
            "risk_tier": "watch",
            "metadata": {"seed_source": "multi_bank_synthetic", "counterparty_for": entity_key},
        }))

    # --- Transactions ---
    severity_map = {**{e.key: e.severity for e in cross}, **{e.key: e.severity for e in single}}
    for entity_key, slug, _, _, _, _ in pairs:
        org_uuid = UUID(banks[slug]["id"])
        acct_uuid = _stable_uuid("account", f"{slug}:{entity_key}")
        cp_uuid = _stable_uuid("account", f"{slug}:{entity_key}:counterparty")
        sev = severity_map.get(entity_key, "low")
        for n in range(rng.randint(3, 4)):
            tx_uuid = _stable_uuid("transaction", f"{slug}:{entity_key}:{n}")
            is_credit = (n % 2 == 0)
            statements.append(_upsert("transactions", {
                "id": tx_uuid,
                "org_id": org_uuid,
                "run_id": None,
                "posted_at": now - timedelta(days=rng.randint(1, 28), hours=rng.randint(0, 23)),
                "src_account_id": cp_uuid if is_credit else acct_uuid,
                "dst_account_id": acct_uuid if is_credit else cp_uuid,
                "amount": _bdt_amount(sev, rng),
                "currency": "BDT",
                "channel": _channel_for_bank(slug, rng),
                "tx_type": "credit" if is_credit else "debit",
                "description": f"Synthetic multi-bank seed · {slug} · {entity_key}",
                "balance_after": float(rng.randint(100_000, 5_000_000)),
                "metadata": {"seed_source": "multi_bank_synthetic", "entity_id": str(_stable_uuid("entity", entity_key)), "entity_key": entity_key},
            }))

    # --- STR reports (cross-bank) ---
    for e in cross:
        for slug in e.bank_slugs:
            org_uuid = UUID(banks[slug]["id"])
            ref = f"STR-{banks[slug]['bank_code']}-{e.key[:8].upper()}"
            uid = _stable_uuid("str-report", f"{slug}:{e.key}")
            r = random.Random(f"{e.key}:{slug}")
            statements.append(_upsert("str_reports", {
                "id": uid,
                "org_id": org_uuid,
                "report_ref": ref,
                "status": "flagged" if e.risk_score >= 70 else "submitted",
                "report_type": "str",
                "subject_name": e.display_name,
                "subject_account": e.canonical_value if e.entity_type == "account" else e.display_value,
                "subject_bank": banks[slug]["name"],
                "subject_phone": e.canonical_value if e.entity_type == "phone" else None,
                "subject_nid": e.canonical_value if e.entity_type == "nid" else None,
                "subject_wallet": None,
                "total_amount": _bdt_amount(e.severity, r),
                "currency": "BDT",
                "transaction_count": 4,
                "primary_channel": _channel_for_bank(slug, r),
                "channels": ["NPSB", "BEFTN", "MFS"],
                "category": "money_laundering",
                "narrative": e.narrative_hook,
                "auto_risk_score": e.risk_score,
                "matched_entity_ids": [cross_uuids[e.key]],
                "cross_bank_hit": True,
                "metadata": {"seed_source": "multi_bank_synthetic", "topology": f"{len(e.bank_slugs)}-bank", "entity_key": e.key},
                "reported_at": now - timedelta(days=r.randint(1, 25)),
            }))

    # --- STR reports (single-bank) ---
    for e in single:
        org_uuid = UUID(banks[e.bank_slug]["id"])
        ref = f"STR-{banks[e.bank_slug]['bank_code']}-{e.key[:8].upper()}"
        uid = _stable_uuid("str-report", f"{e.bank_slug}:{e.key}")
        r = random.Random(e.key)
        statements.append(_upsert("str_reports", {
            "id": uid,
            "org_id": org_uuid,
            "report_ref": ref,
            "status": "submitted",
            "report_type": "str",
            "subject_name": e.display_name,
            "subject_account": e.canonical_value if e.entity_type == "account" else e.display_value,
            "subject_bank": banks[e.bank_slug]["name"],
            "subject_phone": e.canonical_value if e.entity_type == "phone" else None,
            "subject_nid": e.canonical_value if e.entity_type == "nid" else None,
            "subject_wallet": None,
            "total_amount": _bdt_amount(e.severity, r),
            "currency": "BDT",
            "transaction_count": 3,
            "primary_channel": _channel_for_bank(e.bank_slug, r),
            "channels": ["NPSB", "BEFTN"],
            "category": "fraud",
            "narrative": e.narrative_hook,
            "auto_risk_score": e.risk_score,
            "matched_entity_ids": [single_uuids[e.key]],
            "cross_bank_hit": False,
            "metadata": {"seed_source": "multi_bank_synthetic", "topology": "1-bank", "entity_key": e.key},
            "reported_at": now - timedelta(days=r.randint(1, 20)),
        }))

    # --- Matches ---
    for e in cross:
        match_uuid = _stable_uuid("match", e.key)
        r = random.Random(e.key)
        statements.append(_upsert("matches", {
            "id": match_uuid,
            "entity_id": cross_uuids[e.key],
            "match_key": e.canonical_value,
            "match_type": e.entity_type,
            "involved_org_ids": [UUID(banks[s]["id"]) for s in e.bank_slugs if s in banks],
            "involved_str_ids": [_stable_uuid("str-report", f"{s}:{e.key}") for s in e.bank_slugs],
            "match_count": len(e.bank_slugs),
            "total_exposure": _bdt_amount(e.severity, r) * len(e.bank_slugs),
            "risk_score": e.risk_score,
            "severity": e.severity,
            "status": "investigating",
            "notes": [{"seed_source": "multi_bank_synthetic"}],
            "detected_at": now - timedelta(days=r.randint(1, 12)),
        }))

    # --- Cross-bank alerts (one per involved bank per match) ---
    for e in cross:
        match_uuid = _stable_uuid("match", e.key)
        for slug in e.bank_slugs:
            alert_uuid = _stable_uuid("alert", f"crossbank:{e.key}:{slug}")
            statements.append(_upsert("alerts", {
                "id": alert_uuid,
                "org_id": UUID(banks[slug]["id"]),
                "source_type": "cross_bank",
                "source_id": match_uuid,
                "entity_id": cross_uuids[e.key],
                "title": f"Cross-bank match: {e.display_name}",
                "description": e.narrative_hook,
                "alert_type": "cross_bank_match",
                "risk_score": e.risk_score,
                "severity": e.severity,
                "status": "open",
                "reasons": [{"rule": "cross_bank_match", "score": e.risk_score, "reason_text": f"Reported by {len(e.bank_slugs)} institutions"}],
            }))

    statements.append("COMMIT;")
    return "\n".join(statements)


if __name__ == "__main__":
    print(emit_sql())
