"""goAML XML export — inverse of app.parsers.goaml_xml.

Renders a single STRReport as goAML-format XML that peer FIUs and
bank internal systems can ingest. Maps Kestrel's report_type back to
the submission_code, reconstructs the primary subject block, and
embeds any transactions linked to the report via matched runs.
"""
from datetime import datetime
from uuid import UUID
from xml.etree import ElementTree as ET

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.org import Organization
from app.models.str_report import STRReport
from app.models.transaction import Transaction


_REPORT_TYPE_TO_SUBMISSION: dict[str, str] = {
    "str": "STR",
    "sar": "SAR",
    "ctr": "CTR",
    "tbml": "TBML",
    "complaint": "COMP",
    "ier": "IER",
    "internal": "INT",
    "adverse_media_str": "AMSTR",
    "adverse_media_sar": "AMSAR",
    "escalated": "ESC",
    "additional_info": "ADDL",
}


def _sub(parent: ET.Element, tag: str, text: str | None) -> ET.Element:
    child = ET.SubElement(parent, tag)
    if text is not None:
        child.text = str(text)
    return child


def _fmt_dt(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.strftime("%Y-%m-%dT%H:%M:%S")


async def _collect_transactions_for_report(
    session: AsyncSession, report: STRReport
) -> list[Transaction]:
    """Pull transactions linked to the report via metadata or matched run."""
    metadata = report.metadata_json or {}
    run_id_raw = metadata.get("detection_run_id")
    if not run_id_raw:
        return []
    try:
        run_uuid = UUID(str(run_id_raw))
    except ValueError:
        return []
    result = await session.execute(
        select(Transaction).where(Transaction.run_id == run_uuid).order_by(Transaction.posted_at.asc())
    )
    return list(result.scalars().all())


async def render_str_xml(session: AsyncSession, *, report_id: str) -> bytes:
    parsed_id = UUID(report_id)
    result = await session.execute(
        select(STRReport, Organization.name.label("org_name"))
        .join(Organization, Organization.id == STRReport.org_id)
        .where(STRReport.id == parsed_id)
        .limit(1)
    )
    row = result.first()
    if row is None:
        raise ValueError(f"Report {report_id} not found")
    report, org_name = row

    root = ET.Element("report")
    _sub(root, "rentity_id", str(org_name))
    _sub(
        root,
        "submission_code",
        _REPORT_TYPE_TO_SUBMISSION.get(report.report_type or "str", "STR"),
    )
    _sub(root, "report_code", report.report_ref)
    _sub(root, "submission_date", _fmt_dt(report.reported_at or report.created_at))
    _sub(root, "reason", report.narrative or "")

    # Primary subject block
    subject_el = ET.SubElement(root, "primary_subject")
    _sub(subject_el, "subject_name", report.subject_name or "")
    _sub(subject_el, "subject_account", report.subject_account or "")
    _sub(subject_el, "subject_bank", report.subject_bank or "")
    _sub(subject_el, "subject_phone", report.subject_phone or "")
    _sub(subject_el, "subject_wallet", report.subject_wallet or "")
    _sub(subject_el, "subject_nid", report.subject_nid or "")

    # IER-specific fields
    if report.report_type == "ier":
        ier_el = ET.SubElement(root, "ier")
        _sub(ier_el, "direction", report.ier_direction or "")
        _sub(ier_el, "counterparty_fiu", report.ier_counterparty_fiu or "")
        _sub(ier_el, "counterparty_country", report.ier_counterparty_country or "")
        _sub(ier_el, "egmont_ref", report.ier_egmont_ref or "")
        if report.ier_deadline:
            _sub(ier_el, "deadline", report.ier_deadline.isoformat())
        _sub(ier_el, "request_narrative", report.ier_request_narrative or "")
        _sub(ier_el, "response_narrative", report.ier_response_narrative or "")

    # Transactions linked to this report via detection run
    transactions = await _collect_transactions_for_report(session, report)
    for tx in transactions:
        tx_el = ET.SubElement(root, "transaction")
        metadata = tx.metadata_json or {}
        _sub(tx_el, "transactionnumber", str(metadata.get("transaction_ref") or tx.id))
        _sub(tx_el, "date_transaction", _fmt_dt(tx.posted_at))
        _sub(tx_el, "amount_local", f"{float(tx.amount or 0):.2f}")
        _sub(tx_el, "transaction_currency_code", tx.currency or "BDT")
        _sub(tx_el, "transmode_code", tx.channel or "")
        _sub(tx_el, "transaction_description", tx.description or "")
        if metadata.get("source_account"):
            t_from = ET.SubElement(tx_el, "t_from")
            from_account = ET.SubElement(t_from, "from_account")
            _sub(from_account, "account", str(metadata["source_account"]))
        if metadata.get("destination_account"):
            t_to = ET.SubElement(tx_el, "t_to")
            to_account = ET.SubElement(t_to, "to_account")
            _sub(to_account, "account", str(metadata["destination_account"]))

    return b'<?xml version="1.0" encoding="UTF-8"?>\n' + ET.tostring(root)
