"""Pure-helper coverage for the V3 phase 4.1 training corpus exporter.

The async fetch path needs a real Postgres session; this file pins the
deterministic helpers — pair construction, dedup behaviour, and JSONL
formatting.
"""
from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace

from scripts.export_training_corpus import (
    deduplicate_by_digest,
    to_training_pair,
    write_jsonl,
)


def _row(**kwargs):
    defaults = dict(
        id="00000000-0000-0000-0000-000000000001",
        prompt_redacted='{"subject_name":"X"}',
        prompt_digest="digest-1",
        output_json={"narrative": "ai draft"},
        analyst_correction={"narrative": "analyst edit"},
        task_name="str_narrative",
        outcome_label="edited",
        created_at=datetime(2026, 5, 5, tzinfo=UTC),
    )
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


# Pair construction --------------------------------------------------------

def test_to_training_pair_uses_correction_as_expected_output() -> None:
    pair = to_training_pair(_row())
    assert pair["expected_output"] == {"narrative": "analyst edit"}
    assert pair["ai_output"] == {"narrative": "ai draft"}
    assert pair["task_name"] == "str_narrative"
    assert pair["outcome_label"] == "edited"


def test_to_training_pair_falls_back_to_ai_output_when_no_correction() -> None:
    """When analyst_correction is None we still emit the row — the
    ai_output is the best available signal, and the trainer can filter
    on outcome_label if it wants corrections-only training."""
    pair = to_training_pair(_row(analyst_correction=None, outcome_label="accepted"))
    assert pair["expected_output"] == {"narrative": "ai draft"}


def test_to_training_pair_carries_metadata() -> None:
    pair = to_training_pair(_row())
    assert "prompt_digest" in pair
    assert "log_id" in pair
    assert pair["prompt"] == '{"subject_name":"X"}'


# Dedup --------------------------------------------------------------------

def test_deduplicate_keeps_most_recent_per_digest() -> None:
    older = to_training_pair(_row(created_at=datetime(2026, 5, 1, tzinfo=UTC)))
    newer = to_training_pair(
        _row(
            created_at=datetime(2026, 5, 5, tzinfo=UTC),
            analyst_correction={"narrative": "newer"},
        )
    )
    deduped = deduplicate_by_digest([older, newer])
    assert len(deduped) == 1
    assert deduped[0]["expected_output"] == {"narrative": "newer"}


def test_deduplicate_distinct_digests_keeps_both() -> None:
    a = to_training_pair(_row(prompt_digest="a"))
    b = to_training_pair(_row(prompt_digest="b"))
    deduped = deduplicate_by_digest([a, b])
    assert len(deduped) == 2


def test_deduplicate_skips_empty_digests() -> None:
    """Defence: a row without a digest can't be deduped; drop it."""
    empty = to_training_pair(_row(prompt_digest=""))
    assert deduplicate_by_digest([empty]) == []


def test_deduplicate_returns_sorted_output() -> None:
    """The exporter promises byte-deterministic output across runs."""
    a = to_training_pair(_row(prompt_digest="zzz"))
    b = to_training_pair(_row(prompt_digest="aaa"))
    deduped = deduplicate_by_digest([a, b])
    assert deduped[0]["prompt_digest"] == "aaa"
    assert deduped[1]["prompt_digest"] == "zzz"


def test_deduplicate_label_tiebreak() -> None:
    """When two rows share digest + timestamp, prefer the one with a
    populated outcome_label."""
    no_label = to_training_pair(_row(outcome_label=None))
    with_label = to_training_pair(_row(outcome_label="edited"))
    deduped = deduplicate_by_digest([no_label, with_label])
    assert deduped[0]["outcome_label"] == "edited"


# JSONL write --------------------------------------------------------------

def test_write_jsonl_round_trips(tmp_path: Path) -> None:
    rows = [
        {"a": 1, "b": [1, 2, 3]},
        {"a": 2, "b": "two"},
    ]
    out = tmp_path / "corpus.jsonl"
    write_jsonl(out, rows)
    lines = out.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 2
    assert json.loads(lines[0]) == {"a": 1, "b": [1, 2, 3]}
    assert json.loads(lines[1]) == {"a": 2, "b": "two"}


def test_write_jsonl_creates_parent_dirs(tmp_path: Path) -> None:
    out = tmp_path / "deep" / "nested" / "corpus.jsonl"
    write_jsonl(out, [{"x": 1}])
    assert out.exists()


def test_write_jsonl_sorts_keys_for_determinism(tmp_path: Path) -> None:
    """Stable byte output means re-runs produce the same file —
    important for resumable training."""
    out = tmp_path / "corpus.jsonl"
    write_jsonl(out, [{"b": 2, "a": 1}])
    line = out.read_text(encoding="utf-8").splitlines()[0]
    assert line == '{"a": 1, "b": 2}'
