from __future__ import annotations

from collections.abc import Iterable
from datetime import UTC, datetime
from io import BytesIO
import re
from typing import Any

import pdfplumber

DATE_FORMATS = ("%d-%b-%y", "%d-%b-%Y", "%d-%m-%Y", "%d-%m-%y")
DATE_PATTERN = re.compile(r"^\d{2}-(?:\d{2}|[A-Za-z]{3})-\d{2,4}$")
PERIOD_PATTERN = re.compile(
    r"Period From\s*:?\s*(?P<from>\d{2}-(?:\d{2}|[A-Za-z]{3})-\d{2,4})\s*To\s*(?P<to>\d{2}-(?:\d{2}|[A-Za-z]{3})-\d{2,4})",
    re.IGNORECASE,
)
ACCOUNT_PATTERN = re.compile(r"Account Number\s*:?\s*(?P<account>[0-9]{8,20})", re.IGNORECASE)
CUSTOMER_PATTERN = re.compile(r"Customer ID\s*:?\s*(?P<customer>[A-Za-z0-9-]+)", re.IGNORECASE)
PRODUCT_PATTERN = re.compile(r"Product Name\s*:?\s*(?P<product>.+?)\s+Currency\s*:?\s*(?P<currency>[A-Z]{3})", re.IGNORECASE)
FILENAME_ACCOUNT_PATTERN = re.compile(r"(?P<account>[0-9]{8,20})")
FILENAME_NAME_PATTERN = re.compile(r"(?:\d{8,20}|STMNT|Statement|STATEMENT|AC|NO|of|Account|_|-)+(?P<name>[A-Za-z][A-Za-z .&/'-]{3,})")


def _collapse_spaces(value: str) -> str:
    return " ".join(value.split())


def _parse_date_token(value: str | None) -> datetime | None:
    if not value:
        return None

    candidate = value.strip()
    if not DATE_PATTERN.match(candidate):
        return None

    for date_format in DATE_FORMATS:
        try:
            return datetime.strptime(candidate.title(), date_format).replace(tzinfo=UTC)
        except ValueError:
            continue
    return None


def _clean_amount_fragment(value: str) -> str:
    cleaned = re.sub(r"[^0-9,.\-]", "", value)
    cleaned = cleaned.strip(",.")
    if cleaned in {"", "-", ".", "-.", "--"}:
        return ""
    return cleaned


def _parse_amount_fragment(value: str) -> float:
    cleaned = _clean_amount_fragment(value)
    if not cleaned:
        return 0.0

    try:
        return float(cleaned.replace(",", ""))
    except ValueError:
        digits = re.findall(r"\d+", cleaned)
        if not digits:
            return 0.0
        return float("".join(digits))


def classify_statement_channel(description: str) -> str:
    text = description.lower()
    if "bkash" in text:
        return "mfs_bkash"
    if "nagad" in text:
        return "mfs_nagad"
    if "rtgs" in text:
        return "rtgs"
    if "npsb" in text:
        return "npsb"
    if "eft" in text:
        return "eft"
    if "citytouch" in text or "city touch" in text:
        return "citytouch"
    if "cash" in text:
        return "cash"
    if "card" in text:
        return "card"
    if "sms" in text:
        return "sms_fee"
    if "cheque" in text or "clg" in text:
        return "cheque"
    if "transfer" in text or "ac xfr" in text:
        return "transfer"
    return "other"


def _classify_tx_type(description: str, withdrawal: float, deposit: float) -> str:
    text = description.lower()
    if "fee" in text or "charge" in text or "sms" in text:
        return "fee"
    if deposit > 0 and withdrawal == 0:
        return "credit"
    if withdrawal > 0 and deposit == 0:
        return "debit"
    if deposit > 0 and withdrawal > 0:
        return "adjustment"
    return "unknown"


def _cluster_words(words: Iterable[dict[str, Any]], *, tolerance: float = 2.2) -> list[list[dict[str, Any]]]:
    rows: list[list[dict[str, Any]]] = []
    for word in sorted(words, key=lambda item: (item["top"], item["x0"])):
        if float(word.get("height", 0)) > 20:
            continue
        if not rows:
            rows.append([word])
            continue
        previous_top = float(rows[-1][0]["top"])
        if abs(float(word["top"]) - previous_top) <= tolerance:
            rows[-1].append(word)
        else:
            rows.append([word])
    return rows


def _column_text(words: list[dict[str, Any]], *, min_x: float, max_x: float | None = None) -> str:
    selected = [
        str(word["text"]).strip()
        for word in sorted(words, key=lambda item: item["x0"])
        if float(word["x0"]) >= min_x and (max_x is None or float(word["x0"]) < max_x)
    ]
    return _collapse_spaces(" ".join(selected))


def _extract_header(text: str, *, source_name: str | None = None) -> dict[str, Any]:
    lines = [_collapse_spaces(line) for line in text.splitlines() if line.strip()]
    header: dict[str, Any] = {
        "account_name": None,
        "account_number": None,
        "branch": lines[1] if len(lines) > 1 else None,
        "customer_id": None,
        "product_name": None,
        "currency": "BDT",
        "period_from": None,
        "period_to": None,
    }

    period_match = PERIOD_PATTERN.search(text.replace("To", " To "))
    if period_match:
        period_from = _parse_date_token(period_match.group("from"))
        period_to = _parse_date_token(period_match.group("to"))
        header["period_from"] = period_from.isoformat() if period_from else None
        header["period_to"] = period_to.isoformat() if period_to else None

    account_match = ACCOUNT_PATTERN.search(text)
    if account_match:
        header["account_number"] = account_match.group("account")

    customer_match = CUSTOMER_PATTERN.search(text)
    if customer_match:
        header["customer_id"] = customer_match.group("customer")

    product_match = PRODUCT_PATTERN.search(text.replace("\n", " "))
    if product_match:
        header["product_name"] = _collapse_spaces(product_match.group("product"))
        header["currency"] = product_match.group("currency")

    for line in lines:
        if "Period From" in line:
            header["account_name"] = _collapse_spaces(line.split("Period From", 1)[0])
            break

    if source_name:
        filename_account_match = FILENAME_ACCOUNT_PATTERN.search(source_name)
        if not header["account_number"] and filename_account_match:
            header["account_number"] = filename_account_match.group("account")

        if not header["account_name"]:
            stem = re.sub(r"\.pdf$", "", source_name, flags=re.IGNORECASE)
            stem = stem.replace("_", " ")
            stem = re.sub(r"\s+", " ", stem).strip()
            if " - " in stem:
                tail = stem.split(" - ")[-1].strip()
                if tail and not FILENAME_ACCOUNT_PATTERN.fullmatch(tail):
                    header["account_name"] = tail
            else:
                name_match = FILENAME_NAME_PATTERN.search(stem)
                if name_match:
                    header["account_name"] = _collapse_spaces(name_match.group("name"))

    return header


def _parse_transaction_rows(page: pdfplumber.page.Page, *, page_number: int) -> list[dict[str, Any]]:
    words = page.extract_words(x_tolerance=1.5, y_tolerance=2.0, use_text_flow=True)
    rows: list[dict[str, Any]] = []

    for line_words in _cluster_words(words):
        date_text = _column_text(line_words, min_x=0, max_x=72).replace(" ", "")
        posted_at = _parse_date_token(date_text)
        if not posted_at:
            continue

        description = _column_text(line_words, min_x=72, max_x=300)
        if not description:
            continue

        withdrawal = _parse_amount_fragment(_column_text(line_words, min_x=300, max_x=380))
        deposit = _parse_amount_fragment(_column_text(line_words, min_x=380, max_x=470))
        balance = _parse_amount_fragment(_column_text(line_words, min_x=470))

        if withdrawal == 0 and deposit == 0 and balance == 0:
            continue

        rows.append(
            {
                "posted_at": posted_at.isoformat(),
                "description": description,
                "withdrawal": withdrawal,
                "deposit": deposit,
                "balance_after": balance,
                "channel": classify_statement_channel(description),
                "tx_type": _classify_tx_type(description, withdrawal, deposit),
                "page_number": page_number,
            }
        )

    return rows


def extract_statement_pdf(
    pdf_bytes: bytes,
    *,
    source_name: str | None = None,
    max_pages: int | None = None,
) -> dict[str, Any]:
    with pdfplumber.open(BytesIO(pdf_bytes)) as pdf:
        pages = pdf.pages if max_pages is None else pdf.pages[:max_pages]
        first_page_text = pages[0].extract_text() if pages else ""
        header = _extract_header(first_page_text or "", source_name=source_name)

        transactions: list[dict[str, Any]] = []
        for page_number, page in enumerate(pages, start=1):
            transactions.extend(_parse_transaction_rows(page, page_number=page_number))

    return {
        **header,
        "source_name": source_name,
        "page_count": len(pages),
        "transactions": transactions,
    }


def parse_statement_pdf(pdf_bytes: bytes) -> list[dict[str, Any]]:
    return extract_statement_pdf(pdf_bytes)["transactions"]
