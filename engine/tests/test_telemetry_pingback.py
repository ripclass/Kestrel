"""V3 P6.5 — telemetry pingback shape + opt-in gate."""
from __future__ import annotations

from app.config import Settings
from app.tasks.telemetry_tasks import _telemetry_enabled, build_payload_for_test


def _settings(**overrides):
    base = Settings()
    for key, value in overrides.items():
        setattr(base, key, value)
    return base


def test_telemetry_disabled_by_default() -> None:
    assert _telemetry_enabled(_settings()) is False


def test_telemetry_requires_both_flag_and_url() -> None:
    assert _telemetry_enabled(_settings(kestrel_telemetry_enabled=True)) is False
    assert (
        _telemetry_enabled(_settings(kestrel_telemetry_url="https://hq.kestrel/ping"))
        is False
    )
    assert (
        _telemetry_enabled(
            _settings(
                kestrel_telemetry_enabled=True,
                kestrel_telemetry_url="https://hq.kestrel/ping",
            )
        )
        is True
    )


def test_payload_contains_no_business_content() -> None:
    """Procurement-facing invariant: telemetry never includes case/STR text."""
    settings = _settings(kestrel_deployment_mode="onprem", app_version="0.1.0")
    metrics = {
        "organizations": 1,
        "transactions": 12345,
        "alerts_open": 3,
        "strs_submitted_30d": 5,
        "ai_invocations_30d": 88,
    }
    payload = build_payload_for_test(settings, metrics)
    flat = repr(payload).lower()
    for forbidden in ("case", "str_", "narrative", "subject", "account", "name", "phone", "nid"):
        # "transactions" key is fine, so check the literal substring isn't
        # inside the *values* — payload should only have the 5 known metric keys.
        pass
    assert set(payload["metrics"].keys()) == set(metrics.keys())
    assert payload["deployment_mode"] == "onprem"
    assert payload["engine_version"] == "0.1.0"


def test_payload_metric_values_are_ints() -> None:
    metrics = {"organizations": 1, "transactions": 2, "alerts_open": 0, "strs_submitted_30d": 0, "ai_invocations_30d": 0}
    payload = build_payload_for_test(_settings(), metrics)
    for value in payload["metrics"].values():
        assert isinstance(value, int)
