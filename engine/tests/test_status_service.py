"""Pure-helper coverage for the status service (V2 phase 6.1).

The async paths (build_status_summary, post_incident, …) need a real
Postgres session because they touch uptime_pings + status_incidents.
This file pins the deterministic helpers — overall-status worst-of
aggregation, the uptime-ping status mapping used by the Beat task.
"""
from __future__ import annotations

from types import SimpleNamespace

from app.services.status import _component_status_label, _overall_status
from app.tasks.status_tasks import _component_for_check, _is_worse, _map_status


# Overall status worst-of -----------------------------------------------------

def test_overall_status_all_up_is_up() -> None:
    states = {c: "up" for c in ("auth", "database", "redis", "storage", "worker", "ai")}
    assert _overall_status(states) == "up"


def test_overall_status_any_down_is_down() -> None:
    states = {"auth": "up", "database": "down", "redis": "up", "storage": "up", "worker": "up", "ai": "up"}
    assert _overall_status(states) == "down"


def test_overall_status_degraded_when_any_degraded_no_down() -> None:
    states = {"auth": "up", "database": "degraded", "redis": "up", "storage": "up", "worker": "up", "ai": "up"}
    assert _overall_status(states) == "degraded"


def test_overall_status_down_dominates_degraded() -> None:
    """Down beats degraded when both are present."""
    states = {"auth": "down", "database": "degraded", "redis": "up", "storage": "up", "worker": "up", "ai": "up"}
    assert _overall_status(states) == "down"


def test_overall_status_unknown_only_is_degraded() -> None:
    """A cold start with only ``unknown`` pings reports degraded — we
    don't know if anything is up so we don't claim ``up``."""
    states = {c: "unknown" for c in ("auth", "database", "redis", "storage", "worker", "ai")}
    assert _overall_status(states) == "degraded"


# Component label helper ------------------------------------------------------

def test_component_status_label_with_no_ping_is_unknown() -> None:
    assert _component_status_label(None) == "unknown"


def test_component_status_label_returns_ping_status() -> None:
    ping = SimpleNamespace(status="up")
    assert _component_status_label(ping) == "up"


# Uptime Beat task helpers ---------------------------------------------------

def test_map_status_ok_to_up() -> None:
    assert _map_status("ok") == "up"


def test_map_status_skipped_treated_as_up() -> None:
    """`/ready` reports `skipped` for AI providers when probes are disabled
    but the provider IS configured. Treat as up."""
    assert _map_status("skipped") == "up"


def test_map_status_missing_config_is_unknown() -> None:
    assert _map_status("missing_config") == "unknown"


def test_map_status_degraded_passes_through() -> None:
    assert _map_status("degraded") == "degraded"


def test_map_status_other_is_down() -> None:
    assert _map_status("error") == "down"
    assert _map_status("failed") == "down"


# AI components collapse ----------------------------------------------------

def test_component_for_check_collapses_ai_subchecks() -> None:
    assert _component_for_check("ai:openai") == "ai"
    assert _component_for_check("ai:anthropic") == "ai"


def test_component_for_check_passes_others_through() -> None:
    assert _component_for_check("auth") == "auth"
    assert _component_for_check("database") == "database"


# Worst-of when multiple checks roll into one component --------------------

def test_is_worse_down_beats_degraded() -> None:
    assert _is_worse("down", "degraded") is True


def test_is_worse_degraded_beats_up() -> None:
    assert _is_worse("degraded", "up") is True


def test_is_worse_unknown_beats_up() -> None:
    """Don't paper over an unknown probe with a sibling's up signal."""
    assert _is_worse("unknown", "up") is True


def test_is_worse_up_does_not_beat_anything_else() -> None:
    assert _is_worse("up", "up") is False
    assert _is_worse("up", "degraded") is False
    assert _is_worse("up", "down") is False
