# Sovereign-AI training pipeline

V3 phase 4 of `KESTREL-V3-PROMPT.md`. This directory holds the scripts that turn a `corpus.jsonl` from `engine/scripts/export_training_corpus.py` into a deployable LoRA adapter.

## Pipeline

```
ai_outcome_log
    │
    │  python -m scripts.export_training_corpus --days 60 --out corpus.jsonl
    ▼
corpus.jsonl ─── (optional) ───► python -m scripts.generate_synthetic_corpus
    │                                    │
    │                                    ▼
    │                              synthetic.jsonl
    ▼                                    │
infra/training/lora_finetune.py ◄────────┘
    │
    ▼
adapter.safetensors + metrics.json
    │
    ▼
infra/training/promote_sovereign_adapter.py (V3 P5)
    │
    ▼
production rollout via TASK_ROLLOUT_PCT in app/ai/thresholds.py
```

## Prerequisites

- A Supabase service-role key (`SUPABASE_SERVICE_ROLE_KEY`) with read access to `ai_outcome_log` if you want to export from prod.
- A GPU runtime — Modal (preferred for v1 ergonomics) or RunPod. Pick one and stick with it.
- A base model. Two reasonable picks for V3 P4:
  - **Llama 3.3 70B Instruct** — strong general reasoning, decent multilingual.
  - **Qwen 2.5 72B Instruct** — better at structured output; verify Bangla support on a held-out set before committing.

## v1 status

`lora_finetune.py` is a **scaffold**. The argparse + Modal app wrapper + LoRA hyperparameter defaults are real; the actual training step is a documented stub (`raise NotImplementedError`) because:

1. The `ai_outcome_log` corpus needs ~30–60 days of analyst corrections to be meaningful. V3 P4 ships well before that.
2. Running a real LoRA fine-tune is a 4–8 hour A100/H100 job that can't be triggered from a code-review session.

When the corpus has enough rows, replace the stub with a real `peft.get_peft_model` + `Trainer.train` call. Hyperparameters in `LoRAConfig` are set conservatively for first-cycle stability.

## Running the (eventual) real cycle

```bash
# Export the corpus (run from the engine/ directory)
cd engine && python -m scripts.export_training_corpus --days 60 --out /tmp/corpus.jsonl

# (optional) augment with synthetic data
python -m scripts.generate_synthetic_corpus --count 50 --out /tmp/synthetic.jsonl
cat /tmp/synthetic.jsonl >> /tmp/corpus.jsonl

# Run training on Modal
modal run infra/training/lora_finetune.py::train \
  --base-model meta-llama/Llama-3.3-70B-Instruct \
  --corpus /tmp/corpus.jsonl \
  --output-dir /tmp/kestrel-sovereign-v1
```

## Outputs

`metrics.json`:
```json
{
  "base_model": "meta-llama/Llama-3.3-70B-Instruct",
  "corpus_rows": 1247,
  "validation_rows": 124,
  "epochs": 3,
  "train_loss": 1.42,
  "eval_loss": 1.61,
  "perplexity": 5.04,
  "samples_seen": 3741,
  "duration_seconds": 18420,
  "gpu_hours": 5.12,
  "completed_at": "..."
}
```

The V3 P5 promotion harness reads this file alongside the held-out evaluation set + red-team corpus to decide whether to ship the adapter.
