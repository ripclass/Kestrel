"""Training corpus exporter (V3 phase 4.1).

Pulls ai_outcome_log rows over the last N days where
``analyst_correction IS NOT NULL`` and writes them to JSONL — one
training pair per row, deduplicated by ``prompt_digest``. The V3 P4
LoRA fine-tune harness consumes this file directly.

Usage:
    python -m scripts.export_training_corpus --days 60 --out training/corpus.jsonl
    python -m scripts.export_training_corpus --days 60 --upload --month-tag v3-month-3

Storage path on `--upload`: ``training/{month_tag}/corpus.jsonl`` in the
``kestrel-exports`` Supabase Storage bucket.

Output format (one JSON object per line):
    {
      "prompt": "<redacted prompt as the orchestrator saw it>",
      "expected_output": <the analyst-corrected JSON>,
      "ai_output": <the AI's original JSON>,
      "task_name": "alert_explanation",
      "outcome_label": "edited",
      "prompt_digest": "<sha256>",
      "log_id": "<uuid>",
      "created_at": "<iso8601>"
    }

Determinism: rows are emitted in (prompt_digest, created_at) order so
the corpus is byte-identical across runs as long as the underlying data
hasn't changed. The fine-tune harness uses this for resumable training.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

# Make the engine root importable when running as a CLI script.
_ENGINE_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ENGINE_ROOT not in sys.path:
    sys.path.insert(0, _ENGINE_ROOT)

import httpx  # noqa: E402
from sqlalchemy import select  # noqa: E402

from app.config import get_settings  # noqa: E402
from app.database import SessionLocal  # noqa: E402
from app.models.ai_outcome import AIOutcomeLog  # noqa: E402

logger = logging.getLogger("scripts.export_training_corpus")

DEFAULT_DAYS = 60
DEFAULT_OUT = Path("training/corpus.jsonl")
TRAINING_BUCKET = "kestrel-exports"


def to_training_pair(row: AIOutcomeLog) -> dict[str, Any]:
    """Render a single ai_outcome_log row as a training pair.

    The model trains to produce ``expected_output`` given ``prompt``;
    we keep ``ai_output`` alongside so the trainer can compute a
    correction-distance signal during evaluation.
    """
    expected = row.analyst_correction if row.analyst_correction else row.output_json
    return {
        "prompt": row.prompt_redacted,
        "expected_output": expected,
        "ai_output": row.output_json,
        "task_name": row.task_name,
        "outcome_label": row.outcome_label,
        "prompt_digest": row.prompt_digest,
        "log_id": str(row.id),
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }


def deduplicate_by_digest(pairs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Keep only the most recent training pair per ``prompt_digest``.

    A repeated prompt is still useful as a training signal but exposing
    the same input twice biases the gradient. We pick the most recent
    correction (reflects the analyst's latest opinion)."""
    seen: dict[str, dict[str, Any]] = {}
    for pair in pairs:
        digest = pair.get("prompt_digest")
        if not digest:
            continue
        existing = seen.get(digest)
        if existing is None:
            seen[digest] = pair
            continue
        # Keep whichever has the later created_at; ties break in favour
        # of the row with a populated outcome_label.
        a = pair.get("created_at") or ""
        b = existing.get("created_at") or ""
        if a > b or (a == b and pair.get("outcome_label") and not existing.get("outcome_label")):
            seen[digest] = pair
    return sorted(seen.values(), key=lambda p: (p.get("prompt_digest") or "", p.get("created_at") or ""))


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row, ensure_ascii=False, sort_keys=True))
            fh.write("\n")


async def fetch_corrected_rows(*, days: int) -> list[AIOutcomeLog]:
    cutoff = datetime.now(UTC) - timedelta(days=max(1, int(days)))
    async with SessionLocal() as session:
        result = await session.execute(
            select(AIOutcomeLog)
            .where(AIOutcomeLog.analyst_correction.is_not(None))
            .where(AIOutcomeLog.created_at >= cutoff)
            .order_by(AIOutcomeLog.created_at.asc())
        )
        return list(result.scalars().all())


async def upload_to_storage(path: str, content: bytes) -> str:
    settings = get_settings()
    if not settings.supabase_url or not settings.supabase_service_role_key:
        raise RuntimeError("Supabase storage is not configured.")
    url = f"{settings.supabase_url.rstrip('/')}/storage/v1/object/{TRAINING_BUCKET}/{path.lstrip('/')}"
    headers = {
        "apikey": settings.supabase_service_role_key,
        "Authorization": f"Bearer {settings.supabase_service_role_key}",
        "Content-Type": "application/x-ndjson",
        "x-upsert": "true",
    }
    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.put(url, content=content, headers=headers)
    if response.status_code >= 400:
        raise RuntimeError(
            f"Supabase Storage upload failed ({response.status_code}): {response.text[:200]}"
        )
    return f"{TRAINING_BUCKET}/{path.lstrip('/')}"


async def export(
    *,
    days: int,
    out_path: Path,
    upload: bool,
    month_tag: str | None,
) -> dict[str, Any]:
    rows = await fetch_corrected_rows(days=days)
    pairs = [to_training_pair(r) for r in rows]
    deduped = deduplicate_by_digest(pairs)

    write_jsonl(out_path, deduped)
    summary = {
        "rows_fetched": len(pairs),
        "rows_after_dedup": len(deduped),
        "out_path": str(out_path),
        "window_days": days,
    }
    if upload:
        if not month_tag:
            month_tag = f"v3-{datetime.now(UTC).strftime('%Y-%m')}"
        with out_path.open("rb") as fh:
            content = fh.read()
        storage_path = f"training/{month_tag}/corpus.jsonl"
        location = await upload_to_storage(storage_path, content)
        summary["uploaded_to"] = location
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--days", type=int, default=DEFAULT_DAYS, help="Window in days (default 60)")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT, help="Output JSONL path (default training/corpus.jsonl)")
    parser.add_argument("--upload", action="store_true", help="Push the corpus to Supabase Storage as well")
    parser.add_argument("--month-tag", help="Storage subdir under training/ (default v3-YYYY-MM)")
    args = parser.parse_args()

    summary = asyncio.run(
        export(
            days=args.days,
            out_path=args.out,
            upload=args.upload,
            month_tag=args.month_tag,
        )
    )
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
