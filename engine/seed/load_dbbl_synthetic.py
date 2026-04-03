from __future__ import annotations

import argparse
import asyncio
from collections import Counter
from dataclasses import asdict
from datetime import UTC, datetime
import json
from pathlib import Path
from urllib.parse import urlparse
from uuid import UUID, uuid5

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from app.config import get_settings
from app.models.account import Account
from app.models.alert import Alert
from app.models.case import Case
from app.models.connection import Connection
from app.models.entity import Entity
from app.models.match import Match
from app.models.org import Organization
from app.models.str_report import STRReport
from app.models.transaction import Transaction
from app.database import SessionLocal
from seed.dbbl_synthetic import OUTPUT_DIR_DEFAULT
from seed.organizations import OrganizationSeed, build_organizations

NAMESPACE = UUID("8d393384-a67a-4b64-bf0b-7b66b8d5da76")
DBBL_ORG_NAME = "Dutch-Bangla Bank PLC"


def _stable_uuid(kind: str, value: str) -> UUID:
    return uuid5(NAMESPACE, f"{kind}:{value}")


def _read_json(path: Path) -> list[dict[str, object]] | dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_dataset(root: Path) -> dict[str, object]:
    return {
        "summary": _read_json(root / "summary.json"),
        "organizations": _read_json(root / "organizations.json"),
        "statements": _read_json(root / "statements.json"),
        "entities": _read_json(root / "entities.json"),
        "matches": _read_json(root / "matches.json"),
        "connections": _read_json(root / "connections.json"),
        "transactions": _read_json(root / "transactions.json"),
    }


def _organization_seed_map() -> dict[str, OrganizationSeed]:
    return {seed.name: seed for seed in build_organizations()}


def _parse_uuid(value: str | UUID) -> UUID:
    return value if isinstance(value, UUID) else UUID(str(value))


def _parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(UTC)


def _database_target_hint() -> dict[str, object]:
    parsed = urlparse(get_settings().database_url.replace("+asyncpg", ""))
    return {
        "host": parsed.hostname,
        "port": parsed.port,
        "database": parsed.path.lstrip("/"),
    }


async def _ensure_organizations(session, dataset_orgs: list[dict[str, object]]) -> dict[str, UUID]:
    configured = _organization_seed_map()
    name_to_uuid: dict[str, UUID] = {}

    for row in dataset_orgs:
        name = str(row["name"])
        desired = configured.get(name)
        desired_id = _parse_uuid(desired.id if desired else row["id"])
        slug = str((desired.slug if desired else row["slug"]))
        org_type = str(desired.org_type if desired else row["org_type"])
        bank_code = desired.bank_code if desired else row.get("bank_code")

        existing = await session.get(Organization, desired_id)
        if existing is None:
            existing = (
                await session.execute(
                    select(Organization).where(
                        (Organization.slug == slug) | (Organization.name == name)
                    )
                )
            ).scalars().first()

        if existing is None:
            existing = Organization(
                id=desired_id,
                name=name,
                slug=slug,
                org_type=org_type,
                bank_code=bank_code,
                settings={},
            )
            session.add(existing)
        else:
            existing.name = name
            existing.slug = slug
            existing.org_type = org_type
            existing.bank_code = bank_code

        name_to_uuid[name] = existing.id

    await session.flush()
    return name_to_uuid


async def _upsert_entities(
    session,
    *,
    entities_payload: list[dict[str, object]],
    matches_payload: list[dict[str, object]],
    name_to_uuid: dict[str, UUID],
) -> dict[str, UUID]:
    entity_ids: dict[str, UUID] = {}
    match_orgs = {
        str(item["entity_id"]): [name_to_uuid[name] for name in item.get("involved_orgs", []) if name in name_to_uuid]
        for item in matches_payload
    }

    for row in entities_payload:
        synthetic_id = str(row["id"])
        entity_uuid = _stable_uuid("entity", synthetic_id)
        reporting_orgs = match_orgs.get(synthetic_id) or [
            name_to_uuid[name] for name in row.get("reporting_orgs", []) if name in name_to_uuid
        ]

        existing = await session.get(Entity, entity_uuid)
        if existing is None:
            existing = Entity(id=entity_uuid)
            session.add(existing)

        existing.entity_type = str(row["entity_type"])
        existing.canonical_value = str(row["canonical_value"])
        existing.display_value = str(row["display_value"])
        existing.display_name = str(row.get("display_name") or "")
        existing.risk_score = int(row.get("risk_score") or 0)
        existing.severity = str(row.get("severity") or "low")
        existing.confidence = float(row.get("confidence") or 0.82)
        existing.status = str(row.get("status") or "active")
        existing.source = "synthetic_dbbl_seed"
        existing.reporting_orgs = reporting_orgs
        existing.report_count = max(int(row.get("report_count") or 0), len(reporting_orgs), 1)
        existing.first_seen = _parse_dt(str(row.get("first_seen") or row.get("last_seen") or datetime.now(tz=UTC).isoformat()))
        existing.last_seen = _parse_dt(str(row.get("last_seen") or datetime.now(tz=UTC).isoformat()))
        existing.total_exposure = float(row.get("total_exposure") or 0.0)
        existing.tags = [str(item) for item in row.get("tags", [])]
        existing.notes = "Sanitized synthetic derivative generated from local DBBL scam statements."
        existing.metadata_json = {
            "seed_source": "dbbl_synthetic",
            "transaction_count": int(row.get("transaction_count") or 0),
            "source_bank": row.get("source_bank"),
            "product_name": row.get("product_name"),
        }

        entity_ids[synthetic_id] = entity_uuid

    await session.flush()
    return entity_ids


async def _upsert_counterparty_entities(
    session,
    *,
    connections_payload: list[dict[str, object]],
) -> dict[str, UUID]:
    ids: dict[str, UUID] = {}

    for row in connections_payload:
        counterparty = row.get("counterparty")
        if not isinstance(counterparty, dict):
            continue

        synthetic_id = str(counterparty["id"])
        entity_uuid = _stable_uuid("entity", synthetic_id)
        existing = await session.get(Entity, entity_uuid)
        if existing is None:
            existing = Entity(id=entity_uuid)
            session.add(existing)

        existing.entity_type = str(counterparty.get("entity_type") or "account")
        existing.canonical_value = str(counterparty["display_value"])
        existing.display_value = str(counterparty["display_value"])
        existing.display_name = str(counterparty.get("display_name") or "")
        existing.risk_score = int(counterparty.get("risk_score") or 40)
        existing.severity = str(counterparty.get("severity") or "medium")
        existing.confidence = 0.55
        existing.status = "active"
        existing.source = "synthetic_dbbl_seed"
        existing.reporting_orgs = []
        existing.report_count = 0
        existing.first_seen = datetime.now(tz=UTC)
        existing.last_seen = datetime.now(tz=UTC)
        existing.total_exposure = 0.0
        existing.tags = ["synthetic_counterparty"]
        existing.notes = "Synthetic counterparty derived from sanitized DBBL transaction patterns."
        existing.metadata_json = {"seed_source": "dbbl_synthetic"}

        ids[synthetic_id] = entity_uuid

    await session.flush()
    return ids


async def _upsert_connections(
    session,
    *,
    connections_payload: list[dict[str, object]],
    entity_ids: dict[str, UUID],
) -> int:
    count = 0
    for row in connections_payload:
        connection_uuid = _stable_uuid("connection", str(row["id"]))
        from_uuid = entity_ids[str(row["from_entity_id"])]
        to_uuid = entity_ids[str(row["to_entity_id"])]
        amount = float(row.get("weight") or 0.0)
        weight = round(min(max(amount / 100_000.0, 1.0), 999.99), 2)

        existing = await session.get(Connection, connection_uuid)
        if existing is None:
            existing = Connection(id=connection_uuid)
            session.add(existing)

        existing.from_entity_id = from_uuid
        existing.to_entity_id = to_uuid
        existing.relation = str(row.get("relation") or "transacted")
        existing.weight = weight
        existing.evidence = {
            "amount": amount,
            "seed_source": "dbbl_synthetic",
            "counterparty_display": row.get("counterparty", {}).get("display_name"),
        }
        existing.first_seen = datetime.now(tz=UTC)
        existing.last_seen = datetime.now(tz=UTC)
        count += 1

    await session.flush()
    return count


async def _upsert_accounts_and_transactions(
    session,
    *,
    statements_payload: list[dict[str, object]],
    transactions_payload: list[dict[str, object]],
    entity_ids: dict[str, UUID],
    dbbl_org_id: UUID,
) -> tuple[dict[str, UUID], int]:
    statement_to_account: dict[str, UUID] = {}
    counterparty_accounts: dict[str, UUID] = {}

    for row in statements_payload:
        statement_id = str(row["id"])
        account_uuid = _stable_uuid("account", statement_id)
        existing = await session.get(Account, account_uuid)
        if existing is None:
            existing = Account(id=account_uuid)
            session.add(existing)

        existing.org_id = dbbl_org_id
        existing.account_number = str(row["account_number"])
        existing.account_name = str(row["account_name"])
        existing.bank_code = "DBBL"
        existing.account_type = "current"
        existing.risk_tier = str(row.get("severity") or "normal")
        existing.metadata_json = {
            "seed_source": "dbbl_synthetic",
            "statement_id": statement_id,
        }
        statement_to_account[statement_id] = account_uuid

    await session.flush()

    transaction_count = 0
    for row in transactions_payload:
        transaction_uuid = _stable_uuid("transaction", str(row["id"]))
        statement_id = str(row["statement_id"])
        counterparty_code = str(row["counterparty_code"])
        counterparty_uuid = counterparty_accounts.get(counterparty_code)
        if counterparty_uuid is None:
            counterparty_uuid = _stable_uuid("account", counterparty_code)
            counterparty_accounts[counterparty_code] = counterparty_uuid

            existing_account = await session.get(Account, counterparty_uuid)
            if existing_account is None:
                existing_account = Account(id=counterparty_uuid)
                session.add(existing_account)
            existing_account.org_id = dbbl_org_id
            existing_account.account_number = str(_stable_uuid("counterparty-number", counterparty_code).int)[:13]
            existing_account.account_name = f"Counterparty {counterparty_code}"
            existing_account.bank_code = "DBBL"
            existing_account.account_type = "synthetic"
            existing_account.risk_tier = "watch"
            existing_account.metadata_json = {
                "seed_source": "dbbl_synthetic",
                "counterparty_code": counterparty_code,
            }

        existing_tx = await session.get(Transaction, transaction_uuid)
        if existing_tx is None:
            existing_tx = Transaction(id=transaction_uuid)
            session.add(existing_tx)

        existing_tx.org_id = dbbl_org_id
        existing_tx.run_id = None
        existing_tx.posted_at = _parse_dt(str(row["posted_at"]))
        if str(row["tx_type"]) == "credit":
            existing_tx.src_account_id = counterparty_uuid
            existing_tx.dst_account_id = statement_to_account[statement_id]
        else:
            existing_tx.src_account_id = statement_to_account[statement_id]
            existing_tx.dst_account_id = counterparty_uuid
        existing_tx.amount = float(row["amount"])
        existing_tx.currency = "BDT"
        existing_tx.channel = str(row.get("channel") or "other")
        existing_tx.tx_type = str(row.get("tx_type") or "unknown")
        existing_tx.description = str(row.get("description") or "")
        existing_tx.balance_after = float(row.get("balance_after") or 0.0)
        existing_tx.metadata_json = {
            "seed_source": "dbbl_synthetic",
            "entity_id": str(entity_ids[str(row["entity_id"])]),
            "statement_id": statement_id,
            "counterparty_code": counterparty_code,
        }
        transaction_count += 1

    await session.flush()
    return statement_to_account, transaction_count


async def _upsert_str_reports(
    session,
    *,
    statements_payload: list[dict[str, object]],
    matches_payload: list[dict[str, object]],
    entities_payload: list[dict[str, object]],
    transactions_payload: list[dict[str, object]],
    entity_ids: dict[str, UUID],
    name_to_uuid: dict[str, UUID],
) -> tuple[dict[tuple[str, str], UUID], int]:
    entity_by_id = {str(row["id"]): row for row in entities_payload}
    match_by_entity = {str(row["entity_id"]): row for row in matches_payload}
    statement_channels: dict[str, Counter[str]] = {}
    for transaction in transactions_payload:
        counter = statement_channels.setdefault(str(transaction["statement_id"]), Counter())
        counter[str(transaction.get("channel") or "other")] += 1

    report_lookup: dict[tuple[str, str], UUID] = {}
    count = 0

    for statement in statements_payload:
        statement_id = str(statement["id"])
        entity_row = next((row for row in entities_payload if str(row["display_value"]) == str(statement["account_number"])), None)
        if entity_row is None:
            continue

        entity_id = str(entity_row["id"])
        entity_uuid = entity_ids[entity_id]
        match = match_by_entity.get(entity_id)
        involved_orgs = list(match.get("involved_orgs", [])) if isinstance(match, dict) else [statement["source_bank"]]
        involved_refs = list(match.get("involved_str_ids", [])) if isinstance(match, dict) else [f"STR-SYN-{statement_id[-3:]}"]

        for index, org_name in enumerate(involved_orgs):
            org_uuid = name_to_uuid.get(str(org_name))
            if org_uuid is None:
                continue

            report_ref = (
                str(involved_refs[index])
                if index < len(involved_refs)
                else f"STR-SYN-{statement_id[-3:]}-{index + 1:02d}"
            )
            report_uuid = _stable_uuid("str-report", f"{statement_id}:{org_name}:{report_ref}")
            existing = await session.get(STRReport, report_uuid)
            if existing is None:
                existing = STRReport(id=report_uuid)
                session.add(existing)

            reasons = statement.get("reasons", [])
            existing.org_id = org_uuid
            existing.report_ref = report_ref
            existing.status = "flagged" if int(statement.get("risk_score") or 0) >= 70 else "submitted"
            existing.subject_name = str(statement["account_name"])
            existing.subject_account = str(statement["account_number"])
            existing.subject_bank = org_name
            existing.subject_phone = None
            existing.subject_wallet = None
            existing.subject_nid = None
            existing.total_amount = float(entity_row.get("total_exposure") or 0.0)
            existing.currency = str(statement.get("currency") or "BDT")
            existing.transaction_count = int(statement.get("transaction_count") or 0)
            channel_counter = statement_channels.get(statement_id, Counter())
            existing.primary_channel = channel_counter.most_common(1)[0][0] if channel_counter else "transfer"
            existing.category = "fraud"
            existing.channels = sorted(channel_counter.keys()) if channel_counter else ["transfer"]
            existing.date_range_start = _parse_dt(str(statement["period_from"])).date() if statement.get("period_from") else None
            existing.date_range_end = _parse_dt(str(statement["period_to"])).date() if statement.get("period_to") else None
            existing.narrative = (
                f"Synthetic STR derived from sanitized DBBL statement patterns for {statement['account_name']}. "
                f"Risk score {statement['risk_score']} with indicators: {', '.join(str(item['rule']) for item in reasons) or 'baseline monitoring'}."
            )
            existing.auto_risk_score = int(statement.get("risk_score") or 0)
            existing.matched_entity_ids = [entity_uuid]
            existing.cross_bank_hit = bool(match)
            existing.submitted_by = None
            existing.reviewed_by = None
            existing.metadata_json = {
                "seed_source": "dbbl_synthetic",
                "statement_id": statement_id,
                "tags": statement.get("tags", []),
                "reasons": reasons,
            }
            existing.reported_at = _parse_dt(str(statement["period_to"])) if statement.get("period_to") else datetime.now(tz=UTC)
            report_lookup[(str(org_name), report_ref)] = report_uuid
            count += 1

    await session.flush()
    return report_lookup, count


async def _upsert_matches(
    session,
    *,
    matches_payload: list[dict[str, object]],
    entity_ids: dict[str, UUID],
    name_to_uuid: dict[str, UUID],
    report_lookup: dict[tuple[str, str], UUID],
) -> int:
    count = 0
    for row in matches_payload:
        match_uuid = _stable_uuid("match", str(row["id"]))
        existing = await session.get(Match, match_uuid)
        if existing is None:
            existing = Match(id=match_uuid)
            session.add(existing)

        existing.entity_id = entity_ids[str(row["entity_id"])]
        existing.match_key = str(row["match_key"])
        existing.match_type = str(row["match_type"])
        involved_org_names = [str(name) for name in row.get("involved_orgs", [])]
        involved_refs = [str(value) for value in row.get("involved_str_ids", [])]
        existing.involved_org_ids = [name_to_uuid[name] for name in involved_org_names if name in name_to_uuid]
        existing.involved_str_ids = [
            report_lookup[(org_name, report_ref)]
            for org_name, report_ref in zip(involved_org_names, involved_refs)
            if (org_name, report_ref) in report_lookup
        ]
        existing.match_count = int(row.get("match_count") or len(existing.involved_org_ids))
        existing.total_exposure = float(row.get("total_exposure") or 0.0)
        existing.risk_score = int(row.get("risk_score") or 0)
        existing.severity = str(row.get("severity") or "low")
        existing.status = str(row.get("status") or "investigating")
        existing.notes = [{"seed_source": "dbbl_synthetic"}]
        existing.detected_at = datetime.now(tz=UTC)
        count += 1

    await session.flush()
    return count


async def _upsert_alerts(
    session,
    *,
    statements_payload: list[dict[str, object]],
    entities_payload: list[dict[str, object]],
    entity_ids: dict[str, UUID],
    name_to_uuid: dict[str, UUID],
) -> int:
    entity_by_account = {str(row["display_value"]): row for row in entities_payload}
    bfiu_org = name_to_uuid.get("Bangladesh Financial Intelligence Unit")
    if bfiu_org is None:
        return 0

    count = 0
    for statement in statements_payload:
        if int(statement.get("risk_score") or 0) < 70:
            continue

        entity_row = entity_by_account.get(str(statement["account_number"]))
        if entity_row is None:
            continue

        alert_uuid = _stable_uuid("alert", str(statement["id"]))
        existing = await session.get(Alert, alert_uuid)
        if existing is None:
            existing = Alert(id=alert_uuid)
            session.add(existing)

        existing.org_id = bfiu_org
        existing.source_type = "str_enrichment"
        existing.source_id = None
        existing.entity_id = entity_ids[str(entity_row["id"])]
        existing.title = f"{statement['account_name']} synthetic pattern alert"
        existing.description = "Synthetic alert created from sanitized DBBL statement-derived behavior."
        existing.alert_type = "rapid_cashout" if "rapid_cashout" in statement.get("tags", []) else "pattern_scan"
        existing.risk_score = int(statement.get("risk_score") or 0)
        existing.severity = str(statement.get("severity") or "medium")
        existing.status = "open"
        existing.reasons = list(statement.get("reasons", []))
        existing.assigned_to = None
        existing.case_id = None
        existing.resolved_by = None
        existing.resolved_at = None
        count += 1

    await session.flush()
    return count


async def _upsert_cases(
    session,
    *,
    statements_payload: list[dict[str, object]],
    entities_payload: list[dict[str, object]],
    entity_ids: dict[str, UUID],
    name_to_uuid: dict[str, UUID],
) -> int:
    entity_by_account = {str(row["display_value"]): row for row in entities_payload}
    bfiu_org = name_to_uuid.get("Bangladesh Financial Intelligence Unit")
    if bfiu_org is None:
        return 0

    count = 0
    for statement in statements_payload:
        if int(statement.get("risk_score") or 0) < 80:
            continue

        entity_row = entity_by_account.get(str(statement["account_number"]))
        if entity_row is None:
            continue

        case_uuid = _stable_uuid("case", str(statement["id"]))
        alert_uuid = _stable_uuid("alert", str(statement["id"]))
        existing = await session.get(Case, case_uuid)
        if existing is None:
            existing = Case(id=case_uuid)
            session.add(existing)

        existing.org_id = bfiu_org
        existing.case_ref = f"KST-SYN-{str(statement['id'])[-3:]}"
        existing.title = f"{statement['account_name']} synthetic investigation"
        existing.summary = "Synthetic case created from sanitized DBBL statement-derived patterns."
        existing.category = "fraud"
        existing.severity = str(statement.get("severity") or "medium")
        existing.status = "investigating"
        existing.assigned_to = None
        existing.linked_alert_ids = [alert_uuid]
        existing.linked_entity_ids = [entity_ids[str(entity_row["id"])]]
        existing.total_exposure = float(entity_row.get("total_exposure") or 0.0)
        existing.recovered = 0.0
        existing.timeline = [
            {
                "type": "note",
                "timestamp": statement.get("period_to"),
                "content": "Synthetic case created from sanitized DBBL seed import.",
            }
        ]
        existing.tags = [str(tag) for tag in statement.get("tags", [])]
        existing.due_date = None
        existing.closed_at = None
        count += 1

        alert = await session.get(Alert, alert_uuid)
        if alert is not None:
            alert.case_id = case_uuid

    await session.flush()
    return count


def build_load_plan(dataset_root: Path) -> dict[str, object]:
    dataset = _load_dataset(dataset_root)
    counts = dataset["summary"]["counts"]
    return {
        "dataset_root": str(dataset_root),
        "statements": counts["statements"],
        "entities": counts["entities"],
        "matches": counts["matches"],
        "transactions": counts["transactions"],
        "connections": counts["connections"],
    }


async def apply_dataset(dataset_root: Path) -> dict[str, object]:
    dataset = _load_dataset(dataset_root)
    async with SessionLocal() as session:
        name_to_uuid = await _ensure_organizations(session, dataset["organizations"])
        entity_ids = await _upsert_entities(
            session,
            entities_payload=dataset["entities"],
            matches_payload=dataset["matches"],
            name_to_uuid=name_to_uuid,
        )
        counterparty_ids = await _upsert_counterparty_entities(session, connections_payload=dataset["connections"])
        entity_ids.update(counterparty_ids)
        connection_count = await _upsert_connections(session, connections_payload=dataset["connections"], entity_ids=entity_ids)
        dbbl_org_id = name_to_uuid[DBBL_ORG_NAME]
        _, transaction_count = await _upsert_accounts_and_transactions(
            session,
            statements_payload=dataset["statements"],
            transactions_payload=dataset["transactions"],
            entity_ids=entity_ids,
            dbbl_org_id=dbbl_org_id,
        )
        report_lookup, str_report_count = await _upsert_str_reports(
            session,
            statements_payload=dataset["statements"],
            matches_payload=dataset["matches"],
            entities_payload=dataset["entities"],
            transactions_payload=dataset["transactions"],
            entity_ids=entity_ids,
            name_to_uuid=name_to_uuid,
        )
        match_count = await _upsert_matches(
            session,
            matches_payload=dataset["matches"],
            entity_ids=entity_ids,
            name_to_uuid=name_to_uuid,
            report_lookup=report_lookup,
        )
        alert_count = await _upsert_alerts(
            session,
            statements_payload=dataset["statements"],
            entities_payload=dataset["entities"],
            entity_ids=entity_ids,
            name_to_uuid=name_to_uuid,
        )
        case_count = await _upsert_cases(
            session,
            statements_payload=dataset["statements"],
            entities_payload=dataset["entities"],
            entity_ids=entity_ids,
            name_to_uuid=name_to_uuid,
        )
        await session.commit()

    return {
        "dataset_root": str(dataset_root),
        "organizations": len(name_to_uuid),
        "entities": len(dataset["entities"]) + len(counterparty_ids),
        "connections": connection_count,
        "matches": match_count,
        "transactions": transaction_count,
        "str_reports": str_report_count,
        "alerts": alert_count,
        "cases": case_count,
        "reporting_orgs": Counter(
            org_name
            for row in dataset["matches"]
            for org_name in row.get("involved_orgs", [])
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Load generated DBBL synthetic dataset into the configured Kestrel database.")
    parser.add_argument("--dataset-dir", type=Path, default=OUTPUT_DIR_DEFAULT)
    parser.add_argument("--apply", action="store_true", help="Actually write the dataset into the configured database.")
    args = parser.parse_args()

    if args.apply:
        try:
            result = asyncio.run(apply_dataset(args.dataset_dir))
        except (ConnectionRefusedError, OSError, SQLAlchemyError) as exc:
            target = _database_target_hint()
            raise SystemExit(
                "Cannot connect to the configured database for synthetic backfill. "
                f"Target: host={target['host']} port={target['port']} database={target['database']}. "
                "Start Postgres locally or point DATABASE_URL at the intended Supabase/Postgres instance, then rerun "
                "`python -m seed.load_dbbl_synthetic --apply`."
            ) from exc
        print(json.dumps(result, indent=2, default=str))
        return

    print(json.dumps(build_load_plan(args.dataset_dir), indent=2))


if __name__ == "__main__":
    main()
