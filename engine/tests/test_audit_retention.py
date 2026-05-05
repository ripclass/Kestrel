"""V3 P7.3 — audit-log retention helpers."""
from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from types import SimpleNamespace

from app.tasks.retention_tasks import (
    BATCH_SIZE,
    MAX_BATCHES_PER_RUN,
    archive_key_for,
    serialize_batch,
)


def _row(id_: uuid.UUID | str, *, action: str, org_id: str | None = None) -> SimpleNamespace:
    """Tiny stand-in for AuditLog so tests don't need a Postgres."""
    return SimpleNamespace(
        id=id_,
        org_id=org_id,
        actor_user_id=None,
        action=action,
        details={"foo": "bar"},
        resource_id=None,
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
    )


def test_serialize_batch_is_deterministic() -> None:
    a = _row(uuid.UUID("00000000-0000-0000-0000-000000000001"), action="case.create")
    b = _row(uuid.UUID("00000000-0000-0000-0000-000000000002"), action="str.submit")
    one = serialize_batch([a, b])
    two = serialize_batch([b, a])  # different order in
    assert one == two  # output order is canonical


def test_serialize_batch_is_jsonl() -> None:
    rows = [
        _row(uuid.UUID("00000000-0000-0000-0000-000000000001"), action="x"),
        _row(uuid.UUID("00000000-0000-0000-0000-000000000002"), action="y"),
    ]
    out = serialize_batch(rows).decode("utf-8")
    lines = [ln for ln in out.split("\n") if ln]
    assert len(lines) == 2
    parsed = [json.loads(ln) for ln in lines]
    assert parsed[0]["action"] == "x"
    assert parsed[1]["action"] == "y"


def test_serialize_batch_handles_empty() -> None:
    assert serialize_batch([]) == b""


def test_archive_key_uses_yyyy_mm_prefix() -> None:
    period = datetime(2026, 5, 15, tzinfo=UTC)
    key = archive_key_for(period=period, batch_id=uuid.UUID("00000000-0000-0000-0000-000000000001"))
    assert key == "audit-archive/2026-05/00000000-0000-0000-0000-000000000001.jsonl"


def test_archive_key_january() -> None:
    period = datetime(2026, 1, 1, tzinfo=UTC)
    key = archive_key_for(period=period, batch_id=uuid.UUID("00000000-0000-0000-0000-00000000abcd"))
    assert key.startswith("audit-archive/2026-01/")


def test_archive_key_random_id_format() -> None:
    period = datetime(2026, 5, 1, tzinfo=UTC)
    key = archive_key_for(period=period)
    assert key.startswith("audit-archive/2026-05/")
    assert key.endswith(".jsonl")
    parts = key.split("/")
    # uuid is the basename minus extension
    uuid.UUID(parts[-1].removesuffix(".jsonl"))


def test_pinned_constants_are_load_bounded() -> None:
    """Procurement-facing: archive runs aren't allowed to chew through
    the entire audit_log in one go. 500 rows × 40 batches = 20k rows max."""
    assert BATCH_SIZE == 500
    assert MAX_BATCHES_PER_RUN == 40
