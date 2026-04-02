import re
from copy import deepcopy

from app.ai.types import RedactionMode

ACCOUNT_PATTERN = re.compile(r"\b\d{10,20}\b")
PHONE_PATTERN = re.compile(r"\b(?:\+?88)?01\d{9}\b")
EMAIL_PATTERN = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)
NID_PATTERN = re.compile(r"\b\d{10,17}\b")


def mask_by_key(key: str, value: str) -> str | None:
    normalized = key.lower()
    if any(token in normalized for token in ["account", "acct", "iban"]):
        return "[REDACTED_ACCOUNT]"
    if any(token in normalized for token in ["phone", "mobile", "msisdn", "wallet"]):
        return "[REDACTED_PHONE]"
    if "email" in normalized:
        return "[REDACTED_EMAIL]"
    if "nid" in normalized or "national" in normalized:
        return "[REDACTED_NID]"
    return None


def mask_string(value: str) -> str:
    masked = PHONE_PATTERN.sub("[REDACTED_PHONE]", value)
    masked = EMAIL_PATTERN.sub("[REDACTED_EMAIL]", masked)
    masked = ACCOUNT_PATTERN.sub("[REDACTED_ACCOUNT]", masked)
    masked = NID_PATTERN.sub("[REDACTED_NID]", masked)
    return masked


def redact_payload(payload: object, mode: RedactionMode) -> object:
    if mode == RedactionMode.NONE:
        return payload

    if isinstance(payload, str):
        return mask_string(payload)

    if isinstance(payload, list):
        return [redact_payload(item, mode) for item in payload]

    if isinstance(payload, tuple):
        return [redact_payload(item, mode) for item in payload]

    if isinstance(payload, dict):
        redacted = deepcopy(payload)
        for key, value in redacted.items():
            if isinstance(value, str):
                key_mask = mask_by_key(str(key), value)
                if key_mask is not None:
                    redacted[key] = key_mask
                    continue
            redacted[key] = redact_payload(value, mode)
        return redacted

    return payload
