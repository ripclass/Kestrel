"""V3 P7.1 — Stripe billing pure helpers + signature verification."""
from __future__ import annotations

import hashlib
import hmac
import time
from datetime import UTC, datetime, timedelta

from app.services.stripe_billing import (
    GRACE_PERIOD_DAYS,
    SIGNATURE_TOLERANCE_SECONDS,
    SignatureCheck,
    default_price_to_plan,
    evaluate_grace_expiry,
    resolve_plan_for_price,
    verify_signature,
)


# --- Price → plan mapping --------------------------------------------------


def test_default_price_to_plan_filters_unset() -> None:
    mapping = default_price_to_plan(starter=None, professional="price_pro", enterprise=None)
    assert mapping == {"price_pro": "professional"}


def test_default_price_to_plan_complete() -> None:
    mapping = default_price_to_plan(
        starter="price_s", professional="price_p", enterprise="price_e"
    )
    assert mapping == {
        "price_s": "starter",
        "price_p": "professional",
        "price_e": "enterprise",
    }


def test_resolve_plan_for_known_price() -> None:
    mapping = {"price_pro": "professional"}
    assert resolve_plan_for_price("price_pro", mapping) == "professional"


def test_resolve_plan_for_unknown_price_falls_back_to_starter() -> None:
    assert resolve_plan_for_price("price_unknown", {}) == "starter"


def test_resolve_plan_falls_back_when_mapping_value_is_invalid() -> None:
    """A mapping pointing at a non-existent plan_id (e.g. typo'd 'platinum')
    must collapse to starter so the engine never enables a feature bundle
    that doesn't exist."""
    assert resolve_plan_for_price("price_x", {"price_x": "platinum"}) == "starter"


# --- Signature verification ------------------------------------------------


def _stripe_signature(*, payload: bytes, secret: str, timestamp: int) -> str:
    digest = hmac.new(
        secret.encode("utf-8"),
        msg=f"{timestamp}.".encode() + payload,
        digestmod=hashlib.sha256,
    ).hexdigest()
    return f"t={timestamp},v1={digest}"


def test_signature_valid_round_trips() -> None:
    secret = "whsec_test"
    payload = b'{"type":"customer.subscription.created"}'
    now = int(time.time())
    header = _stripe_signature(payload=payload, secret=secret, timestamp=now)
    check = verify_signature(payload=payload, header=header, secret=secret, now=float(now))
    assert isinstance(check, SignatureCheck)
    assert check.valid is True
    assert check.reason is None


def test_signature_rejects_when_secret_missing() -> None:
    check = verify_signature(payload=b"{}", header="t=1,v1=abc", secret=None)
    assert check.valid is False
    assert check.reason == "webhook_secret_not_configured"


def test_signature_rejects_when_header_missing() -> None:
    check = verify_signature(payload=b"{}", header=None, secret="s")
    assert check.valid is False
    assert check.reason == "signature_header_missing"


def test_signature_rejects_outside_tolerance() -> None:
    secret = "whsec_test"
    payload = b"{}"
    old = int(time.time()) - SIGNATURE_TOLERANCE_SECONDS - 60
    header = _stripe_signature(payload=payload, secret=secret, timestamp=old)
    check = verify_signature(payload=payload, header=header, secret=secret)
    assert check.valid is False
    assert check.reason == "timestamp_outside_tolerance"


def test_signature_rejects_malformed_timestamp() -> None:
    check = verify_signature(payload=b"{}", header="t=notanint,v1=abc", secret="s")
    assert check.valid is False
    assert check.reason == "timestamp_malformed"


def test_signature_rejects_when_no_v1_present() -> None:
    check = verify_signature(payload=b"{}", header=f"t={int(time.time())}", secret="s")
    assert check.valid is False
    assert check.reason == "no_v1_signature"


def test_signature_rejects_mismatched_digest() -> None:
    now = int(time.time())
    check = verify_signature(
        payload=b'{"x":1}',
        header=f"t={now},v1=deadbeef",
        secret="whsec_real",
        now=float(now),
    )
    assert check.valid is False
    assert check.reason == "signature_mismatch"


# --- Grace expiry evaluator ------------------------------------------------


def test_grace_window_constant_is_seven_days() -> None:
    assert GRACE_PERIOD_DAYS == 7


def test_grace_with_no_window_keeps_plan() -> None:
    assert (
        evaluate_grace_expiry(plan_id="professional", subscription_status="active", grace_until=None)
        == "professional"
    )


def test_grace_with_open_window_keeps_plan() -> None:
    future = datetime.now(UTC) + timedelta(hours=1)
    assert (
        evaluate_grace_expiry(
            plan_id="professional",
            subscription_status="past_due",
            grace_until=future,
        )
        == "professional"
    )


def test_grace_with_expired_window_downgrades_to_starter() -> None:
    past = datetime.now(UTC) - timedelta(hours=1)
    assert (
        evaluate_grace_expiry(
            plan_id="professional",
            subscription_status="past_due",
            grace_until=past,
        )
        == "starter"
    )


def test_grace_with_active_subscription_keeps_plan_even_after_window() -> None:
    """A late-arriving payment_succeeded event clears the grace; if the
    subscription is back to active we don't downgrade even though the
    timer has elapsed (timer + status need to AGREE on degradation)."""
    past = datetime.now(UTC) - timedelta(hours=1)
    assert (
        evaluate_grace_expiry(
            plan_id="enterprise",
            subscription_status="active",
            grace_until=past,
        )
        == "enterprise"
    )


def test_grace_pinned_constants() -> None:
    """If someone tweaks the grace window quietly, the test suite catches
    it. A 7-day window is the procurement-facing commitment."""
    assert GRACE_PERIOD_DAYS == 7
    assert SIGNATURE_TOLERANCE_SECONDS == 300


def test_signature_rejects_future_timestamp_outside_tolerance() -> None:
    # A far-future timestamp must fail too — otherwise a captured
    # signature with a forged future `t` stays replayable indefinitely.
    payload = b'{"id": "evt_future"}'
    secret = "whsec_future"
    future = int(time.time()) + SIGNATURE_TOLERANCE_SECONDS + 60
    header = _stripe_signature(payload=payload, secret=secret, timestamp=future)
    check = verify_signature(payload=payload, header=header, secret=secret)
    assert check.valid is False
    assert check.reason == "timestamp_outside_tolerance"
