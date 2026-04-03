from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from dataclasses import asdict
from datetime import UTC, datetime, timedelta
import hashlib
import json
from pathlib import Path
import re
from typing import Any

from app.parsers.statement_pdf import classify_statement_channel, extract_statement_pdf
from seed.organizations import build_organizations

SOURCE_DIR_DEFAULT = Path(r"F:\New Download\Scammers' Bank statement DBBL")
OUTPUT_DIR_DEFAULT = Path(__file__).resolve().parent / "generated" / "dbbl_synthetic"
SYNTHETIC_SALT = "kestrel-dbb-synthetic-v1"
CURATED_SOURCE_FILES = [
    "2 - STMNT - 1781430000701 - RIZWANA ENTERPRISE.pdf",
    "1 - STMNT - 1503326526001 - STAR SHOES.pdf",
    "1. STMNT_1494297585001_MS Khokon Enterprise.pdf",
    "3 - STMNT - 1401805513001 - EMBRYONIC ENTERPRISE.pdf",
]
NAME_PREFIXES = ["Blue", "Eastern", "Delta", "Golden", "Summit", "Prime", "River", "Urban", "Beacon", "Harbor"]
NAME_ROOTS = ["Orbit", "Lantern", "Meridian", "Vertex", "Signal", "Bridge", "Atlas", "Horizon", "Anchor", "Praxis"]
BUSINESS_SUFFIXES = ["Trading", "Enterprise", "Ventures", "Supplies", "Merchants", "Logistics", "Partners", "Works"]
PERSON_SUFFIXES = ["Ahmed", "Rahman", "Karim", "Sarker", "Hossain", "Akter", "Begum", "Islam"]
MATCH_ORGS = ["Dutch-Bangla Bank PLC", "Sonali Bank PLC", "BRAC Bank PLC", "City Bank PLC", "Islami Bank Bangladesh PLC"]


def _stable_hex(kind: str, value: str) -> str:
    return hashlib.sha256(f"{SYNTHETIC_SALT}:{kind}:{value}".encode("utf-8")).hexdigest()


def _stable_int(kind: str, value: str, modulo: int) -> int:
    return int(_stable_hex(kind, value)[:12], 16) % modulo


def synthetic_account_number(raw_value: str, *, length: int | None = None) -> str:
    digits = re.sub(r"\D", "", raw_value)
    target_length = length or max(len(digits), 13)
    digest = _stable_hex("account", digits or raw_value)
    generated = "".join(str(int(char, 16) % 10) for char in digest)
    if not generated or generated[0] == "0":
        generated = f"1{generated}"
    return generated[:target_length]


def synthesize_name(raw_name: str | None) -> str:
    seed = _collapse(raw_name or "unknown")
    digest = _stable_int("name", seed, 10_000)
    prefix = NAME_PREFIXES[digest % len(NAME_PREFIXES)]
    root = NAME_ROOTS[(digest // 7) % len(NAME_ROOTS)]
    business = any(token in seed.lower() for token in ("enterprise", "traders", "shoes", "company", "co.", "store", "trading", "ltd"))
    if business:
        suffix = BUSINESS_SUFFIXES[(digest // 13) % len(BUSINESS_SUFFIXES)]
        return f"{prefix} {root} {suffix}"
    suffix = PERSON_SUFFIXES[(digest // 13) % len(PERSON_SUFFIXES)]
    return f"{prefix} {root} {suffix}"


def _collapse(value: str) -> str:
    return " ".join(value.split())


def _iso_to_dt(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(UTC)


def _round_money(value: float) -> float:
    if value <= 0:
        return 0.0
    rounded = round(value / 100.0) * 100.0
    return float(max(rounded, 100.0))


def _scale_factor(seed: str) -> float:
    return 0.88 + (_stable_int("scale", seed, 21) / 100.0)


def _target_end_date(seed: str) -> datetime:
    base = datetime(2026, 3, 30, tzinfo=UTC)
    return base - timedelta(days=_stable_int("shift", seed, 45))


def _counterparty_code(description: str) -> str:
    hint = description.upper()
    account_match = re.search(r"([0-9]{8,20})", hint)
    if account_match:
        token = account_match.group(1)
    else:
        token = re.sub(r"[^A-Z]", "", hint)[:18] or "COUNTERPARTY"
    return f"CP-{_stable_int('counterparty', token, 10_000):04d}"


def _synthetic_description(description: str, *, tx_type: str) -> str:
    channel = classify_statement_channel(description)
    counterparty = _counterparty_code(description)

    if channel == "mfs_bkash":
        return "bKash merchant intake" if tx_type == "credit" else f"bKash cashout to {counterparty}"
    if channel == "mfs_nagad":
        return "Nagad merchant intake" if tx_type == "credit" else f"Nagad payout to {counterparty}"
    if channel == "rtgs":
        return f"RTGS incoming from {counterparty}" if tx_type == "credit" else f"RTGS outgoing to {counterparty}"
    if channel == "npsb":
        return f"NPSB incoming from {counterparty}" if tx_type == "credit" else f"NPSB outgoing to {counterparty}"
    if channel == "eft":
        return f"EFT incoming from {counterparty}" if tx_type == "credit" else f"EFT outgoing to {counterparty}"
    if channel == "citytouch":
        return f"Citytouch transfer from {counterparty}" if tx_type == "credit" else f"Citytouch transfer to {counterparty}"
    if channel == "cash":
        return "Cash deposit at branch" if tx_type == "credit" else "Cash withdrawal at branch"
    if channel == "cheque":
        return "Cheque clearing credit" if tx_type == "credit" else "Cheque clearing debit"
    if channel == "card":
        return "Card fee and charges"
    if channel == "sms_fee":
        return "SMS renewal fee"
    if "transfer" in description.lower():
        return f"Fund transfer from {counterparty}" if tx_type == "credit" else f"Fund transfer to {counterparty}"
    return f"Account activity via {counterparty}"


def derive_risk_profile(transactions: list[dict[str, Any]]) -> dict[str, Any]:
    total_in = sum(float(item["deposit"]) for item in transactions)
    total_out = sum(float(item["withdrawal"]) for item in transactions)
    channel_counts = Counter(str(item["channel"]) for item in transactions)
    daily: dict[str, dict[str, float]] = defaultdict(lambda: {"in": 0.0, "out": 0.0, "count": 0.0})

    for item in transactions:
        day = str(item["posted_at"])[:10]
        daily[day]["in"] += float(item["deposit"])
        daily[day]["out"] += float(item["withdrawal"])
        daily[day]["count"] += 1

    rapid_cashout_ratio = max(
        (values["out"] / values["in"] for values in daily.values() if values["in"] > 0),
        default=0.0,
    )
    max_daily_count = max((int(values["count"]) for values in daily.values()), default=0)
    cash_share = (channel_counts["cash"] / len(transactions)) if transactions else 0.0
    mfs_share = (
        (channel_counts["mfs_bkash"] + channel_counts["mfs_nagad"]) / len(transactions)
        if transactions
        else 0.0
    )

    score = 20
    tags: list[str] = []
    reasons: list[dict[str, Any]] = []

    if rapid_cashout_ratio >= 0.75:
        score += 28
        tags.append("rapid_cashout")
        reasons.append(
            {
                "rule": "rapid_cashout",
                "score": 28,
                "explanation": f"Peak same-day outflow reached {rapid_cashout_ratio:.0%} of inbound funds.",
            }
        )

    if mfs_share >= 0.25:
        score += 18
        tags.append("mfs_fanout")
        reasons.append(
            {
                "rule": "mfs_fanout",
                "score": 18,
                "explanation": f"{mfs_share:.0%} of parsed transactions used bKash or Nagad channels.",
            }
        )

    if cash_share >= 0.20:
        score += 14
        tags.append("cash_exit")
        reasons.append(
            {
                "rule": "cash_exit",
                "score": 14,
                "explanation": f"{cash_share:.0%} of activity flowed through cash deposit or withdrawal entries.",
            }
        )

    if max_daily_count >= 18:
        score += 16
        tags.append("burst_activity")
        reasons.append(
            {
                "rule": "burst_activity",
                "score": 16,
                "explanation": f"Peak daily velocity hit {max_daily_count} transactions.",
            }
        )

    if total_in and total_out / total_in >= 0.90:
        score += 10
        tags.append("high_turnover")
        reasons.append(
            {
                "rule": "high_turnover",
                "score": 10,
                "explanation": "Outbound movement nearly exhausted inbound funds over the sampled period.",
            }
        )

    score = min(score, 97)
    severity = "critical" if score >= 85 else "high" if score >= 70 else "medium" if score >= 50 else "low"

    return {
        "risk_score": score,
        "severity": severity,
        "tags": sorted(set(tags)),
        "reasons": reasons,
        "stats": {
            "total_in": total_in,
            "total_out": total_out,
            "rapid_cashout_ratio": rapid_cashout_ratio,
            "max_daily_count": max_daily_count,
            "mfs_share": mfs_share,
            "cash_share": cash_share,
        },
    }


def _build_synthetic_transactions(parsed: dict[str, Any], *, entity_id: str, statement_id: str) -> list[dict[str, Any]]:
    transactions = list(parsed["transactions"])
    if not transactions:
        return []

    account_seed = str(parsed.get("account_number") or parsed.get("source_name") or statement_id)
    scale_factor = _scale_factor(account_seed)
    original_end = max(_iso_to_dt(item["posted_at"]) for item in transactions)
    target_end = _target_end_date(account_seed)
    date_offset = target_end - original_end

    first = transactions[0]
    opening_balance = max(float(first["balance_after"]) - float(first["deposit"]) + float(first["withdrawal"]), 0.0)
    synthetic_balance = _round_money(opening_balance * scale_factor)

    synthetic_transactions: list[dict[str, Any]] = []
    for index, item in enumerate(transactions, start=1):
        deposit = _round_money(float(item["deposit"]) * scale_factor)
        withdrawal = _round_money(float(item["withdrawal"]) * scale_factor)
        synthetic_balance = max(synthetic_balance + deposit - withdrawal, 0.0)
        posted_at = (_iso_to_dt(item["posted_at"]) + date_offset).astimezone(UTC)
        tx_type = str(item["tx_type"])
        synthetic_transactions.append(
            {
                "id": f"{statement_id}-tx-{index:04d}",
                "statement_id": statement_id,
                "entity_id": entity_id,
                "posted_at": posted_at.isoformat(),
                "tx_type": tx_type,
                "channel": item["channel"],
                "amount": deposit if deposit > 0 else withdrawal,
                "deposit": deposit,
                "withdrawal": withdrawal,
                "balance_after": synthetic_balance,
                "counterparty_code": _counterparty_code(str(item["description"])),
                "description": _synthetic_description(str(item["description"]), tx_type=tx_type),
            }
        )
    return synthetic_transactions


def _build_entity_record(
    parsed: dict[str, Any],
    *,
    entity_id: str,
    synthetic_name: str,
    synthetic_account: str,
    risk_profile: dict[str, Any],
    transaction_count: int,
) -> dict[str, Any]:
    return {
        "id": entity_id,
        "entity_type": "account",
        "display_value": synthetic_account,
        "display_name": synthetic_name,
        "canonical_value": synthetic_account,
        "risk_score": risk_profile["risk_score"],
        "severity": risk_profile["severity"],
        "confidence": 0.82,
        "status": "investigating" if risk_profile["risk_score"] >= 70 else "active",
        "report_count": 1,
        "reporting_orgs": ["Dutch-Bangla Bank PLC"],
        "total_exposure": round(risk_profile["stats"]["total_in"], 2),
        "tags": risk_profile["tags"],
        "transaction_count": transaction_count,
        "source_bank": "Dutch-Bangla Bank PLC",
        "product_name": parsed.get("product_name"),
    }


def _build_match_record(entity: dict[str, Any], *, index: int) -> dict[str, Any]:
    if int(entity["risk_score"]) < 70:
        return {}

    involved_orgs = MATCH_ORGS[: 3 + (index % 2)]
    return {
        "id": f"match-dbbl-{index:03d}",
        "entity_id": entity["id"],
        "match_key": entity["display_value"],
        "match_type": "account",
        "involved_orgs": involved_orgs,
        "involved_str_ids": [f"STR-2604-{index:06d}", f"STR-2603-{index + 90:06d}", f"STR-2602-{index + 180:06d}"][: len(involved_orgs)],
        "match_count": len(involved_orgs),
        "total_exposure": entity["total_exposure"],
        "risk_score": entity["risk_score"],
        "severity": entity["severity"],
        "status": "investigating",
    }


def _build_connection_records(entity: dict[str, Any], transactions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_counterparty: dict[str, dict[str, Any]] = {}
    for item in transactions:
        counterparty_code = str(item["counterparty_code"])
        record = by_counterparty.setdefault(
            counterparty_code,
            {
                "id": f"cp-{counterparty_code.lower()}",
                "display_value": synthetic_account_number(counterparty_code, length=13),
                "display_name": f"Counterparty {counterparty_code}",
                "amount": 0.0,
                "count": 0,
            },
        )
        record["amount"] += float(item["amount"])
        record["count"] += 1

    top_counterparties = sorted(by_counterparty.values(), key=lambda item: (item["amount"], item["count"]), reverse=True)[:5]
    connections: list[dict[str, Any]] = []
    for index, counterparty in enumerate(top_counterparties, start=1):
        connections.append(
            {
                "id": f"{entity['id']}-edge-{index:02d}",
                "from_entity_id": entity["id"],
                "to_entity_id": counterparty["id"],
                "relation": "transacted",
                "weight": round(counterparty["amount"], 2),
                "counterparty": {
                    "id": counterparty["id"],
                    "entity_type": "account",
                    "display_value": counterparty["display_value"],
                    "display_name": counterparty["display_name"],
                    "risk_score": max(entity["risk_score"] - 8, 40),
                    "severity": "high" if entity["risk_score"] >= 80 else "medium",
                },
            }
        )
    return connections


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _resolve_source_files(source_dir: Path, curated: bool) -> list[Path]:
    if curated:
        return [source_dir / file_name for file_name in CURATED_SOURCE_FILES if (source_dir / file_name).exists()]
    return sorted(source_dir.glob("*.pdf"))


def generate_dataset(
    *,
    source_dir: Path = SOURCE_DIR_DEFAULT,
    output_dir: Path = OUTPUT_DIR_DEFAULT,
    curated: bool = True,
    max_pages: int = 4,
) -> dict[str, Any]:
    organizations = [asdict(organization) for organization in build_organizations()]
    statements: list[dict[str, Any]] = []
    entities: list[dict[str, Any]] = []
    matches: list[dict[str, Any]] = []
    transactions: list[dict[str, Any]] = []
    connections: list[dict[str, Any]] = []
    manifest: list[dict[str, Any]] = []

    for index, path in enumerate(_resolve_source_files(source_dir, curated), start=1):
        parsed = extract_statement_pdf(path.read_bytes(), source_name=path.name, max_pages=max_pages)
        if not parsed["transactions"]:
            continue

        entity_id = f"dbbl-entity-{index:03d}"
        statement_id = f"dbbl-statement-{index:03d}"
        synthetic_name = synthesize_name(str(parsed.get("account_name") or path.stem))
        synthetic_account = synthetic_account_number(str(parsed.get("account_number") or path.stem))
        synthetic_transactions = _build_synthetic_transactions(parsed, entity_id=entity_id, statement_id=statement_id)
        risk_profile = derive_risk_profile(synthetic_transactions)

        entity = _build_entity_record(
            parsed,
            entity_id=entity_id,
            synthetic_name=synthetic_name,
            synthetic_account=synthetic_account,
            risk_profile=risk_profile,
            transaction_count=len(synthetic_transactions),
        )
        match = _build_match_record(entity, index=index)
        if match:
            entity["reporting_orgs"] = list(match["involved_orgs"])
            entity["report_count"] = int(match["match_count"])
        entity_connections = _build_connection_records(entity, synthetic_transactions)

        statements.append(
            {
                "id": statement_id,
                "source_file_hash": _stable_hex("file", path.name)[:16],
                "account_name": synthetic_name,
                "account_number": synthetic_account,
                "source_bank": "Dutch-Bangla Bank PLC",
                "currency": parsed.get("currency") or "BDT",
                "period_from": synthetic_transactions[0]["posted_at"],
                "period_to": synthetic_transactions[-1]["posted_at"],
                "transaction_count": len(synthetic_transactions),
                "risk_score": risk_profile["risk_score"],
                "severity": risk_profile["severity"],
                "tags": risk_profile["tags"],
                "reasons": risk_profile["reasons"],
            }
        )
        entities.append(entity)
        transactions.extend(synthetic_transactions)
        connections.extend(entity_connections)
        if match:
            matches.append(match)

        manifest.append(
            {
                "statement_id": statement_id,
                "source_file_hash": _stable_hex("file", path.name)[:16],
                "source_pages_processed": int(parsed["page_count"]),
                "parsed_transactions": len(parsed["transactions"]),
                "synthetic_transactions": len(synthetic_transactions),
                "risk_score": risk_profile["risk_score"],
            }
        )

    dataset = {
        "dataset_version": 1,
        "source_dir": source_dir.name,
        "curated": curated,
        "max_pages": max_pages,
        "counts": {
            "organizations": len(organizations),
            "statements": len(statements),
            "entities": len(entities),
            "matches": len(matches),
            "transactions": len(transactions),
            "connections": len(connections),
        },
    }

    _write_json(output_dir / "summary.json", dataset)
    _write_json(output_dir / "organizations.json", organizations)
    _write_json(output_dir / "statements.json", statements)
    _write_json(output_dir / "entities.json", entities)
    _write_json(output_dir / "matches.json", matches)
    _write_json(output_dir / "transactions.json", transactions)
    _write_json(output_dir / "connections.json", connections)
    _write_json(output_dir / "manifest.json", manifest)
    return dataset


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate sanitized synthetic seed data from DBBL scam statement PDFs.")
    parser.add_argument("--source-dir", type=Path, default=SOURCE_DIR_DEFAULT)
    parser.add_argument("--output-dir", type=Path, default=OUTPUT_DIR_DEFAULT)
    parser.add_argument("--all-files", action="store_true", help="Parse every PDF in the source directory instead of the curated subset.")
    parser.add_argument("--max-pages", type=int, default=4, help="Limit pages processed per statement to keep generation bounded.")
    args = parser.parse_args()

    dataset = generate_dataset(
        source_dir=args.source_dir,
        output_dir=args.output_dir,
        curated=not args.all_files,
        max_pages=args.max_pages,
    )
    print(json.dumps(dataset, indent=2))


if __name__ == "__main__":
    main()
