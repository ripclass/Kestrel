"""Detection pipelines.

Two entry points:

- ``run_str_pipeline``: called from ``services.str_reports.submit_str_report``.
  Resolves the STR subject identifiers to entities and runs cross-bank matching.

- ``run_scan_pipeline``: called from ``services.scanning.queue_run``. Loads the
  org's transactions and accounts, runs every active rule, resolves flagged
  accounts to entities, runs cross-bank matching, creates alerts, and updates
  the ``detection_runs`` row.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.detection.evaluator import evaluate_accounts
from app.core.detection.loader import load_rules
from app.core.detection.rule_hit import RuleHit
from app.core.detection.scorer import calculate_risk_score
from app.core.graph.builder import build_graph
from app.core.matcher import run_cross_bank_matching
from app.core.resolver import resolve_identifier, resolve_identifiers_from_str
from app.models.account import Account
from app.models.alert import Alert
from app.models.audit import AuditLog
from app.models.connection import Connection
from app.models.detection_run import DetectionRun
from app.models.entity import Entity
from app.models.match import Match
from app.models.str_report import STRReport
from app.models.transaction import Transaction

_RULES_PATH = Path(__file__).resolve().parent / "detection" / "rules"

_SCAN_SCORE_THRESHOLD = 50


def _load_active_rules() -> list[dict[str, Any]]:
    return load_rules(_RULES_PATH)


async def run_str_pipeline(
    session: AsyncSession,
    *,
    str_report: STRReport,
    org_id: uuid.UUID,
) -> dict[str, Any]:
    """Resolve identifiers from an STR, run cross-bank matching, update the STR.

    Mutates ``str_report`` in place to set ``matched_entity_ids``,
    ``cross_bank_hit``, and ``auto_risk_score`` (if matches found). Caller owns
    the surrounding transaction.
    """
    entities = await resolve_identifiers_from_str(
        session, str_report=str_report, org_id=org_id
    )
    matches, alerts = await run_cross_bank_matching(
        session, entities=entities, str_report=str_report, org_id=org_id
    )

    entity_ids = [e.id for e in entities]
    str_report.matched_entity_ids = entity_ids
    str_report.cross_bank_hit = len(matches) > 0
    if matches:
        str_report.auto_risk_score = max(int(m.risk_score or 0) for m in matches)

    session.add(
        AuditLog(
            org_id=org_id,
            user_id=None,
            action="pipeline.str.completed",
            resource_type="str_report",
            resource_id=str_report.id,
            details={
                "entities_resolved": len(entities),
                "cross_bank_matches": len(matches),
                "new_alerts": len(alerts),
            },
        )
    )

    return {
        "entities": entities,
        "matches": matches,
        "alerts": alerts,
    }


async def _load_accounts_and_transactions(
    session: AsyncSession,
    *,
    scope_org_ids: list[uuid.UUID] | None,
    source_run_id: uuid.UUID | None = None,
) -> tuple[list[Account], list[Transaction]]:
    """Load accounts and transactions to scan.

    When ``source_run_id`` is set, only transactions tagged with that run_id
    (and the accounts they touch) are returned — this is the upload path,
    where the scan operates only on freshly-uploaded data.

    Otherwise, ``scope_org_ids=None`` loads everything (regulator scope) and
    a non-empty list filters to those orgs (bank scope).
    """
    if source_run_id is not None:
        txns_result = await session.execute(
            select(Transaction).where(Transaction.run_id == source_run_id)
        )
        transactions = list(txns_result.scalars().all())

        account_ids = {
            tx.src_account_id for tx in transactions if tx.src_account_id is not None
        } | {
            tx.dst_account_id for tx in transactions if tx.dst_account_id is not None
        }
        if not account_ids:
            return [], transactions
        accounts_result = await session.execute(
            select(Account).where(Account.id.in_(account_ids))
        )
        accounts = list(accounts_result.scalars().all())
        return accounts, transactions

    accounts_stmt = select(Account)
    txns_stmt = select(Transaction)
    if scope_org_ids:
        accounts_stmt = accounts_stmt.where(Account.org_id.in_(scope_org_ids))
        txns_stmt = txns_stmt.where(Transaction.org_id.in_(scope_org_ids))

    accounts_result = await session.execute(accounts_stmt)
    accounts = list(accounts_result.scalars().all())
    txns_result = await session.execute(txns_stmt)
    transactions = list(txns_result.scalars().all())

    return accounts, transactions


async def _load_graph_and_flagged(
    session: AsyncSession,
) -> tuple[Any, set[str]]:
    ent_result = await session.execute(select(Entity))
    entities = list(ent_result.scalars().all())
    con_result = await session.execute(select(Connection))
    connections = list(con_result.scalars().all())
    flagged_ids = {
        str(e.id)
        for e in entities
        if (e.risk_score or 0) >= 70 or e.severity in {"high", "critical"}
    }
    graph = build_graph(entities, connections)
    return graph, flagged_ids


async def _resolve_flagged_account_as_entity(
    session: AsyncSession,
    *,
    account: Account,
    org_id: uuid.UUID,
    score: int,
    severity: str,
    reasons: list[dict[str, Any]],
) -> Entity:
    entity = await resolve_identifier(
        session,
        entity_type="account",
        raw_value=account.account_number,
        org_id=org_id,
        source="pattern_scan",
        display_name=account.account_name or account.account_number,
    )
    entity.risk_score = max(int(entity.risk_score or 0), score)
    entity.severity = severity
    metadata = dict(entity.metadata_json or {})
    metadata["last_scan_reasons"] = reasons
    metadata["last_scan_at"] = datetime.now(UTC).isoformat()
    entity.metadata_json = metadata

    acct_meta = dict(account.metadata_json or {})
    acct_meta["entity_id"] = str(entity.id)
    account.metadata_json = acct_meta

    return entity


def _build_scan_alert(
    *,
    entity: Entity,
    account: Account,
    org_id: uuid.UUID,
    hits: list[RuleHit],
    score: int,
    severity: str,
    reasons: list[dict[str, Any]],
) -> Alert:
    top_hit = max(hits, key=lambda h: h.score * h.weight)
    return Alert(
        id=uuid.uuid4(),
        org_id=org_id,
        source_type="scan",
        source_id=None,
        entity_id=entity.id,
        title=top_hit.alert_title or f"Scan alert: {account.account_number}",
        description=top_hit.alert_description or "Multiple detection rules fired",
        alert_type=top_hit.rule_code,
        risk_score=score,
        severity=severity,
        status="open",
        reasons=reasons,
    )


async def run_scan_pipeline(
    session: AsyncSession,
    *,
    run_id: uuid.UUID,
    org_id: uuid.UUID,
    scope_org_ids: list[uuid.UUID] | None = None,
    source_run_id: uuid.UUID | None = None,
) -> dict[str, Any]:
    """Execute the full scan detection pipeline.

    - ``org_id`` is the *caller's* org (used for the DetectionRun row and
      the audit log entry — i.e. who triggered the scan).
    - ``scope_org_ids`` controls which accounts/transactions to evaluate.
      ``None`` means scan everything (regulator scope). A list means filter
      to those orgs.

    For each flagged account, the resulting Entity and Alert are attributed
    to the *bank that owns the account* (``account.org_id``), not to the
    caller, so banks see their own alerts even when a regulator triggered
    the scan.
    """
    run: DetectionRun | None = await session.get(DetectionRun, run_id)
    if run is None:
        raise ValueError(f"DetectionRun {run_id} not found")

    run.status = "processing"
    run.started_at = datetime.now(UTC)

    accounts, transactions = await _load_accounts_and_transactions(
        session, scope_org_ids=scope_org_ids, source_run_id=source_run_id
    )
    graph, flagged_entity_ids = await _load_graph_and_flagged(session)

    rules = _load_active_rules()
    hits = evaluate_accounts(
        accounts=accounts,
        transactions=transactions,
        rules=rules,
        graph=graph,
        flagged_entity_ids=flagged_entity_ids,
    )

    hits_by_account: dict[uuid.UUID, list[RuleHit]] = {}
    for hit in hits:
        hits_by_account.setdefault(hit.account_id, []).append(hit)

    flagged_accounts_out: list[dict[str, Any]] = []
    alerts_created: list[Alert] = []
    matches_touched: list[Match] = []

    account_by_id = {acct.id: acct for acct in accounts}

    for account_id, account_hits in hits_by_account.items():
        account = account_by_id.get(account_id)
        if account is None:
            continue
        score, severity, reasons = calculate_risk_score(account_hits)
        if score < _SCAN_SCORE_THRESHOLD:
            continue

        # Attribute the Entity, Alert, and cross-bank match to the bank that
        # owns the account, not to the user who triggered the scan.
        owning_org_id = account.org_id or org_id

        entity = await _resolve_flagged_account_as_entity(
            session,
            account=account,
            org_id=owning_org_id,
            score=score,
            severity=severity,
            reasons=reasons,
        )
        cb_matches, cb_alerts = await run_cross_bank_matching(
            session, entities=[entity], str_report=None, org_id=owning_org_id
        )
        matches_touched.extend(cb_matches)

        alert = _build_scan_alert(
            entity=entity,
            account=account,
            org_id=owning_org_id,
            hits=account_hits,
            score=score,
            severity=severity,
            reasons=reasons,
        )
        session.add(alert)
        alerts_created.append(alert)
        alerts_created.extend(cb_alerts)

        flagged_accounts_out.append(
            {
                "entity_id": str(entity.id),
                "account_number": account.account_number,
                "account_name": account.account_name or account.account_number,
                "score": score,
                "severity": severity,
                "summary": alert.description,
                "matched_banks": max(1, len(entity.reporting_orgs or [])),
                "total_exposure": float(entity.total_exposure or 0),
                "tags": list(entity.tags or []),
                "linked_alert_id": str(alert.id),
                "linked_case_id": None,
            }
        )

    run.status = "completed"
    run.completed_at = datetime.now(UTC)
    run.accounts_scanned = len(accounts)
    run.tx_count = len(transactions)
    run.alerts_generated = len(alerts_created)
    run.results = {
        "summary": (
            f"{len(flagged_accounts_out)} account candidate(s) flagged from "
            f"{len(accounts)} accounts and {len(transactions)} transactions."
        ),
        "selected_rules": [rule["code"] for rule in rules],
        "flagged_accounts": flagged_accounts_out,
    }

    session.add(
        AuditLog(
            org_id=org_id,
            user_id=None,
            action="pipeline.scan.completed",
            resource_type="detection_run",
            resource_id=run.id,
            details={
                "accounts_scanned": run.accounts_scanned,
                "alerts_generated": run.alerts_generated,
                "flagged_count": len(flagged_accounts_out),
            },
        )
    )

    return {
        "run_id": str(run.id),
        "flagged_accounts": flagged_accounts_out,
        "alerts": alerts_created,
        "matches": matches_touched,
    }
