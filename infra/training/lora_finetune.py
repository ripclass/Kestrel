"""LoRA fine-tune harness (V3 phase 4.2).

Modal-flavored scaffold. Loads a base model + corpus, trains a LoRA
adapter, writes the adapter + metrics. The actual training step is a
documented stub — see infra/training/README.md for why.

Real run cost (back-of-envelope, A100 80GB):
  * Llama 3.3 70B + LoRA rank 16 / alpha 32 / 3 epochs over a 1k-row
    corpus = ~5–6 GPU-hours.
  * Qwen 2.5 72B is similar.

Hyperparameters in ``LoRAConfig`` are set conservatively for the first
cycle. Tune after seeing eval_loss + perplexity on the held-out split.
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
import time
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger("infra.training.lora_finetune")


@dataclass(frozen=True, slots=True)
class LoRAConfig:
    rank: int = 16
    alpha: int = 32
    dropout: float = 0.05
    target_modules: tuple[str, ...] = ("q_proj", "k_proj", "v_proj", "o_proj")


@dataclass(frozen=True, slots=True)
class TrainingConfig:
    base_model: str
    corpus_path: Path
    output_dir: Path
    epochs: int = 3
    batch_size: int = 4
    gradient_accumulation_steps: int = 4
    learning_rate: float = 1e-4
    validation_fraction: float = 0.1
    max_seq_length: int = 4096
    seed: int = 7
    lora: LoRAConfig = LoRAConfig()


SUPPORTED_BASE_MODELS = {
    "meta-llama/Llama-3.3-70B-Instruct",
    "Qwen/Qwen2.5-72B-Instruct",
    "meta-llama/Llama-3.3-8B-Instruct",   # cheaper smoke-test option
    "Qwen/Qwen2.5-7B-Instruct",            # cheaper smoke-test option
}


def load_corpus(path: Path) -> list[dict[str, Any]]:
    """Load a corpus JSONL produced by export_training_corpus."""
    if not path.exists():
        raise FileNotFoundError(f"Corpus file not found: {path}")
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        rows.append(json.loads(line))
    return rows


def split_validation(rows: list[dict[str, Any]], fraction: float, seed: int) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Deterministic split. Used by the trainer + by V3 P5 quality gates
    (held-out evaluation reads from the same split)."""
    if fraction <= 0 or fraction >= 1:
        raise ValueError("validation fraction must be in (0, 1)")
    import random

    rng = random.Random(seed)
    shuffled = list(rows)
    rng.shuffle(shuffled)
    cutoff = max(1, int(len(shuffled) * (1 - fraction)))
    return shuffled[:cutoff], shuffled[cutoff:]


def write_metrics(output_dir: Path, metrics: dict[str, Any]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "metrics.json").write_text(
        json.dumps(metrics, indent=2, sort_keys=True, default=str),
        encoding="utf-8",
    )


def _build_prompt_and_target(row: dict[str, Any]) -> tuple[str, str]:
    """Assemble the (input, target) pair the trainer sees.

    The exporter wrote ``prompt`` (redacted, what the orchestrator
    handed to the provider) + ``expected_output`` (analyst correction or
    the original AI output if no correction was captured). The trainer
    learns to reproduce the expected output given the prompt."""
    prompt = row["prompt"]
    target_obj = row["expected_output"]
    if isinstance(target_obj, (dict, list)):
        target = json.dumps(target_obj, ensure_ascii=False, sort_keys=True)
    else:
        target = str(target_obj)
    return prompt, target


def train(config: TrainingConfig) -> dict[str, Any]:
    """Train a LoRA adapter and write outputs to ``config.output_dir``.

    **Stub for V3 P4.** Replace the inner block with a real
    transformers + peft training run when the corpus + GPU allocation
    are ready. See ``infra/training/README.md``."""
    if config.base_model not in SUPPORTED_BASE_MODELS:
        raise ValueError(
            f"base_model {config.base_model!r} not in SUPPORTED_BASE_MODELS — pick one from "
            f"{sorted(SUPPORTED_BASE_MODELS)}"
        )

    rows = load_corpus(config.corpus_path)
    train_rows, eval_rows = split_validation(rows, config.validation_fraction, config.seed)

    started = time.time()
    logger.info(
        "lora.train.start",
        extra={
            "base_model": config.base_model,
            "train_rows": len(train_rows),
            "eval_rows": len(eval_rows),
        },
    )

    # ------------------------------------------------------------------
    # ⚠️  V3 P4 stub. Real training plugs in here.
    #
    # When live, the body is roughly:
    #
    #   from transformers import AutoTokenizer, AutoModelForCausalLM, Trainer, TrainingArguments
    #   from peft import LoraConfig, get_peft_model, TaskType
    #   from datasets import Dataset
    #
    #   tok = AutoTokenizer.from_pretrained(config.base_model)
    #   model = AutoModelForCausalLM.from_pretrained(
    #       config.base_model, torch_dtype="auto", device_map="auto"
    #   )
    #   model = get_peft_model(model, LoraConfig(
    #       r=config.lora.rank, lora_alpha=config.lora.alpha,
    #       target_modules=list(config.lora.target_modules),
    #       lora_dropout=config.lora.dropout, task_type=TaskType.CAUSAL_LM,
    #   ))
    #   train_ds = Dataset.from_list([_to_chat_format(r, tok) for r in train_rows])
    #   eval_ds = Dataset.from_list([_to_chat_format(r, tok) for r in eval_rows])
    #   trainer = Trainer(
    #       model=model, tokenizer=tok,
    #       args=TrainingArguments(
    #           output_dir=str(config.output_dir),
    #           num_train_epochs=config.epochs,
    #           per_device_train_batch_size=config.batch_size,
    #           gradient_accumulation_steps=config.gradient_accumulation_steps,
    #           learning_rate=config.learning_rate,
    #           bf16=True, save_strategy="epoch", evaluation_strategy="epoch",
    #           seed=config.seed,
    #       ),
    #       train_dataset=train_ds, eval_dataset=eval_ds,
    #   )
    #   train_metrics = trainer.train()
    #   eval_metrics = trainer.evaluate()
    #   model.save_pretrained(config.output_dir)
    # ------------------------------------------------------------------
    raise NotImplementedError(
        "V3 P4 stub. The real LoRA fine-tune plugs into this function — see the "
        "block comment above and infra/training/README.md. Train when the "
        "ai_outcome_log corpus has accumulated >=1000 corrected rows."
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-model", required=True, choices=sorted(SUPPORTED_BASE_MODELS))
    parser.add_argument("--corpus", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--epochs", type=int, default=3)
    parser.add_argument("--batch-size", type=int, default=4)
    parser.add_argument("--learning-rate", type=float, default=1e-4)
    parser.add_argument("--validation-fraction", type=float, default=0.1)
    parser.add_argument("--seed", type=int, default=7)
    args = parser.parse_args()

    cfg = TrainingConfig(
        base_model=args.base_model,
        corpus_path=args.corpus,
        output_dir=args.output_dir,
        epochs=args.epochs,
        batch_size=args.batch_size,
        learning_rate=args.learning_rate,
        validation_fraction=args.validation_fraction,
        seed=args.seed,
    )
    started_at = datetime.now(UTC).isoformat()
    try:
        metrics = train(cfg)
        metrics = {**metrics, "completed_at": datetime.now(UTC).isoformat()}
    except NotImplementedError as exc:
        # Stub path — write a minimal metrics.json so downstream tooling
        # can verify the harness wires up cleanly.
        rows = load_corpus(cfg.corpus_path)
        train_rows, eval_rows = split_validation(rows, cfg.validation_fraction, cfg.seed)
        metrics = {
            "status": "stub",
            "stub_reason": str(exc),
            "base_model": cfg.base_model,
            "config": asdict(cfg),
            "corpus_rows": len(rows),
            "train_rows": len(train_rows),
            "eval_rows": len(eval_rows),
            "started_at": started_at,
        }
    write_metrics(cfg.output_dir, metrics)
    print(json.dumps(metrics, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
