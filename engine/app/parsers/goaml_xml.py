"""goAML XML report parser.

goAML is the reporting format every BFIU-reporting bank already knows
how to emit. The schema varies by deployment, so this parser is
deliberately permissive: it extracts the known high-value fields,
collects identifiers we can feed through the entity resolver, and
logs warnings for anything it doesn't recognize rather than rejecting
the whole document.

Maps goAML concepts to Kestrel:
- <submission_code> (STR/SAR/CTR) → report_type
- <report_code> → surfaced as metadata
- First <t_from> or first <activity> subject → primary subject fields
- Every <transaction> → a Transaction row tagged with the import run_id
- Every <from_account>/<to_account>/<from_person>/<to_person>/<from_entity>/<to_entity>
  → a subject identifier for the entity resolver
"""
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from io import BytesIO

from lxml import etree


_SUBMISSION_TO_REPORT_TYPE: dict[str, str] = {
    "STR": "str",
    "SAR": "sar",
    "CTR": "ctr",
    "TBML": "tbml",
    "IER": "ier",
    "ADDL": "additional_info",
    "ADDITIONAL": "additional_info",
    "AMSTR": "adverse_media_str",
    "AMSAR": "adverse_media_sar",
    "ESC": "escalated",
    "COMP": "complaint",
    "COMPLAINT": "complaint",
    "INT": "internal",
    "INTERNAL": "internal",
}


@dataclass
class SubjectIdentifier:
    role: str                # "from" | "to" | "about"
    kind: str                # "account" | "person" | "entity" | "phone" | "wallet" | "nid"
    value: str
    display_name: str | None = None


@dataclass
class ParsedTransaction:
    transaction_ref: str | None
    amount: Decimal | None
    currency: str | None
    channel: str | None
    posted_at: datetime | None
    source_account: str | None
    destination_account: str | None
    description: str | None
    metadata: dict[str, object] = field(default_factory=dict)


@dataclass
class ParsedReport:
    submission_code: str
    report_type: str
    report_code: str | None = None
    reporting_entity_id: str | None = None
    reporting_person_name: str | None = None
    reporting_location: str | None = None
    submitted_at: datetime | None = None
    subject_name: str | None = None
    subject_account: str | None = None
    subject_bank: str | None = None
    subject_phone: str | None = None
    subject_wallet: str | None = None
    subject_nid: str | None = None
    narrative: str | None = None
    total_amount: Decimal = Decimal(0)
    currency: str = "BDT"
    primary_channel: str | None = None
    date_range_start: date | None = None
    date_range_end: date | None = None
    transactions: list[ParsedTransaction] = field(default_factory=list)
    subjects: list[SubjectIdentifier] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


class GoAMLParseError(ValueError):
    """Raised when the document is not usable as a goAML report."""


def _text(element: etree._Element | None, path: str) -> str | None:
    if element is None:
        return None
    child = element.find(path)
    if child is None:
        return None
    value = (child.text or "").strip()
    return value or None


def _decimal(value: str | None) -> Decimal | None:
    if not value:
        return None
    try:
        return Decimal(value.replace(",", ""))
    except (InvalidOperation, ValueError):
        return None


def _iso_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    for pattern in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(value[:19] if len(value) >= 19 else value, pattern)
        except ValueError:
            continue
    return None


def _iso_date(value: str | None) -> date | None:
    dt = _iso_datetime(value)
    return dt.date() if dt else None


def _collect_subjects(txn_el: etree._Element, report: ParsedReport) -> None:
    """Extract every subject-like child and add to report.subjects."""
    subject_paths: list[tuple[str, str, str]] = [
        # role, kind, XPath (relative to element)
        ("from", "account", "from_account/account"),
        ("from", "account", "t_from/from_account/account"),
        ("to", "account", "to_account/account"),
        ("to", "account", "t_to/to_account/account"),
        ("from", "person", "from_person/nationality_document/document_number"),
        ("from", "person", "t_from/from_person/nationality_document/document_number"),
        ("to", "person", "to_person/nationality_document/document_number"),
        ("to", "person", "t_to/to_person/nationality_document/document_number"),
        ("from", "phone", "from_person/phones/phone/tph_number"),
        ("from", "phone", "t_from/from_person/phones/phone/tph_number"),
        ("to", "phone", "to_person/phones/phone/tph_number"),
        ("to", "phone", "t_to/to_person/phones/phone/tph_number"),
        ("from", "entity", "from_entity/name"),
        ("from", "entity", "t_from/from_entity/name"),
        ("to", "entity", "to_entity/name"),
        ("to", "entity", "t_to/to_entity/name"),
    ]
    for role, kind, path in subject_paths:
        for element in txn_el.findall(path):
            value = (element.text or "").strip()
            if not value:
                continue
            display = None
            parent = element.getparent()
            if parent is not None:
                first_last = _text(parent, "first_name") or _text(parent, "name")
                if first_last:
                    last = _text(parent, "last_name")
                    display = f"{first_last} {last}".strip() if last else first_last
            report.subjects.append(
                SubjectIdentifier(role=role, kind=kind, value=value, display_name=display)
            )


def _parse_transaction(txn_el: etree._Element, report: ParsedReport) -> None:
    transaction_ref = _text(txn_el, "transactionnumber") or _text(txn_el, "transaction_number")
    amount_text = _text(txn_el, "amount_local") or _text(txn_el, "amount")
    currency = _text(txn_el, "transaction_currency_code") or _text(txn_el, "currency") or "BDT"
    channel = (
        _text(txn_el, "transaction_description")
        or _text(txn_el, "transmode_code")
        or _text(txn_el, "funds_code")
    )
    posted_at = _iso_datetime(
        _text(txn_el, "date_transaction") or _text(txn_el, "transactiondatetime")
    )
    source_account = (
        _text(txn_el, "from_account/account")
        or _text(txn_el, "t_from/from_account/account")
    )
    destination_account = (
        _text(txn_el, "to_account/account")
        or _text(txn_el, "t_to/to_account/account")
    )
    description = (
        _text(txn_el, "transaction_description")
        or _text(txn_el, "comments")
    )

    amount = _decimal(amount_text)
    if amount is not None:
        report.total_amount += amount

    # Track the first non-null channel as the primary channel on the report.
    if channel and not report.primary_channel:
        report.primary_channel = channel

    # Track the earliest/latest transaction date for the report's date range.
    if posted_at:
        as_date = posted_at.date()
        if report.date_range_start is None or as_date < report.date_range_start:
            report.date_range_start = as_date
        if report.date_range_end is None or as_date > report.date_range_end:
            report.date_range_end = as_date

    report.transactions.append(
        ParsedTransaction(
            transaction_ref=transaction_ref,
            amount=amount,
            currency=currency,
            channel=channel,
            posted_at=posted_at,
            source_account=source_account,
            destination_account=destination_account,
            description=description,
            metadata={},
        )
    )
    _collect_subjects(txn_el, report)


def _apply_primary_subject(report: ParsedReport) -> None:
    """Promote the first sensible subject we saw into the report header."""
    if not report.subjects:
        return

    def _find(role: str, kind: str) -> SubjectIdentifier | None:
        for subject in report.subjects:
            if subject.role == role and subject.kind == kind and subject.value:
                return subject
        return None

    account = _find("from", "account") or _find("to", "account")
    if account:
        report.subject_account = account.value
        if account.display_name:
            report.subject_name = account.display_name

    person = _find("from", "person") or _find("to", "person")
    if person:
        report.subject_nid = report.subject_nid or person.value
        if not report.subject_name and person.display_name:
            report.subject_name = person.display_name

    phone = _find("from", "phone") or _find("to", "phone")
    if phone:
        report.subject_phone = report.subject_phone or phone.value

    entity = _find("from", "entity") or _find("to", "entity")
    if entity and not report.subject_name:
        report.subject_name = entity.value


def parse_goaml_report(xml_bytes: bytes) -> ParsedReport:
    """Parse a goAML XML document into a ParsedReport.

    Raises GoAMLParseError if the document is not a recognizable report.
    """
    # Disable entity expansion to blunt XXE.
    parser = etree.XMLParser(resolve_entities=False, no_network=True, recover=True)
    try:
        tree = etree.parse(BytesIO(xml_bytes), parser=parser)
    except etree.XMLSyntaxError as exc:
        raise GoAMLParseError(f"Malformed XML: {exc}") from exc

    root = tree.getroot()
    if root is None:
        raise GoAMLParseError("Empty document.")

    # Locate the <report> element (could be root or nested).
    report_el = root if root.tag.lower().endswith("report") else root.find(".//report")
    if report_el is None:
        raise GoAMLParseError("No <report> element found.")

    submission_code = (
        _text(report_el, "submission_code")
        or _text(report_el, "rentity_id/submission_code")
        or "STR"
    ).upper()
    report_code = _text(report_el, "report_code")
    mapped_type = _SUBMISSION_TO_REPORT_TYPE.get(submission_code, "str")

    report = ParsedReport(
        submission_code=submission_code,
        report_type=mapped_type,
        report_code=report_code,
        reporting_entity_id=_text(report_el, "rentity_id") or _text(report_el, "rentity_id/entity_id"),
        reporting_person_name=_text(report_el, "reporting_person/first_name"),
        reporting_location=_text(report_el, "location/address/town"),
        submitted_at=_iso_datetime(_text(report_el, "submission_date")),
        narrative=_text(report_el, "reason") or _text(report_el, "action"),
        currency="BDT",
    )

    transactions = report_el.findall(".//transaction")
    activities = report_el.findall(".//activity")
    if not transactions and not activities:
        report.warnings.append(
            "No <transaction> or <activity> elements found; the report will be created without transactions."
        )
    for txn_el in transactions:
        _parse_transaction(txn_el, report)
    for activity_el in activities:
        # Activities aren't transactions per se but may still carry subjects —
        # collect them so the resolver sees them.
        _collect_subjects(activity_el, report)
        # Treat a top-level activity amount as a soft "total_amount" contribution.
        amount = _decimal(_text(activity_el, "total_amount") or _text(activity_el, "amount"))
        if amount is not None:
            report.total_amount += amount

    _apply_primary_subject(report)

    if not report.subject_account and not report.subjects:
        report.warnings.append(
            "No subject identifiers were extracted. Check the goAML XML against your bank's schema version."
        )
    return report
