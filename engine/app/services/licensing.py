"""On-prem license file (V3 phase 6.5).

Cloud tenants get their plan_id from `organizations.plan_id` (set by a
superadmin via `/admin/team`). On-prem deployments don't have that
operator — the license is shipped as a file, mounted into the engine
container, and read on boot.

Format (YAML or JSON; YAML preferred for operator readability):

    customer: "Example Bank PLC"
    issued_at: "2026-05-05T00:00:00Z"
    expires_at: "2027-05-05T00:00:00Z"
    plan_id: enterprise
    plan_overrides:
      sovereign_ai: true
      cross_bank_intelligence: false
    seats_max: 50
    contact:
      primary: "compliance@example.com.bd"

The license maps to the same Plan / TenantPlan abstraction the cloud
side uses — `plan_overrides` follows the same enable-only semantics, so
an air-gapped customer's overrides cannot accidentally disable a
plan-included feature.

Security model: the license file is a configuration file, not a
cryptographic artifact. Tampering protection is the customer's
responsibility (file-system permissions + ACLs on `/etc/kestrel/`).
The point isn't to prevent a sophisticated customer from running
features they didn't pay for; it's to surface the contractual feature
list to the engine so route-level gates work consistently with cloud.
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import yaml

from app.services.billing import PLANS, Plan, get_plan

logger = logging.getLogger("kestrel.licensing")

WARNING_WINDOW_DAYS = 30


@dataclass(frozen=True, slots=True)
class License:
    customer: str
    plan_id: str
    plan: Plan
    plan_overrides: dict[str, Any]
    issued_at: datetime | None
    expires_at: datetime | None
    seats_max: int | None
    contact: dict[str, str]
    raw: dict[str, Any]

    def is_expired(self, *, now: datetime | None = None) -> bool:
        if self.expires_at is None:
            return False
        return (now or datetime.now(UTC)) > self.expires_at

    def expiring_soon(self, *, now: datetime | None = None, window_days: int = WARNING_WINDOW_DAYS) -> bool:
        if self.expires_at is None:
            return False
        cutoff = (now or datetime.now(UTC)) + timedelta(days=window_days)
        return self.expires_at < cutoff and not self.is_expired(now=now)


def _coerce_datetime(value: Any) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=UTC)
    if isinstance(value, str):
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)
    return None


def parse_license_payload(payload: dict[str, Any]) -> License:
    """Validate + coerce a license dict into a License dataclass.

    Pure function; no IO. Tests cover this directly so we don't need a
    file fixture for every edge case.
    """
    plan_id_raw = str(payload.get("plan_id", "starter")).lower()
    if plan_id_raw not in PLANS:
        logger.warning("license.unknown_plan", extra={"plan_id": plan_id_raw})
        plan_id_raw = "starter"
    overrides = payload.get("plan_overrides") or {}
    if not isinstance(overrides, dict):
        overrides = {}
    seats = payload.get("seats_max")
    seats_max = int(seats) if isinstance(seats, (int, float)) and seats > 0 else None
    contact = payload.get("contact") or {}
    if not isinstance(contact, dict):
        contact = {}
    return License(
        customer=str(payload.get("customer", "")),
        plan_id=plan_id_raw,
        plan=get_plan(plan_id_raw),
        plan_overrides={k: bool(v) for k, v in overrides.items()},
        issued_at=_coerce_datetime(payload.get("issued_at")),
        expires_at=_coerce_datetime(payload.get("expires_at")),
        seats_max=seats_max,
        contact={str(k): str(v) for k, v in contact.items()},
        raw=dict(payload),
    )


def load_license(path: str | Path) -> License | None:
    """Read a YAML or JSON license file and return a parsed License.

    Returns None if the file is missing — engine startup logs a warning
    but does NOT crash; an unlicensed onprem boot defaults to
    starter-plan + sovereign-disabled, which means the operator hasn't
    finished provisioning, not that an attacker is bypassing licensing.
    """
    p = Path(path)
    if not p.is_file():
        logger.warning("license.missing", extra={"path": str(p)})
        return None
    body = p.read_text(encoding="utf-8")
    try:
        if p.suffix.lower() == ".json":
            payload = json.loads(body)
        else:
            payload = yaml.safe_load(body)
    except (yaml.YAMLError, json.JSONDecodeError) as exc:
        logger.error("license.parse_failure", extra={"path": str(p), "error": str(exc)})
        return None
    if not isinstance(payload, dict):
        logger.error("license.not_a_mapping", extra={"path": str(p), "type": type(payload).__name__})
        return None
    license_obj = parse_license_payload(payload)
    if license_obj.is_expired():
        logger.warning(
            "license.expired",
            extra={"customer": license_obj.customer, "expires_at": str(license_obj.expires_at)},
        )
    elif license_obj.expiring_soon():
        logger.warning(
            "license.expiring_soon",
            extra={"customer": license_obj.customer, "expires_at": str(license_obj.expires_at)},
        )
    return license_obj


def license_summary(license_obj: License | None) -> dict[str, Any]:
    """Operator-facing summary; suitable for `/admin/license` exposure."""
    if license_obj is None:
        return {"licensed": False}
    return {
        "licensed": True,
        "customer": license_obj.customer,
        "plan_id": license_obj.plan_id,
        "plan_overrides": license_obj.plan_overrides,
        "issued_at": license_obj.issued_at.isoformat() if license_obj.issued_at else None,
        "expires_at": license_obj.expires_at.isoformat() if license_obj.expires_at else None,
        "seats_max": license_obj.seats_max,
        "contact": license_obj.contact,
        "is_expired": license_obj.is_expired(),
        "expiring_soon": license_obj.expiring_soon(),
    }
