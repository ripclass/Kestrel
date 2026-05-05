"""V3 P6.5 — license file parsing + expiry handling."""
from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

from app.services.licensing import (
    WARNING_WINDOW_DAYS,
    license_summary,
    load_license,
    parse_license_payload,
)


def test_parse_minimal_payload_defaults_to_starter() -> None:
    license_obj = parse_license_payload({"customer": "Tiny Bank"})
    assert license_obj.plan_id == "starter"
    assert license_obj.plan.plan_id == "starter"
    assert license_obj.plan_overrides == {}
    assert license_obj.seats_max is None


def test_unknown_plan_falls_back_to_starter_and_logs() -> None:
    license_obj = parse_license_payload({"plan_id": "platinum"})
    assert license_obj.plan_id == "starter"


def test_overrides_coerce_to_bool() -> None:
    license_obj = parse_license_payload(
        {"plan_id": "enterprise", "plan_overrides": {"sovereign_ai": "yes", "kyc": 0}}
    )
    assert license_obj.plan_overrides == {"sovereign_ai": True, "kyc": False}


def test_iso_timestamps_parse_with_z_and_offset() -> None:
    license_obj = parse_license_payload(
        {
            "issued_at": "2026-05-05T00:00:00Z",
            "expires_at": "2027-05-05T00:00:00+00:00",
        }
    )
    assert license_obj.issued_at == datetime(2026, 5, 5, tzinfo=UTC)
    assert license_obj.expires_at == datetime(2027, 5, 5, tzinfo=UTC)


def test_naive_datetime_promotes_to_utc() -> None:
    license_obj = parse_license_payload({"expires_at": "2027-05-05T00:00:00"})
    assert license_obj.expires_at is not None
    assert license_obj.expires_at.tzinfo is UTC


def test_invalid_iso_returns_none_for_that_field() -> None:
    license_obj = parse_license_payload({"expires_at": "not-a-date"})
    assert license_obj.expires_at is None


def test_is_expired_compares_against_now() -> None:
    past = datetime(2020, 1, 1, tzinfo=UTC)
    future = datetime(2099, 1, 1, tzinfo=UTC)
    expired = parse_license_payload({"expires_at": past.isoformat()})
    fresh = parse_license_payload({"expires_at": future.isoformat()})
    assert expired.is_expired() is True
    assert fresh.is_expired() is False


def test_no_expiry_means_never_expired() -> None:
    license_obj = parse_license_payload({"plan_id": "enterprise"})
    assert license_obj.is_expired() is False
    assert license_obj.expiring_soon() is False


def test_expiring_soon_window_is_30_days() -> None:
    now = datetime(2026, 5, 5, tzinfo=UTC)
    inside = now + timedelta(days=WARNING_WINDOW_DAYS - 1)
    outside = now + timedelta(days=WARNING_WINDOW_DAYS + 1)
    soon = parse_license_payload({"expires_at": inside.isoformat()})
    later = parse_license_payload({"expires_at": outside.isoformat()})
    assert soon.expiring_soon(now=now) is True
    assert later.expiring_soon(now=now) is False


def test_seats_max_coerces_positive_int() -> None:
    assert parse_license_payload({"seats_max": 25}).seats_max == 25
    assert parse_license_payload({"seats_max": -3}).seats_max is None
    assert parse_license_payload({"seats_max": "thirty"}).seats_max is None
    assert parse_license_payload({"seats_max": 12.5}).seats_max == 12


def test_load_yaml_license(tmp_path: Path) -> None:
    body = """
customer: Acme Bank
plan_id: enterprise
plan_overrides:
  sovereign_ai: true
seats_max: 25
"""
    path = tmp_path / "license.yaml"
    path.write_text(body)
    license_obj = load_license(path)
    assert license_obj is not None
    assert license_obj.customer == "Acme Bank"
    assert license_obj.plan_id == "enterprise"
    assert license_obj.plan_overrides == {"sovereign_ai": True}
    assert license_obj.seats_max == 25


def test_load_json_license(tmp_path: Path) -> None:
    payload = {"customer": "JSON Bank", "plan_id": "professional"}
    path = tmp_path / "license.json"
    path.write_text(json.dumps(payload))
    license_obj = load_license(path)
    assert license_obj is not None
    assert license_obj.customer == "JSON Bank"
    assert license_obj.plan_id == "professional"


def test_load_missing_file_returns_none(tmp_path: Path) -> None:
    assert load_license(tmp_path / "absent.yaml") is None


def test_load_malformed_yaml_returns_none(tmp_path: Path) -> None:
    path = tmp_path / "bad.yaml"
    path.write_text("customer: Acme\n  plan_id:")
    assert load_license(path) is None


def test_load_top_level_list_returns_none(tmp_path: Path) -> None:
    path = tmp_path / "list.yaml"
    path.write_text("- not\n- a mapping\n")
    assert load_license(path) is None


def test_summary_handles_none_license() -> None:
    assert license_summary(None) == {"licensed": False}


def test_summary_emits_expected_keys() -> None:
    license_obj = parse_license_payload(
        {
            "customer": "Acme",
            "plan_id": "enterprise",
            "issued_at": "2026-01-01T00:00:00Z",
            "expires_at": "2099-01-01T00:00:00Z",
            "seats_max": 50,
            "contact": {"primary": "ops@acme"},
        }
    )
    summary = license_summary(license_obj)
    assert summary["licensed"] is True
    assert summary["plan_id"] == "enterprise"
    assert summary["seats_max"] == 50
    assert summary["contact"] == {"primary": "ops@acme"}
    assert summary["is_expired"] is False
