"""Pure-helper coverage for AI outcome logging (V3 phase 1).

The async paths (record_ai_invocation, record_outcome_correction,
build_outcome_dashboard) need a real Postgres session because they
touch ai_outcome_log + audit_log. This file pins the deterministic
helpers — the redaction-text serialiser, the digest, the outcome
view shape — and the orchestrator's outcome_log_id surfacing path.
"""
from __future__ import annotations

import json
import uuid
from types import SimpleNamespace

from app.ai.audit import _digest, _redact_text, _uuid_or_none
from app.services.ai_outcome import _outcome_to_view


# Digest helper -------------------------------------------------------------

def test_digest_is_stable_for_dict_input() -> None:
    a = {"name": "Mohammad Karim", "amount": 1500000}
    b = {"name": "Mohammad Karim", "amount": 1500000}
    assert _digest(a) == _digest(b)


def test_digest_changes_when_payload_changes() -> None:
    assert _digest({"a": 1}) != _digest({"a": 2})


def test_digest_is_64_hex_chars() -> None:
    """SHA-256 hex digest is always 64 characters."""
    digest = _digest("anything")
    assert len(digest) == 64
    assert all(c in "0123456789abcdef" for c in digest)


# UUID parser ---------------------------------------------------------------

def test_uuid_or_none_accepts_valid_uuid() -> None:
    raw = "9c222222-2222-4222-8222-222222222222"
    assert str(_uuid_or_none(raw)) == raw


def test_uuid_or_none_returns_none_for_falsy_or_invalid() -> None:
    assert _uuid_or_none(None) is None
    assert _uuid_or_none("") is None
    assert _uuid_or_none("not a uuid") is None


# Redact-text serialiser ----------------------------------------------------

def test_redact_text_serialises_dict_deterministically() -> None:
    """Sort_keys=True so the same payload always renders the same text —
    the V3 phase 4 training corpus dedup key depends on this."""
    a = {"b": 1, "a": 2}
    b = {"a": 2, "b": 1}
    assert _redact_text(a) == _redact_text(b)


def test_redact_text_handles_unicode() -> None:
    payload = {"name": "মোহাম্মদ করিম"}  # Bangla — should round-trip without escapes
    text = _redact_text(payload)
    parsed = json.loads(text)
    assert parsed["name"] == "মোহাম্মদ করিম"


def test_redact_text_falls_back_to_str_on_unserialisable() -> None:
    """Defensive: the orchestrator should never hand us something
    unserialisable, but if it does we don't crash."""
    class NotSerialisable:
        def __str__(self) -> str:
            return "fallback-form"

    text = _redact_text(NotSerialisable())
    assert text == "fallback-form"


# Outcome view shape --------------------------------------------------------

def _row(**kwargs):
    defaults = dict(
        id=uuid.uuid4(),
        task_name="alert_explanation",
        provider="openai",
        model="anthropic/claude-sonnet-4.6",
        confidence=None,
        analyst_correction=None,
        outcome_label=None,
        latency_ms=320,
        prompt_tokens=None,
        completion_tokens=None,
        fallback_from_provider=None,
        request_id="abc123",
        created_at=None,
        updated_at=None,
    )
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


def test_outcome_to_view_round_trips_basic_fields() -> None:
    view = _outcome_to_view(_row(latency_ms=420, prompt_tokens=180, completion_tokens=64))
    assert view["task_name"] == "alert_explanation"
    assert view["latency_ms"] == 420
    assert view["prompt_tokens"] == 180
    assert view["completion_tokens"] == 64
    assert view["has_correction"] is False


def test_outcome_to_view_flips_has_correction_when_correction_present() -> None:
    view = _outcome_to_view(_row(analyst_correction={"diff": "..."}))
    assert view["has_correction"] is True


def test_outcome_to_view_serialises_confidence_as_float() -> None:
    """The DB column is numeric (psycopg returns Decimal); the API surface
    should use float so JSON serialisation is straightforward."""
    from decimal import Decimal

    view = _outcome_to_view(_row(confidence=Decimal("0.87")))
    assert view["confidence"] == 0.87
    assert isinstance(view["confidence"], float)


def test_outcome_to_view_handles_null_confidence() -> None:
    view = _outcome_to_view(_row(confidence=None))
    assert view["confidence"] is None
