"""Synthetic training corpus generator (V3 phase 4.3).

The ``analyst_correction``-only corpus from
``scripts.export_training_corpus`` will be small at first — V3 P4 may
have only tens of corrections in the first month. To bootstrap the
sovereign model, augment with Claude-generated synthetic pairs covering
the task surface.

Output is structured the same as the live-correction corpus so the LoRA
harness consumes both paths identically. A separate file path keeps
quality gates honest — we want to compare adapters trained on
``corrections only`` vs ``corrections + synthetic`` to know what the
analyst signal is actually worth.

Usage:
    python -m scripts.generate_synthetic_corpus \\
        --count 50 \\
        --tasks str_narrative,alert_explanation \\
        --out training/synthetic.jsonl

Each row's ``outcome_label`` is set to ``"synthetic"`` (a non-validated
label that the trainer can filter on if it wants corrections-only
training during quality-gate evaluation).
"""
from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path
from typing import Any

# Make the engine root importable when running as a CLI script.
_ENGINE_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ENGINE_ROOT not in sys.path:
    sys.path.insert(0, _ENGINE_ROOT)

from app.ai.types import AITaskName  # noqa: E402

logger = logging.getLogger("scripts.generate_synthetic_corpus")


@dataclass(frozen=True, slots=True)
class _SyntheticSeed:
    """Deterministic seed input + expected-shape sketch per task. The
    Claude generator expands these into full training pairs."""

    task: AITaskName
    description: str
    seed_inputs: tuple[dict[str, Any], ...]


# Hand-curated seeds covering the AI task surface. The generator combines
# each seed with a Claude call asking for ``count`` synthetic variants.
SEEDS: list[_SyntheticSeed] = [
    _SyntheticSeed(
        task=AITaskName.STR_NARRATIVE,
        description="Bangladesh-anchored STR narrative drafts from structured facts.",
        seed_inputs=(
            {
                "subject_name": "Mohammad Karim",
                "subject_account": "1234567890123",
                "total_amount": 1750000,
                "category": "fraud",
                "trigger_facts": [
                    "Rapid cashout: 92% debited within 38 minutes",
                    "Cross-bank match across 3 institutions",
                ],
            },
            {
                "subject_name": "Asma Begum",
                "total_amount": 9_000_000,
                "category": "tbml",
                "trigger_facts": [
                    "First-time high-value transfer of BDT 90 lakh from a 12-day-old account",
                    "Beneficiary in adverse-media watchlist",
                ],
            },
        ),
    ),
    _SyntheticSeed(
        task=AITaskName.ALERT_EXPLANATION,
        description="Analyst-ready alert explanations from rule-hit reasons.",
        seed_inputs=(
            {
                "title": "Rapid cashout: ACCT-887331",
                "description": "92% of credit debited within 38 minutes",
                "reasons": [
                    {"rule": "rapid_cashout", "score": 88, "weight": 8.0},
                    {"rule": "first_time_high_value", "score": 65, "weight": 6.0},
                ],
            },
        ),
    ),
    _SyntheticSeed(
        task=AITaskName.ENTITY_EXTRACTION,
        description="Extract financially-relevant entities from raw text.",
        seed_inputs=(
            {
                "raw_text": (
                    "Subject Mohammad Karim (NID 1979314001234) operates account 1234567890123 "
                    "and bKash wallet 01711-555-001 across BRAC and Sonali."
                ),
            },
        ),
    ),
    _SyntheticSeed(
        task=AITaskName.TYPOLOGY_SUGGESTION,
        description="Identify the most likely typology from observed signals.",
        seed_inputs=(
            {
                "indicators": [
                    "Rapid cashout",
                    "Multiple NPSB hops",
                    "Beneficiary at different bank",
                    "First-time large beneficiary",
                ],
            },
        ),
    ),
    _SyntheticSeed(
        task=AITaskName.CASE_SUMMARY,
        description="Executive case summaries for investigators + leadership.",
        seed_inputs=(
            {
                "id": "KST-2605-00041",
                "title": "Cross-bank cashout ring",
                "summary": "5-bank cluster with shared beneficial owner",
                "severity": "high",
                "status": "open",
                "linked_entity_ids": ["e1", "e2", "e3", "e4", "e5"],
                "timeline": [],
                "notes": [
                    {"author": "analyst", "note": "Subject flagged at 4 institutions"},
                ],
            },
        ),
    ),
    _SyntheticSeed(
        task=AITaskName.EXECUTIVE_BRIEFING,
        description="Cautious factual executive briefing for FIU leadership.",
        seed_inputs=(
            {
                "headline_seed": "Cross-bank cashout activity surging in Q2",
                "summary_seed": "12 cases opened in the last 7 days; 4 institutions involved",
                "priorities": ["Wallet ring takedown", "Trade-based laundering review"],
                "risk_watchlist": ["Riverbend Trading", "Galaxy Trade House"],
            },
        ),
    ),
]


def _digest(payload: object) -> str:
    return sha256(
        json.dumps(payload, sort_keys=True, ensure_ascii=True).encode("utf-8")
    ).hexdigest()


async def generate_for_task(
    *,
    seed: _SyntheticSeed,
    count: int,
) -> list[dict[str, Any]]:
    """Run the AI orchestrator over each seed input and collect the
    structured outputs as synthetic training pairs.

    Imports are lazy so the script can be inspected by the test suite
    without dragging the AIOrchestrator's heavy dependencies (asyncpg,
    httpx, pydantic-settings) into the import path."""
    from app.ai.service import AIInvocationError, AIOrchestrator
    from app.auth import AuthenticatedUser
    from app.schemas.ai import (
        AlertExplanationResult,
        CaseSummaryResult,
        EntityExtractionResult,
        ExecutiveBriefingResult,
        STRNarrativeResult,
        TypologySuggestionResult,
    )

    output_models: dict[AITaskName, type] = {
        AITaskName.STR_NARRATIVE: STRNarrativeResult,
        AITaskName.ALERT_EXPLANATION: AlertExplanationResult,
        AITaskName.ENTITY_EXTRACTION: EntityExtractionResult,
        AITaskName.TYPOLOGY_SUGGESTION: TypologySuggestionResult,
        AITaskName.CASE_SUMMARY: CaseSummaryResult,
        AITaskName.EXECUTIVE_BRIEFING: ExecutiveBriefingResult,
    }
    output_model = output_models.get(seed.task)
    if output_model is None:
        return []

    orchestrator = AIOrchestrator()
    user = AuthenticatedUser(
        user_id="synthetic-generator",
        email="synthetic@kestrel.local",
        org_id="00000000-0000-0000-0000-000000000000",
        org_type="regulator",
        role="superadmin",
        persona="bfiu_director",
        designation="Synthetic Generator",
    )

    pairs: list[dict[str, Any]] = []
    per_seed = max(1, count // max(1, len(seed.seed_inputs)))
    for input_payload in seed.seed_inputs:
        for _ in range(per_seed):
            try:
                result = await orchestrator.invoke(
                    task=seed.task,
                    payload=input_payload,
                    output_model=output_model,
                    user=user,
                )
            except AIInvocationError as exc:
                logger.warning("synthetic.invoke_failed", extra={"task": str(seed.task), "error": str(exc)})
                continue
            output_payload = result.output.model_dump()
            prompt_text = json.dumps(input_payload, ensure_ascii=False, sort_keys=True)
            pairs.append(
                {
                    "prompt": prompt_text,
                    "expected_output": output_payload,
                    "ai_output": output_payload,
                    "task_name": str(seed.task),
                    "outcome_label": "synthetic",
                    "prompt_digest": _digest(input_payload),
                    "log_id": None,
                    "created_at": datetime.now(UTC).isoformat(),
                }
            )
    return pairs


async def generate(
    *,
    count: int,
    tasks: list[AITaskName] | None,
    out_path: Path,
) -> dict[str, Any]:
    selected = [s for s in SEEDS if (tasks is None or s.task in set(tasks))]
    all_pairs: list[dict[str, Any]] = []
    for seed in selected:
        pairs = await generate_for_task(seed=seed, count=count)
        all_pairs.extend(pairs)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as fh:
        for row in all_pairs:
            fh.write(json.dumps(row, ensure_ascii=False, sort_keys=True))
            fh.write("\n")

    return {
        "tasks_covered": [str(s.task) for s in selected],
        "rows_written": len(all_pairs),
        "out_path": str(out_path),
    }


def parse_tasks(raw: str | None) -> list[AITaskName] | None:
    if not raw:
        return None
    parsed: list[AITaskName] = []
    for token in raw.split(","):
        token = token.strip()
        if not token:
            continue
        try:
            parsed.append(AITaskName(token))
        except ValueError:
            logger.warning("synthetic.unknown_task", extra={"token": token})
    return parsed or None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--count", type=int, default=20, help="Approx pairs per task (default 20)")
    parser.add_argument(
        "--tasks",
        help="Comma-separated AITaskName values to generate for (default: all)",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("training/synthetic.jsonl"),
        help="Output JSONL path",
    )
    args = parser.parse_args()

    summary = asyncio.run(
        generate(
            count=args.count,
            tasks=parse_tasks(args.tasks),
            out_path=args.out,
        )
    )
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
