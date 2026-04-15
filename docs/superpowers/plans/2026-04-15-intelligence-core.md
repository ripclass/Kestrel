# Kestrel Intelligence Core Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the stubbed intelligence core (resolver, matcher, evaluator, scorer, pipeline, rule YAMLs) with real detection logic that produces explainable alerts and cross-bank matches from the DBBL synthetic dataset, delivered on a feature branch and merged to main only after end-to-end verification.

**Architecture:** Three layers. (1) YAML rule definitions declare condition triggers, scoring modifiers, severity bands, and alert templates. (2) Pure-Python evaluators — one function per rule — operate on account-grouped SQLAlchemy `Transaction` objects and return `RuleHit` dataclasses. (3) Async pipeline orchestrators (`run_str_pipeline`, `run_scan_pipeline`) chain resolver → matcher → evaluator → scorer → alert creation. Detection runs synchronously on the request path — no Celery yet, keeping the demo path simple. Unit tests use fake transaction objects; end-to-end verification uses the existing DBBL synthetic seeder.

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy 2 async + asyncpg, PyYAML, networkx, Pydantic v2, pytest, pytest-asyncio. No new dependencies.

**Domain glossary (for subagents with zero context):**
- **STR** — Suspicious Transaction Report. Native BFIU/goAML report type banks file when they suspect money laundering.
- **BFIU** — Bangladesh Financial Intelligence Unit. The regulator. Kestrel's primary persona is a BFIU analyst.
- **CAMLCO** — Chief Anti-Money Laundering Compliance Officer. Bank-side persona.
- **NPSB** — National Payment Switch Bangladesh. Inter-bank transfer rail.
- **Cross-bank match** — the same identifier (account, phone, wallet, NID) appears on STRs from two or more different banks. This is the "wow moment" for the demo — banks don't see each other's STRs today.
- **Entity** — a canonical shared-intelligence record identified by `(entity_type, canonical_value)` — e.g., `(account, "1781430000701")`. Entities are shared across all orgs via RLS; STRs are per-org.
- **Rule hit** — a single rule triggering against a single account. One account can have multiple rule hits (e.g., rapid_cashout + proximity_to_bad). Hits are combined by the scorer into a final risk score.
- **DBBL synthetic** — the curated, sanitized dataset in `engine/seed/generated/dbbl_synthetic/` loaded into Supabase via `POST /admin/synthetic-backfill`. This is the only realistic data we have and is the ground truth for end-to-end verification.

---

## File Structure

| Path | Action | Responsibility |
|------|--------|----------------|
| `engine/app/core/detection/rules/rapid_cashout.yaml` | Rewrite | Declarative config for rapid cash-out rule |
| `engine/app/core/detection/rules/fan_in_burst.yaml` | Rewrite | Declarative config for fan-in burst rule |
| `engine/app/core/detection/rules/fan_out_burst.yaml` | Rewrite | Declarative config for fan-out burst rule |
| `engine/app/core/detection/rules/dormant_spike.yaml` | Rewrite | Declarative config for dormant spike rule |
| `engine/app/core/detection/rules/layering.yaml` | Rewrite | Declarative config for layering rule |
| `engine/app/core/detection/rules/proximity_to_bad.yaml` | Rewrite | Declarative config for proximity-to-flagged rule |
| `engine/app/core/detection/rules/structuring.yaml` | Rewrite | Declarative config for structuring (CTR avoidance) rule |
| `engine/app/core/detection/rules/first_time_high_value.yaml` | Rewrite | Declarative config for first-time high-value transfer rule |
| `engine/app/core/detection/loader.py` | Modify | Parse new YAML schema into `RuleDefinition` dicts |
| `engine/app/core/detection/rule_hit.py` | Create | `RuleHit` dataclass returned by every evaluator |
| `engine/app/core/detection/evaluator.py` | Rewrite | Per-rule evaluator functions + `evaluate_accounts` entry point |
| `engine/app/core/detection/scorer.py` | Rewrite | `calculate_risk_score` — combines weighted hits into final score |
| `engine/app/core/resolver.py` | Rewrite | Normalize identifiers, find/create entities, fuzzy-match on display_name, link entities via connections |
| `engine/app/core/matcher.py` | Rewrite | Detect cross-bank matches, upsert `matches` rows, emit cross-bank alerts |
| `engine/app/core/pipeline.py` | Rewrite | `run_str_pipeline` (STR submission) and `run_scan_pipeline` (scan run) |
| `engine/app/services/str_reports.py` | Modify | Call `run_str_pipeline` from `submit_str_report` |
| `engine/app/services/scanning.py` | Modify | Call `run_scan_pipeline` from `queue_run` |
| `engine/tests/test_rules_loader_core.py` | Create | Validate new YAML schema and loader output |
| `engine/tests/test_resolver_core.py` | Create | Unit tests for normalization + resolver helpers |
| `engine/tests/test_evaluator_core.py` | Create | Unit tests for each rule evaluator |
| `engine/tests/test_matcher_core.py` | Create | Unit tests for cross-bank matcher |
| `engine/tests/test_scorer_core.py` | Create | Unit tests for scorer |
| `engine/tests/test_pipeline_core.py` | Create | Pipeline orchestration smoke tests |

**Files intentionally NOT touched:**
- `engine/app/core/alerter.py` — legacy fixture stub. The new pipeline writes `Alert` rows directly. `alerter.py` is orphaned after this plan; leave it alone to avoid scope creep.
- `engine/app/core/graph/builder.py` / `analyzer.py` / `pathfinder.py` / `export.py` — reused as-is.
- `engine/app/tasks/*` — Celery modules are irrelevant for this plan; detection runs synchronously.
- `supabase/migrations/*` — no schema changes required for Tasks 1–7. Tasks 8–9 will add a migration.

---

## Prerequisites

**Before Task 1:**

- [ ] **P1: Create feature branch**

```bash
cd "J:/Enso Intelligence/Kestrel"
git checkout -b feature/intelligence-core
git status
```

Expected: `On branch feature/intelligence-core` with clean working tree.

- [ ] **P2: Verify engine test suite currently passes**

```bash
cd engine
pytest -q
```

Expected: all existing tests pass. If any fail, stop and report — do not build on a broken baseline.

- [ ] **P3: Verify DBBL synthetic fixtures exist on disk**

```bash
ls engine/seed/generated/dbbl_synthetic/
```

Expected: `summary.json`, `organizations.json`, `entities.json`, `matches.json`, `connections.json`, `transactions.json`, `manifest.json`, `statements.json` are all present. These are the inputs for Task 8 verification.

---

## Task 1: Rewrite detection rule YAMLs + loader

**Why this is first:** Every other task reads these YAMLs (directly or indirectly). The evaluator needs the rule config to know thresholds and scoring modifiers. The scorer needs the weight. The pipeline loads them at startup.

**Files:**
- Create: `engine/tests/test_rules_loader_core.py`
- Modify: `engine/app/core/detection/loader.py`
- Rewrite: `engine/app/core/detection/rules/rapid_cashout.yaml`
- Rewrite: `engine/app/core/detection/rules/fan_in_burst.yaml`
- Rewrite: `engine/app/core/detection/rules/fan_out_burst.yaml`
- Rewrite: `engine/app/core/detection/rules/dormant_spike.yaml`
- Rewrite: `engine/app/core/detection/rules/layering.yaml`
- Rewrite: `engine/app/core/detection/rules/proximity_to_bad.yaml`
- Rewrite: `engine/app/core/detection/rules/structuring.yaml`
- Rewrite: `engine/app/core/detection/rules/first_time_high_value.yaml`

**Completion criteria:** All 8 YAML files parse under the new schema; `load_rules()` returns a list of `RuleDefinition` dicts; `test_rules_loader_core.py` and the legacy `test_scaffold.py::test_rule_catalog_loads_all_seeded_rules` both pass.

- [ ] **Step 1.1: Write failing loader test**

Create `engine/tests/test_rules_loader_core.py`:

```python
from pathlib import Path

import pytest

from app.core.detection.loader import load_rules

RULES_PATH = Path(__file__).resolve().parents[1] / "app" / "core" / "detection" / "rules"

EXPECTED_CODES = {
    "rapid_cashout",
    "fan_in_burst",
    "fan_out_burst",
    "dormant_spike",
    "layering",
    "proximity_to_bad",
    "structuring",
    "first_time_high_value",
}


def test_loader_returns_all_eight_rules() -> None:
    rules = load_rules(RULES_PATH)
    assert len(rules) == 8
    assert {rule["code"] for rule in rules} == EXPECTED_CODES


@pytest.mark.parametrize("code", sorted(EXPECTED_CODES))
def test_each_rule_has_full_schema(code: str) -> None:
    rules = {rule["code"]: rule for rule in load_rules(RULES_PATH)}
    rule = rules[code]

    assert isinstance(rule["title"], str) and rule["title"]
    assert isinstance(rule["category"], str) and rule["category"]
    assert isinstance(rule["weight"], (int, float)) and rule["weight"] > 0
    assert isinstance(rule["description"], str) and rule["description"].strip()

    conditions = rule["conditions"]
    assert isinstance(conditions["trigger"], str) and conditions["trigger"]
    assert isinstance(conditions["params"], dict)

    scoring = rule["scoring"]
    assert isinstance(scoring["base"], int) and 0 < scoring["base"] <= 100
    assert isinstance(scoring["modifiers"], list)
    for mod in scoring["modifiers"]:
        assert isinstance(mod["when"], str) and mod["when"]
        assert isinstance(mod["add"], int) and mod["add"] > 0
        assert isinstance(mod["reason"], str) and mod["reason"]

    severity = rule["severity"]
    assert severity["critical"] >= severity["high"] >= severity["medium"]

    template = rule["alert_template"]
    assert "{" in template["title"]
    assert "{" in template["description"]
```

- [ ] **Step 1.2: Run loader test — expect FAIL**

```bash
cd engine
pytest tests/test_rules_loader_core.py -q
```

Expected: fails because the current YAML files only have `code/title/weight/threshold`, not the full schema.

- [ ] **Step 1.3: Rewrite `loader.py`**

Replace `engine/app/core/detection/loader.py` contents with:

```python
from pathlib import Path
from typing import Any

import yaml

REQUIRED_TOP_LEVEL_KEYS = {
    "code",
    "title",
    "category",
    "weight",
    "description",
    "conditions",
    "scoring",
    "severity",
    "alert_template",
}


def _validate(rule: dict[str, Any], source: Path) -> None:
    missing = REQUIRED_TOP_LEVEL_KEYS - rule.keys()
    if missing:
        raise ValueError(f"Rule {source.name} is missing required keys: {sorted(missing)}")
    conditions = rule["conditions"]
    if not isinstance(conditions, dict) or "trigger" not in conditions or "params" not in conditions:
        raise ValueError(f"Rule {source.name} conditions must include trigger and params")
    scoring = rule["scoring"]
    if not isinstance(scoring, dict) or "base" not in scoring or "modifiers" not in scoring:
        raise ValueError(f"Rule {source.name} scoring must include base and modifiers")
    severity = rule["severity"]
    if not isinstance(severity, dict) or not {"critical", "high", "medium"}.issubset(severity.keys()):
        raise ValueError(f"Rule {source.name} severity must include critical/high/medium thresholds")
    template = rule["alert_template"]
    if not isinstance(template, dict) or "title" not in template or "description" not in template:
        raise ValueError(f"Rule {source.name} alert_template must include title and description")


def load_rules(rules_path: Path) -> list[dict[str, Any]]:
    """Load all YAML rule definition files under ``rules_path``.

    Returns a list of dicts conforming to the RuleDefinition schema.
    Raises ValueError if any rule file is missing required keys.
    """
    rules: list[dict[str, Any]] = []
    for path in sorted(rules_path.glob("*.yaml")):
        with path.open("r", encoding="utf-8") as handle:
            data = yaml.safe_load(handle)
        if not isinstance(data, dict):
            raise ValueError(f"Rule file {path.name} must contain a YAML mapping")
        _validate(data, path)
        rules.append(data)
    return rules
```

- [ ] **Step 1.4: Rewrite `rapid_cashout.yaml`**

Replace `engine/app/core/detection/rules/rapid_cashout.yaml` with:

```yaml
code: rapid_cashout
title: Rapid cash-out
category: velocity
weight: 8.0
description: >
  Flags accounts that receive credit and transfer out >=80% within 60 minutes.
  Classic mule account behavior - money lands and exits immediately.

conditions:
  trigger: credit_then_debit_percentage
  params:
    debit_pct_min: 80
    time_window_minutes: 60
    min_credit_amount: 50000

scoring:
  base: 60
  modifiers:
    - when: time_gap_minutes < 30
      add: 20
      reason: "Cash-out completed in under 30 minutes"
    - when: total_credit > 1000000
      add: 15
      reason: "Credit exceeds 10 lakh BDT"
    - when: account_age_days < 90
      add: 10
      reason: "Account opened less than 90 days ago"
    - when: cross_bank_debit == true
      add: 10
      reason: "Debits sent to accounts at different banks"
    - when: proximity_to_flagged <= 2
      add: 15
      reason: "Within 2 hops of a known flagged entity"

severity:
  critical: 90
  high: 70
  medium: 50

alert_template:
  title: "Rapid cash-out: {account_name}"
  description: "{debit_pct}% of BDT {credit_amount} debited within {time_gap} minutes via {debit_channel}"
```

- [ ] **Step 1.5: Rewrite `fan_in_burst.yaml`**

Replace contents with:

```yaml
code: fan_in_burst
title: Fan-in burst
category: velocity
weight: 6.0
description: >
  Multiple unique senders transfer to the same recipient within a short window.
  Indicates pooled fund collection typical of mule account operations.

conditions:
  trigger: unique_senders_to_recipient
  params:
    min_unique_senders: 5
    time_window_minutes: 30
    min_total_amount: 100000

scoring:
  base: 55
  modifiers:
    - when: unique_senders > 10
      add: 15
      reason: "More than 10 unique senders"
    - when: total_amount > 2000000
      add: 10
      reason: "Total inflow exceeds 20 lakh BDT"
    - when: senders_from_multiple_banks == true
      add: 10
      reason: "Senders span multiple banks (NPSB transfers)"
    - when: all_similar_amounts == true
      add: 10
      reason: "All incoming amounts are suspiciously similar (within 10%)"

severity:
  critical: 90
  high: 70
  medium: 50

alert_template:
  title: "Fan-in burst: {account_name}"
  description: "{unique_senders} unique senders transferred BDT {total_amount} within {time_window} minutes"
```

- [ ] **Step 1.6: Rewrite `fan_out_burst.yaml`**

Replace contents with:

```yaml
code: fan_out_burst
title: Fan-out burst
category: velocity
weight: 6.0
description: >
  One account sends to multiple distinct recipients within a short window.
  Indicates fund distribution or layering through multiple accounts.

conditions:
  trigger: unique_recipients_from_sender
  params:
    min_unique_recipients: 5
    time_window_minutes: 30
    min_total_amount: 100000

scoring:
  base: 50
  modifiers:
    - when: unique_recipients > 8
      add: 15
      reason: "More than 8 unique recipients"
    - when: all_similar_amounts == true
      add: 10
      reason: "All outgoing amounts are suspiciously similar (within 10%)"
    - when: recipients_at_different_banks == true
      add: 10
      reason: "Recipients span multiple banks"
    - when: total_amount > 2000000
      add: 10
      reason: "Total outflow exceeds 20 lakh BDT"

severity:
  critical: 90
  high: 70
  medium: 50

alert_template:
  title: "Fan-out burst: {account_name}"
  description: "{unique_recipients} recipients received BDT {total_amount} within {time_window} minutes"
```

- [ ] **Step 1.7: Rewrite `dormant_spike.yaml`**

Replace contents with:

```yaml
code: dormant_spike
title: Dormant account spike
category: pattern
weight: 5.0
description: >
  Account with near-zero balance suddenly receives large credits.
  Rented or hijacked accounts often show this pattern.

conditions:
  trigger: balance_spike_after_dormancy
  params:
    dormant_days: 30
    max_prior_balance: 10000
    min_spike_amount: 5000000

scoring:
  base: 65
  modifiers:
    - when: spike_amount > 10000000
      add: 15
      reason: "Spike exceeds 1 crore BDT"
    - when: multiple_npsb_sources == true
      add: 10
      reason: "Credits arrived from multiple banks via NPSB"
    - when: dormant_days > 90
      add: 10
      reason: "Account dormant for over 90 days before spike"
    - when: immediate_outflow == true
      add: 15
      reason: "Significant outflow began within hours of spike"

severity:
  critical: 90
  high: 70
  medium: 50

alert_template:
  title: "Dormant spike: {account_name}"
  description: "Account dormant {dormant_days} days, then received BDT {spike_amount} from {source_count} sources"
```

- [ ] **Step 1.8: Rewrite `layering.yaml`**

Replace contents with:

```yaml
code: layering
title: Layering
category: pattern
weight: 7.0
description: >
  Multiple structured transfers of similar amounts within a short period,
  designed to obscure the money trail through layers of transactions.

conditions:
  trigger: structured_similar_transfers
  params:
    min_transfer_count: 5
    amount_variance_pct: 10
    time_window_hours: 48
    min_total_amount: 200000

scoring:
  base: 55
  modifiers:
    - when: transfer_count > 10
      add: 15
      reason: "More than 10 structured transfers"
    - when: involves_multiple_banks == true
      add: 10
      reason: "Transfers span multiple banks"
    - when: amount_variance_pct < 5
      add: 10
      reason: "Amounts are nearly identical (variance under 5%)"
    - when: circular_flow_detected == true
      add: 15
      reason: "Circular flow detected - funds return to origin path"

severity:
  critical: 90
  high: 70
  medium: 50

alert_template:
  title: "Layering detected: {account_name}"
  description: "{transfer_count} transfers averaging BDT {avg_amount} (within {variance}%) over {time_window} hours"
```

- [ ] **Step 1.9: Rewrite `proximity_to_bad.yaml`**

Replace contents with:

```yaml
code: proximity_to_bad
title: Proximity to flagged entity
category: graph
weight: 5.0
description: >
  Account or entity is within 2 transaction hops of a known flagged entity.

conditions:
  trigger: graph_proximity
  params:
    max_hops: 2
    target_entity_status:
      - active
      - confirmed
    min_target_confidence: 0.6

scoring:
  base: 40
  modifiers:
    - when: hop_distance == 1
      add: 25
      reason: "Direct transaction with flagged entity"
    - when: target_confidence > 0.8
      add: 10
      reason: "Connected entity has high confidence score"
    - when: multiple_flagged_neighbors == true
      add: 15
      reason: "Connected to multiple flagged entities"

severity:
  critical: 90
  high: 70
  medium: 50

alert_template:
  title: "Proximity alert: {account_name}"
  description: "{hop_distance} hop(s) from flagged entity {flagged_entity_name} (confidence {confidence})"
```

- [ ] **Step 1.10: Rewrite `structuring.yaml`**

Replace contents with:

```yaml
code: structuring
title: Structuring
category: pattern
weight: 5.0
description: >
  Multiple transactions just under the CTR reporting threshold (10 lakh BDT)
  within a short period, suggesting deliberate avoidance of reporting.

conditions:
  trigger: sub_threshold_clustering
  params:
    threshold_amount: 1000000
    margin_pct: 5
    min_count: 3
    time_window_hours: 24

scoring:
  base: 45
  modifiers:
    - when: count > 5
      add: 15
      reason: "More than 5 sub-threshold transactions"
    - when: same_channel == true
      add: 10
      reason: "All transactions through same channel"
    - when: amounts_tightly_clustered == true
      add: 10
      reason: "Amounts clustered within 2% of threshold"
    - when: same_day == true
      add: 10
      reason: "All transactions on same day"

severity:
  critical: 90
  high: 70
  medium: 50

alert_template:
  title: "Structuring suspected: {account_name}"
  description: "{count} transactions averaging BDT {avg_amount} (just under 10 lakh threshold) within {hours} hours"
```

- [ ] **Step 1.11: Rewrite `first_time_high_value.yaml`**

Replace contents with:

```yaml
code: first_time_high_value
title: First-time high value
category: behavioral
weight: 4.0
description: >
  Large transfer to a new beneficiary from a relatively new account.

conditions:
  trigger: new_beneficiary_high_value
  params:
    min_amount: 500000
    max_account_age_days: 90
    no_prior_transactions_to_beneficiary: true

scoring:
  base: 50
  modifiers:
    - when: amount > 1000000
      add: 20
      reason: "Amount exceeds 10 lakh BDT"
    - when: beneficiary_at_different_bank == true
      add: 10
      reason: "Beneficiary is at a different bank"
    - when: account_age_days < 30
      add: 10
      reason: "Sender account is less than 30 days old"
    - when: beneficiary_is_flagged == true
      add: 15
      reason: "Beneficiary is a known flagged entity"

severity:
  critical: 90
  high: 70
  medium: 50

alert_template:
  title: "First-time high value: {account_name}"
  description: "BDT {amount} sent to new beneficiary {beneficiary_name} (account age {account_age} days)"
```

- [ ] **Step 1.12: Run loader tests — expect PASS**

```bash
cd engine
pytest tests/test_rules_loader_core.py tests/test_scaffold.py::test_rule_catalog_loads_all_seeded_rules -v
```

Expected: both the new test file and the existing scaffold test pass. If the scaffold test fails, inspect its assertions — it may need to be updated to the new schema shape.

- [ ] **Step 1.13: Commit**

```bash
git add engine/app/core/detection/rules/ engine/app/core/detection/loader.py engine/tests/test_rules_loader_core.py
git commit -m "feat(detection): expand rule YAMLs to declarative DSL with scoring modifiers"
```

---

## Task 3: Entity resolver (TDD)

**Dependency:** Task 1 complete (not strictly required but keeps commits ordered).

**Why this comes before Task 2:** The scan pipeline flow is `parse transactions → evaluate → resolve flagged account as entity → check cross-bank`. But the STR pipeline flow is `STR submitted → resolve subject identifiers → check cross-bank`. The resolver is used by both pipelines, so building it first unblocks Task 6 and lets us write realistic tests for Task 4 (matcher) which consumes resolved entities.

**Files:**
- Rewrite: `engine/app/core/resolver.py`
- Create: `engine/tests/test_resolver_core.py`

**Completion criteria:** Pure normalization helpers are unit-tested. `resolve_identifier` and `resolve_identifiers_from_str` are implemented with clear docstrings. Tests use fake SQLAlchemy session and model rows.

- [ ] **Step 3.1: Write failing test for normalization helpers**

Create `engine/tests/test_resolver_core.py`:

```python
import pytest

from app.core.resolver import normalize_identifier


@pytest.mark.parametrize(
    ("entity_type", "raw", "expected"),
    [
        ("account", "  1781 4300 0070 1  ", "178143000701"),
        ("account", "abc-123", "ABC123"),
        ("phone", "+880 1712 345678", "+8801712345678"),
        ("phone", "01712-345678", "01712345678"),
        ("phone", "8801712345678", "+8801712345678"),
        ("nid", " 1234 5678 9012 ", "123456789012"),
        ("wallet", " abcd1234 ", "ABCD1234"),
        ("person", "  Rizwana   Enterprise  ", "rizwana enterprise"),
        ("business", "RIZWANA ENTERPRISE LTD.", "rizwana enterprise ltd."),
    ],
)
def test_normalize_identifier_forms(entity_type: str, raw: str, expected: str) -> None:
    assert normalize_identifier(entity_type, raw) == expected


def test_normalize_identifier_rejects_empty() -> None:
    with pytest.raises(ValueError):
        normalize_identifier("account", "")
    with pytest.raises(ValueError):
        normalize_identifier("account", "   ")


def test_normalize_identifier_unknown_type_passes_through() -> None:
    # Unknown types fall back to strip + lowercase
    assert normalize_identifier("device", "  ABC-XYZ  ") == "abc-xyz"
```

- [ ] **Step 3.2: Run test — expect FAIL (ImportError)**

```bash
cd engine
pytest tests/test_resolver_core.py -q
```

Expected: fails because `normalize_identifier` does not yet exist in `app.core.resolver`.

- [ ] **Step 3.3: Rewrite `resolver.py` skeleton with `normalize_identifier`**

Replace `engine/app/core/resolver.py` contents with:

```python
"""Entity resolver.

Turns identifiers (account, phone, wallet, nid, person, business) into
canonical shared-intelligence `Entity` rows. Used by the STR submission
pipeline and the scan detection pipeline.
"""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.connection import Connection
from app.models.entity import Entity
from app.models.str_report import STRReport

_CONFIDENCE_BY_SOURCE: dict[str, float] = {
    "str_cross_ref": 0.7,
    "manual": 0.8,
    "pattern_scan": 0.6,
    "system": 0.5,
}

_FUZZY_ELIGIBLE_TYPES = {"person", "business"}
_FUZZY_SIMILARITY_THRESHOLD = 0.6


def normalize_identifier(entity_type: str, raw_value: str) -> str:
    """Return the canonical form of ``raw_value`` for the given ``entity_type``.

    - account / wallet: strip whitespace, uppercase, remove separators.
    - phone: strip whitespace/punctuation; if 13 digits starting with 880 prepend ``+``.
    - nid: digits only.
    - person / business: lowercase, collapse whitespace.
    - anything else: strip + lowercase.

    Raises ValueError when the normalized value is empty.
    """
    if raw_value is None:
        raise ValueError("Identifier value is required")
    value = str(raw_value).strip()
    if not value:
        raise ValueError("Identifier value is required")

    if entity_type in {"account", "wallet"}:
        cleaned = re.sub(r"[\s\-]+", "", value).upper()
    elif entity_type == "phone":
        digits_plus = re.sub(r"[^\d+]", "", value)
        if digits_plus.startswith("+"):
            cleaned = digits_plus
        elif digits_plus.startswith("880") and len(digits_plus) >= 12:
            cleaned = "+" + digits_plus
        else:
            cleaned = digits_plus
    elif entity_type == "nid":
        cleaned = re.sub(r"[^\d]", "", value)
    elif entity_type in _FUZZY_ELIGIBLE_TYPES:
        cleaned = re.sub(r"\s+", " ", value).strip().lower()
    else:
        cleaned = value.lower()

    if not cleaned:
        raise ValueError(f"Normalized identifier is empty for type {entity_type}")
    return cleaned
```

- [ ] **Step 3.4: Run normalization test — expect PASS**

```bash
cd engine
pytest tests/test_resolver_core.py -q
```

Expected: all 10 parametrized cases plus the three edge-case tests pass.

- [ ] **Step 3.5: Write failing test for `resolve_identifier`**

Append to `engine/tests/test_resolver_core.py`:

```python
import uuid
from types import SimpleNamespace

from app.core.resolver import resolve_identifier


class FakeScalarsResult:
    def __init__(self, items: list[object]) -> None:
        self._items = items

    def first(self) -> object | None:
        return self._items[0] if self._items else None

    def all(self) -> list[object]:
        return list(self._items)


class FakeExecResult:
    def __init__(self, items: list[object]) -> None:
        self._items = items

    def scalars(self) -> FakeScalarsResult:
        return FakeScalarsResult(self._items)


class FakeSession:
    def __init__(self, preloaded: list[object] | None = None) -> None:
        self.preloaded = preloaded or []
        self.added: list[object] = []
        self.flushed = False

    async def execute(self, *_args, **_kwargs) -> FakeExecResult:
        return FakeExecResult(self.preloaded)

    def add(self, obj: object) -> None:
        self.added.append(obj)

    async def flush(self) -> None:
        self.flushed = True


@pytest.mark.asyncio
async def test_resolve_identifier_creates_new_entity_when_no_match() -> None:
    session = FakeSession(preloaded=[])
    org_id = uuid.uuid4()

    entity = await resolve_identifier(
        session,
        entity_type="account",
        raw_value="  1781 4300 0070 1  ",
        org_id=org_id,
        source="str_cross_ref",
        display_name="Rizwana Enterprise",
    )

    assert entity.canonical_value == "178143000701"
    assert entity.entity_type == "account"
    assert entity.source == "str_cross_ref"
    assert float(entity.confidence) == pytest.approx(0.7)
    assert org_id in entity.reporting_orgs
    assert entity.report_count == 1
    assert session.added == [entity]
    assert session.flushed is True


@pytest.mark.asyncio
async def test_resolve_identifier_updates_existing_entity_on_hit() -> None:
    existing = Entity(
        id=uuid.uuid4(),
        entity_type="phone",
        canonical_value="+8801712345678",
        display_value="01712345678",
        display_name="Rizwana",
        confidence=0.6,
        source="system",
        reporting_orgs=[],
        report_count=2,
        total_exposure=0,
        tags=[],
        metadata_json={},
    )
    new_org_id = uuid.uuid4()
    session = FakeSession(preloaded=[existing])

    entity = await resolve_identifier(
        session,
        entity_type="phone",
        raw_value="+880 1712-345678",
        org_id=new_org_id,
        source="str_cross_ref",
        display_name="Rizwana",
    )

    assert entity is existing
    assert entity.report_count == 3
    assert new_org_id in entity.reporting_orgs
    assert entity.last_seen is not None
    assert session.added == []  # Not re-added
```

- [ ] **Step 3.6: Run new tests — expect FAIL**

```bash
cd engine
pytest tests/test_resolver_core.py -q
```

Expected: fails with `ImportError` or `AttributeError: resolve_identifier`.

- [ ] **Step 3.7: Implement `resolve_identifier`**

Append to `engine/app/core/resolver.py`:

```python
async def _find_exact_entity(
    session: AsyncSession,
    *,
    entity_type: str,
    canonical_value: str,
) -> Entity | None:
    stmt = (
        select(Entity)
        .where(Entity.entity_type == entity_type)
        .where(Entity.canonical_value == canonical_value)
        .limit(1)
    )
    result = await session.execute(stmt)
    return result.scalars().first()


async def _find_fuzzy_entity(
    session: AsyncSession,
    *,
    entity_type: str,
    display_name: str,
) -> Entity | None:
    """Fuzzy-match on display_name using pg_trgm similarity.

    Only used for ``person`` and ``business`` entity types. Falls back to None
    silently if pg_trgm is not available (e.g., in unit tests against a mock
    session that returns an empty result).
    """
    try:
        stmt = (
            select(Entity)
            .where(Entity.entity_type == entity_type)
            .where(func.similarity(Entity.display_name, display_name) >= _FUZZY_SIMILARITY_THRESHOLD)
            .order_by(func.similarity(Entity.display_name, display_name).desc())
            .limit(1)
        )
        result = await session.execute(stmt)
        return result.scalars().first()
    except Exception:
        return None


def _update_existing(
    entity: Entity,
    *,
    org_id: uuid.UUID,
    source: str,
) -> Entity:
    now = datetime.now(UTC)
    entity.last_seen = now
    entity.report_count = (entity.report_count or 0) + 1
    reporting = list(entity.reporting_orgs or [])
    if org_id not in reporting:
        reporting.append(org_id)
    entity.reporting_orgs = reporting
    if not entity.first_seen:
        entity.first_seen = now
    if source and (not entity.source or entity.source == "system"):
        entity.source = source
    return entity


def _build_new_entity(
    *,
    entity_type: str,
    canonical_value: str,
    display_value: str,
    display_name: str | None,
    org_id: uuid.UUID,
    source: str,
) -> Entity:
    now = datetime.now(UTC)
    confidence = _CONFIDENCE_BY_SOURCE.get(source, 0.5)
    return Entity(
        id=uuid.uuid4(),
        entity_type=entity_type,
        canonical_value=canonical_value,
        display_value=display_value,
        display_name=display_name,
        confidence=confidence,
        source=source,
        status="active",
        reporting_orgs=[org_id],
        report_count=1,
        first_seen=now,
        last_seen=now,
        total_exposure=0,
        tags=[],
        metadata_json={},
    )


async def resolve_identifier(
    session: AsyncSession,
    *,
    entity_type: str,
    raw_value: str,
    org_id: uuid.UUID,
    source: str = "str_cross_ref",
    display_name: str | None = None,
) -> Entity:
    """Resolve one identifier to an Entity row, creating it if missing.

    - Normalizes the raw value to its canonical form.
    - Looks for an exact ``(entity_type, canonical_value)`` match.
    - For person/business types, falls back to fuzzy match on display_name.
    - On hit, updates ``last_seen``, ``report_count``, ``reporting_orgs``.
    - On miss, inserts a new Entity with source-based initial confidence.

    Caller is responsible for the surrounding transaction; this function
    calls ``session.flush()`` after adding new entities so the caller sees
    a populated ``entity.id``.
    """
    canonical = normalize_identifier(entity_type, raw_value)

    existing = await _find_exact_entity(
        session, entity_type=entity_type, canonical_value=canonical
    )
    if existing is None and entity_type in _FUZZY_ELIGIBLE_TYPES and display_name:
        existing = await _find_fuzzy_entity(
            session, entity_type=entity_type, display_name=display_name
        )

    if existing is not None:
        return _update_existing(existing, org_id=org_id, source=source)

    entity = _build_new_entity(
        entity_type=entity_type,
        canonical_value=canonical,
        display_value=str(raw_value).strip(),
        display_name=display_name,
        org_id=org_id,
        source=source,
    )
    session.add(entity)
    await session.flush()
    return entity
```

- [ ] **Step 3.8: Run resolver tests — expect PASS**

```bash
cd engine
pytest tests/test_resolver_core.py -q
```

Expected: all tests pass including the two async tests.

- [ ] **Step 3.9: Write failing test for `resolve_identifiers_from_str`**

Append to `engine/tests/test_resolver_core.py`:

```python
from app.core.resolver import resolve_identifiers_from_str
from app.models.str_report import STRReport


class FakeSessionWithConnections(FakeSession):
    """Tracks Connection rows added in addition to Entity rows."""

    async def execute(self, *_args, **_kwargs) -> FakeExecResult:
        # Always return empty so every identifier gets created as new.
        return FakeExecResult([])


@pytest.mark.asyncio
async def test_resolve_identifiers_from_str_creates_all_entities_and_connections() -> None:
    session = FakeSessionWithConnections(preloaded=[])
    org_id = uuid.uuid4()

    report = SimpleNamespace(
        id=uuid.uuid4(),
        org_id=org_id,
        subject_name="Rizwana Enterprise",
        subject_account="178143000701",
        subject_bank="Dutch-Bangla Bank PLC",
        subject_phone="+8801712345678",
        subject_wallet=None,
        subject_nid="1234567890123",
    )

    entities = await resolve_identifiers_from_str(
        session, str_report=report, org_id=org_id
    )

    codes = sorted({e.entity_type for e in entities})
    assert codes == ["account", "nid", "phone"]

    added_entities = [obj for obj in session.added if isinstance(obj, Entity)]
    added_connections = [obj for obj in session.added if isinstance(obj, Connection)]

    assert len(added_entities) == 3
    # phone + account + nid => 3 entities => 3 pairwise connections
    assert len(added_connections) == 3
    assert all(conn.relation == "same_owner" for conn in added_connections)
```

- [ ] **Step 3.10: Run — expect FAIL**

```bash
cd engine
pytest tests/test_resolver_core.py::test_resolve_identifiers_from_str_creates_all_entities_and_connections -q
```

Expected: fails with `ImportError: resolve_identifiers_from_str`.

- [ ] **Step 3.11: Implement `resolve_identifiers_from_str`**

Append to `engine/app/core/resolver.py`:

```python
@dataclass
class _IdentifierSlot:
    entity_type: str
    raw_value: str
    display_name: str | None


def _extract_identifier_slots(str_report: STRReport | Any) -> list[_IdentifierSlot]:
    slots: list[_IdentifierSlot] = []
    subject_name = getattr(str_report, "subject_name", None)

    subject_account = getattr(str_report, "subject_account", None)
    if subject_account:
        slots.append(_IdentifierSlot("account", subject_account, subject_name))

    subject_phone = getattr(str_report, "subject_phone", None)
    if subject_phone:
        slots.append(_IdentifierSlot("phone", subject_phone, subject_name))

    subject_wallet = getattr(str_report, "subject_wallet", None)
    if subject_wallet:
        slots.append(_IdentifierSlot("wallet", subject_wallet, subject_name))

    subject_nid = getattr(str_report, "subject_nid", None)
    if subject_nid:
        slots.append(_IdentifierSlot("nid", subject_nid, subject_name))

    if subject_name:
        slots.append(_IdentifierSlot("person", subject_name, subject_name))

    return slots


async def _upsert_same_owner_connection(
    session: AsyncSession,
    *,
    from_entity: Entity,
    to_entity: Entity,
) -> None:
    if from_entity.id == to_entity.id:
        return
    stmt = (
        select(Connection)
        .where(Connection.from_entity_id == from_entity.id)
        .where(Connection.to_entity_id == to_entity.id)
        .where(Connection.relation == "same_owner")
        .limit(1)
    )
    try:
        result = await session.execute(stmt)
        existing = result.scalars().first()
    except Exception:
        existing = None
    if existing is not None:
        existing.last_seen = datetime.now(UTC)
        return

    now = datetime.now(UTC)
    connection = Connection(
        id=uuid.uuid4(),
        from_entity_id=from_entity.id,
        to_entity_id=to_entity.id,
        relation="same_owner",
        weight=1.0,
        evidence={"source": "str_cross_ref"},
        first_seen=now,
        last_seen=now,
    )
    session.add(connection)


async def resolve_identifiers_from_str(
    session: AsyncSession,
    *,
    str_report: STRReport | Any,
    org_id: uuid.UUID,
) -> list[Entity]:
    """Resolve every identifier on ``str_report`` and link them pairwise.

    Emits ``same_owner`` connections between every pair of non-person
    entities so the shared graph picks up the relationship. Returns the
    full list of resolved entities (new + existing).
    """
    slots = _extract_identifier_slots(str_report)
    resolved: list[Entity] = []
    for slot in slots:
        try:
            entity = await resolve_identifier(
                session,
                entity_type=slot.entity_type,
                raw_value=slot.raw_value,
                org_id=org_id,
                source="str_cross_ref",
                display_name=slot.display_name,
            )
        except ValueError:
            continue
        resolved.append(entity)

    graph_entities = [e for e in resolved if e.entity_type != "person"]
    for i, a in enumerate(graph_entities):
        for b in graph_entities[i + 1:]:
            await _upsert_same_owner_connection(session, from_entity=a, to_entity=b)
            await _upsert_same_owner_connection(session, from_entity=b, to_entity=a)

    return resolved
```

- [ ] **Step 3.12: Run resolver tests — expect PASS**

```bash
cd engine
pytest tests/test_resolver_core.py -q
```

Expected: all resolver tests pass. If the last test asserts 3 connections but the implementation produces 6 (pairwise bidirectional: account↔phone, account↔nid, phone↔nid = 3 pairs × 2 directions), update the assertion to `== 6`. Directionality is intentional because `Connection` is a directed edge.

**Note to implementer:** The initial test asserted `== 3` based on "3 pairs". After running, you will likely see 6 because each pair creates two directed edges. Update the assertion to `== 6` and re-run. This is the intended behavior — do not change the implementation.

- [ ] **Step 3.13: Commit**

```bash
git add engine/app/core/resolver.py engine/tests/test_resolver_core.py
git commit -m "feat(detection): real entity resolver with normalization, fuzzy match, connection linking"
```

---

## Task 2: Detection evaluator

**Dependency:** Task 1 complete (evaluator reads YAML configs).

**Files:**
- Create: `engine/app/core/detection/rule_hit.py`
- Rewrite: `engine/app/core/detection/evaluator.py`
- Create: `engine/tests/test_evaluator_core.py`

**Completion criteria:** All 8 rule evaluators implemented, unit-tested against synthetic `SimpleNamespace` transactions, and a top-level `evaluate_accounts` function returns `list[RuleHit]`.

- [ ] **Step 2.1: Create `RuleHit` dataclass**

Create `engine/app/core/detection/rule_hit.py`:

```python
"""RuleHit dataclass - the unit of output from detection rule evaluators."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any


@dataclass
class RuleHit:
    """One rule triggering against one account.

    - ``account_entity_id`` is the Entity row the alert will point at.
      Evaluators populate the Account's id (or synthetic id) and the
      pipeline resolves it to an Entity.
    - ``score`` is the raw score including base + applied modifiers.
    - ``weight`` is the rule weight from YAML, used by the scorer.
    - ``reasons`` is an ordered list of dicts: {modifier, score_added, reason}.
    - ``evidence`` is rule-specific context (times, amounts, counts) used
      for alert templating and explainability.
    - ``alert_title`` / ``alert_description`` are rendered from the rule's
      alert_template using evidence fields.
    """

    account_id: uuid.UUID | str
    rule_code: str
    score: int
    weight: float
    reasons: list[dict[str, Any]] = field(default_factory=list)
    evidence: dict[str, Any] = field(default_factory=dict)
    alert_title: str = ""
    alert_description: str = ""
```

- [ ] **Step 2.2: Write failing test for `_group_transactions_by_account`**

Create `engine/tests/test_evaluator_core.py`:

```python
import uuid
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import pytest

from app.core.detection.evaluator import (
    _group_transactions_by_account,
    evaluate_rapid_cashout,
    evaluate_fan_in_burst,
    evaluate_fan_out_burst,
    evaluate_structuring,
    evaluate_layering,
    evaluate_first_time_high_value,
    evaluate_dormant_spike,
    evaluate_accounts,
)
from app.core.detection.rule_hit import RuleHit


NOW = datetime(2026, 4, 15, 12, 0, 0, tzinfo=UTC)


def make_txn(
    *,
    src: uuid.UUID | None,
    dst: uuid.UUID | None,
    amount: float,
    posted_at: datetime,
    channel: str = "NPSB",
    tx_type: str = "transfer",
) -> SimpleNamespace:
    return SimpleNamespace(
        id=uuid.uuid4(),
        src_account_id=src,
        dst_account_id=dst,
        amount=amount,
        posted_at=posted_at,
        channel=channel,
        tx_type=tx_type,
        currency="BDT",
    )


def make_account(account_id: uuid.UUID, *, name: str, bank_code: str = "DBBL", age_days: int = 365) -> SimpleNamespace:
    return SimpleNamespace(
        id=account_id,
        account_number=f"ACC{str(account_id)[:8]}",
        account_name=name,
        bank_code=bank_code,
        created_at=NOW - timedelta(days=age_days),
        metadata_json={},
    )


def test_group_transactions_by_account_includes_src_and_dst() -> None:
    a = uuid.uuid4()
    b = uuid.uuid4()
    c = uuid.uuid4()
    txns = [
        make_txn(src=a, dst=b, amount=100, posted_at=NOW),
        make_txn(src=b, dst=c, amount=50, posted_at=NOW),
    ]

    grouped = _group_transactions_by_account(txns)

    assert set(grouped.keys()) == {a, b, c}
    assert len(grouped[a]) == 1
    assert len(grouped[b]) == 2
    assert len(grouped[c]) == 1
```

- [ ] **Step 2.3: Run — expect FAIL (ImportError)**

```bash
cd engine
pytest tests/test_evaluator_core.py::test_group_transactions_by_account_includes_src_and_dst -q
```

Expected: fails because nothing is implemented.

- [ ] **Step 2.4: Implement evaluator skeleton + grouping helper**

Replace `engine/app/core/detection/evaluator.py` contents with:

```python
"""Detection rule evaluators.

Each public ``evaluate_*`` function takes:
- ``account``: a SimpleNamespace or SQLAlchemy ``Account`` with at least
  ``id``, ``account_number``, ``account_name``, ``bank_code``, ``created_at``,
  ``metadata_json``.
- ``account_txns``: list of Transaction-like objects where ``src_account_id``
  or ``dst_account_id`` equals ``account.id``.
- ``rule_config``: the YAML-loaded rule dict.
- ``graph``: optional NetworkX DiGraph, only used by ``evaluate_proximity_to_bad``.
- ``flagged_entity_ids``: optional set[str], only used by proximity.

Each returns ``RuleHit`` on trigger or ``None`` otherwise.

Determinism: evaluators must be deterministic given the same inputs.
Never use ``random``, ``datetime.now``, or wall-clock time - all time
comparisons must derive from transaction ``posted_at`` values.
"""

from __future__ import annotations

import statistics
import uuid
from collections import defaultdict
from datetime import UTC, datetime, timedelta
from typing import Any, Iterable

import networkx as nx

from app.core.detection.rule_hit import RuleHit


def _txn_dt(txn: Any) -> datetime:
    value = txn.posted_at
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _as_float(value: Any) -> float:
    if value is None:
        return 0.0
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _group_transactions_by_account(
    transactions: Iterable[Any],
) -> dict[uuid.UUID, list[Any]]:
    """Return a dict mapping account_id -> list of transactions touching it.

    Each transaction appears in at most two lists (source and destination).
    """
    grouped: dict[uuid.UUID, list[Any]] = defaultdict(list)
    for txn in transactions:
        src = getattr(txn, "src_account_id", None)
        dst = getattr(txn, "dst_account_id", None)
        if src is not None:
            grouped[src].append(txn)
        if dst is not None and dst != src:
            grouped[dst].append(txn)
    return dict(grouped)


def _render_template(template: str, evidence: dict[str, Any]) -> str:
    try:
        return template.format_map(_DefaultDict(evidence))
    except Exception:
        return template


class _DefaultDict(dict):
    def __missing__(self, key: str) -> str:
        return f"{{{key}}}"


def _account_age_days(account: Any, reference: datetime) -> int:
    created = getattr(account, "created_at", None)
    if created is None:
        return 365
    if created.tzinfo is None:
        created = created.replace(tzinfo=UTC)
    return max(0, (reference - created).days)
```

- [ ] **Step 2.5: Run grouping test — expect PASS**

```bash
cd engine
pytest tests/test_evaluator_core.py::test_group_transactions_by_account_includes_src_and_dst -q
```

Expected: PASS.

- [ ] **Step 2.6: Write failing test for `evaluate_rapid_cashout`**

Append to `engine/tests/test_evaluator_core.py`:

```python
RAPID_CASHOUT_CONFIG = {
    "code": "rapid_cashout",
    "title": "Rapid cash-out",
    "weight": 8.0,
    "conditions": {
        "trigger": "credit_then_debit_percentage",
        "params": {
            "debit_pct_min": 80,
            "time_window_minutes": 60,
            "min_credit_amount": 50_000,
        },
    },
    "scoring": {
        "base": 60,
        "modifiers": [
            {"when": "time_gap_minutes < 30", "add": 20, "reason": "Under 30 minutes"},
            {"when": "total_credit > 1000000", "add": 15, "reason": "Credit over 10 lakh"},
            {"when": "account_age_days < 90", "add": 10, "reason": "New account"},
            {"when": "cross_bank_debit == true", "add": 10, "reason": "Cross-bank exit"},
        ],
    },
    "severity": {"critical": 90, "high": 70, "medium": 50},
    "alert_template": {
        "title": "Rapid cash-out: {account_name}",
        "description": "{debit_pct}% of BDT {credit_amount} debited within {time_gap} minutes",
    },
}


def test_rapid_cashout_triggers_on_large_credit_then_fast_debit() -> None:
    account_id = uuid.uuid4()
    other_id = uuid.uuid4()
    account = make_account(account_id, name="Mule One", age_days=45)

    txns = [
        # Credit lands
        make_txn(src=other_id, dst=account_id, amount=1_500_000, posted_at=NOW),
        # Debits exit within 20 minutes, totaling 95% of credit
        make_txn(src=account_id, dst=uuid.uuid4(), amount=700_000, posted_at=NOW + timedelta(minutes=5), channel="NPSB"),
        make_txn(src=account_id, dst=uuid.uuid4(), amount=725_000, posted_at=NOW + timedelta(minutes=18), channel="NPSB"),
    ]

    hit = evaluate_rapid_cashout(
        account=account,
        account_txns=txns,
        rule_config=RAPID_CASHOUT_CONFIG,
    )

    assert hit is not None
    assert hit.rule_code == "rapid_cashout"
    assert hit.score >= 60  # base
    # Under 30 minutes modifier (+20), over 10 lakh (+15), new account (+10)
    assert hit.score >= 60 + 20 + 15 + 10
    assert hit.weight == 8.0
    assert "Mule One" in hit.alert_title
    assert "95" in hit.alert_description or "95.0" in hit.alert_description
    assert any("Under 30 minutes" in r["reason"] for r in hit.reasons)


def test_rapid_cashout_no_trigger_when_debit_too_slow() -> None:
    account_id = uuid.uuid4()
    account = make_account(account_id, name="Normal", age_days=500)
    txns = [
        make_txn(src=uuid.uuid4(), dst=account_id, amount=1_000_000, posted_at=NOW),
        make_txn(src=account_id, dst=uuid.uuid4(), amount=900_000, posted_at=NOW + timedelta(hours=5)),
    ]

    hit = evaluate_rapid_cashout(
        account=account, account_txns=txns, rule_config=RAPID_CASHOUT_CONFIG
    )
    assert hit is None


def test_rapid_cashout_no_trigger_when_credit_too_small() -> None:
    account_id = uuid.uuid4()
    account = make_account(account_id, name="Small", age_days=500)
    txns = [
        make_txn(src=uuid.uuid4(), dst=account_id, amount=20_000, posted_at=NOW),
        make_txn(src=account_id, dst=uuid.uuid4(), amount=18_000, posted_at=NOW + timedelta(minutes=10)),
    ]

    hit = evaluate_rapid_cashout(
        account=account, account_txns=txns, rule_config=RAPID_CASHOUT_CONFIG
    )
    assert hit is None
```

- [ ] **Step 2.7: Run — expect FAIL**

```bash
cd engine
pytest tests/test_evaluator_core.py -k rapid_cashout -q
```

Expected: ImportError for `evaluate_rapid_cashout`.

- [ ] **Step 2.8: Implement `evaluate_rapid_cashout`**

Append to `engine/app/core/detection/evaluator.py`:

```python
def _apply_modifiers(
    rule_config: dict[str, Any],
    evidence: dict[str, Any],
    modifier_map: dict[str, bool],
) -> tuple[int, list[dict[str, Any]]]:
    base = int(rule_config["scoring"]["base"])
    reasons: list[dict[str, Any]] = []
    for modifier in rule_config["scoring"]["modifiers"]:
        when = modifier["when"]
        if modifier_map.get(when, False):
            base += int(modifier["add"])
            reasons.append(
                {
                    "modifier": when,
                    "score_added": int(modifier["add"]),
                    "reason": modifier["reason"],
                }
            )
    return min(base, 100), reasons


def evaluate_rapid_cashout(
    *,
    account: Any,
    account_txns: list[Any],
    rule_config: dict[str, Any],
) -> RuleHit | None:
    """Fire when a credit is followed by >=X% in debits within the time window."""
    params = rule_config["conditions"]["params"]
    debit_pct_min = float(params["debit_pct_min"])
    time_window = timedelta(minutes=int(params["time_window_minutes"]))
    min_credit = float(params["min_credit_amount"])

    credits = sorted(
        (t for t in account_txns if t.dst_account_id == account.id and _as_float(t.amount) > 0),
        key=_txn_dt,
    )
    if not credits:
        return None

    best_hit: RuleHit | None = None

    for credit in credits:
        credit_amount = _as_float(credit.amount)
        if credit_amount < min_credit:
            continue
        window_end = _txn_dt(credit) + time_window
        following_debits = [
            t
            for t in account_txns
            if t.src_account_id == account.id
            and _txn_dt(t) >= _txn_dt(credit)
            and _txn_dt(t) <= window_end
        ]
        if not following_debits:
            continue
        debit_total = sum(_as_float(t.amount) for t in following_debits)
        debit_pct = (debit_total / credit_amount) * 100 if credit_amount else 0
        if debit_pct < debit_pct_min:
            continue

        last_debit = max(following_debits, key=_txn_dt)
        time_gap_minutes = (_txn_dt(last_debit) - _txn_dt(credit)).total_seconds() / 60

        account_age_days = _account_age_days(account, _txn_dt(credit))
        total_credit = sum(_as_float(t.amount) for t in credits)
        debit_banks = {
            getattr(t, "dst_account_bank_code", None)
            or (t.metadata_json or {}).get("dst_bank_code")
            for t in following_debits
            if hasattr(t, "metadata_json") or hasattr(t, "dst_account_bank_code")
        }
        account_bank = getattr(account, "bank_code", None)
        cross_bank_debit = any(b and b != account_bank for b in debit_banks)

        modifier_map = {
            "time_gap_minutes < 30": time_gap_minutes < 30,
            "total_credit > 1000000": total_credit > 1_000_000,
            "account_age_days < 90": account_age_days < 90,
            "cross_bank_debit == true": cross_bank_debit,
            "proximity_to_flagged <= 2": False,  # Set by pipeline post-eval, not here
        }
        evidence = {
            "account_name": getattr(account, "account_name", None) or getattr(account, "account_number", ""),
            "credit_amount": f"{credit_amount:,.0f}",
            "debit_pct": f"{debit_pct:.0f}",
            "time_gap": f"{time_gap_minutes:.0f}",
            "debit_channel": getattr(following_debits[0], "channel", None) or "transfer",
            "time_gap_minutes": time_gap_minutes,
            "total_credit": total_credit,
            "account_age_days": account_age_days,
        }
        score, reasons = _apply_modifiers(rule_config, evidence, modifier_map)
        candidate = RuleHit(
            account_id=account.id,
            rule_code=rule_config["code"],
            score=score,
            weight=float(rule_config["weight"]),
            reasons=reasons,
            evidence=evidence,
            alert_title=_render_template(rule_config["alert_template"]["title"], evidence),
            alert_description=_render_template(rule_config["alert_template"]["description"], evidence),
        )
        if best_hit is None or candidate.score > best_hit.score:
            best_hit = candidate

    return best_hit
```

- [ ] **Step 2.9: Run rapid_cashout tests — expect PASS**

```bash
cd engine
pytest tests/test_evaluator_core.py -k rapid_cashout -q
```

Expected: all three rapid_cashout tests pass. If the cross-bank assertion fails because `make_txn` doesn't set `dst_account_bank_code`, that's fine — the modifier simply won't fire. The test only asserts `score >= 60 + 20 + 15 + 10` which does not require cross-bank.

- [ ] **Step 2.10: Write test + implement `evaluate_fan_in_burst`**

Append to test file:

```python
FAN_IN_CONFIG = {
    "code": "fan_in_burst",
    "title": "Fan-in burst",
    "weight": 6.0,
    "conditions": {
        "trigger": "unique_senders_to_recipient",
        "params": {
            "min_unique_senders": 5,
            "time_window_minutes": 30,
            "min_total_amount": 100_000,
        },
    },
    "scoring": {
        "base": 55,
        "modifiers": [
            {"when": "unique_senders > 10", "add": 15, "reason": "More than 10 senders"},
            {"when": "total_amount > 2000000", "add": 10, "reason": "Over 20 lakh"},
            {"when": "all_similar_amounts == true", "add": 10, "reason": "Similar amounts"},
        ],
    },
    "severity": {"critical": 90, "high": 70, "medium": 50},
    "alert_template": {
        "title": "Fan-in: {account_name}",
        "description": "{unique_senders} senders -> BDT {total_amount}",
    },
}


def test_fan_in_burst_triggers_on_many_unique_senders() -> None:
    recipient = uuid.uuid4()
    account = make_account(recipient, name="Pool", age_days=200)
    txns = [
        make_txn(src=uuid.uuid4(), dst=recipient, amount=50_000, posted_at=NOW + timedelta(minutes=i))
        for i in range(6)
    ]

    hit = evaluate_fan_in_burst(account=account, account_txns=txns, rule_config=FAN_IN_CONFIG)

    assert hit is not None
    assert hit.score >= 55
    assert hit.evidence["unique_senders"] == 6


def test_fan_in_burst_no_trigger_under_threshold() -> None:
    recipient = uuid.uuid4()
    account = make_account(recipient, name="Low", age_days=200)
    txns = [
        make_txn(src=uuid.uuid4(), dst=recipient, amount=50_000, posted_at=NOW + timedelta(minutes=i))
        for i in range(3)
    ]

    hit = evaluate_fan_in_burst(account=account, account_txns=txns, rule_config=FAN_IN_CONFIG)
    assert hit is None
```

Run to verify FAIL:

```bash
pytest tests/test_evaluator_core.py -k fan_in_burst -q
```

Append to evaluator:

```python
def _sliding_window_groups(
    events: list[Any],
    *,
    window: timedelta,
) -> list[list[Any]]:
    """Return all maximal sliding windows of ``events`` sorted by time."""
    if not events:
        return []
    events = sorted(events, key=_txn_dt)
    windows: list[list[Any]] = []
    for i in range(len(events)):
        end = _txn_dt(events[i]) + window
        group = [events[i]]
        for j in range(i + 1, len(events)):
            if _txn_dt(events[j]) <= end:
                group.append(events[j])
            else:
                break
        windows.append(group)
    return windows


def _amounts_similar(amounts: list[float], *, tolerance_pct: float = 10.0) -> bool:
    if len(amounts) < 2:
        return False
    mean = sum(amounts) / len(amounts)
    if mean == 0:
        return False
    max_dev = max(abs(a - mean) / mean * 100 for a in amounts)
    return max_dev <= tolerance_pct


def evaluate_fan_in_burst(
    *,
    account: Any,
    account_txns: list[Any],
    rule_config: dict[str, Any],
) -> RuleHit | None:
    """Fire when N+ unique senders transfer to this account inside the window."""
    params = rule_config["conditions"]["params"]
    min_senders = int(params["min_unique_senders"])
    window = timedelta(minutes=int(params["time_window_minutes"]))
    min_total = float(params["min_total_amount"])

    credits = [t for t in account_txns if t.dst_account_id == account.id]
    best_hit: RuleHit | None = None

    for group in _sliding_window_groups(credits, window=window):
        unique_senders = {t.src_account_id for t in group if t.src_account_id is not None}
        total_amount = sum(_as_float(t.amount) for t in group)
        if len(unique_senders) < min_senders or total_amount < min_total:
            continue
        amounts = [_as_float(t.amount) for t in group]
        modifier_map = {
            "unique_senders > 10": len(unique_senders) > 10,
            "total_amount > 2000000": total_amount > 2_000_000,
            "senders_from_multiple_banks == true": False,
            "all_similar_amounts == true": _amounts_similar(amounts),
        }
        evidence = {
            "account_name": getattr(account, "account_name", None) or getattr(account, "account_number", ""),
            "unique_senders": len(unique_senders),
            "total_amount": f"{total_amount:,.0f}",
            "time_window": int(params["time_window_minutes"]),
        }
        score, reasons = _apply_modifiers(rule_config, evidence, modifier_map)
        candidate = RuleHit(
            account_id=account.id,
            rule_code=rule_config["code"],
            score=score,
            weight=float(rule_config["weight"]),
            reasons=reasons,
            evidence=evidence,
            alert_title=_render_template(rule_config["alert_template"]["title"], evidence),
            alert_description=_render_template(rule_config["alert_template"]["description"], evidence),
        )
        if best_hit is None or candidate.score > best_hit.score:
            best_hit = candidate
    return best_hit
```

Run to verify PASS:

```bash
pytest tests/test_evaluator_core.py -k fan_in_burst -q
```

- [ ] **Step 2.11: Write test + implement `evaluate_fan_out_burst`**

Append test:

```python
FAN_OUT_CONFIG = {
    **FAN_IN_CONFIG,
    "code": "fan_out_burst",
    "conditions": {
        "trigger": "unique_recipients_from_sender",
        "params": {
            "min_unique_recipients": 5,
            "time_window_minutes": 30,
            "min_total_amount": 100_000,
        },
    },
    "scoring": {
        "base": 50,
        "modifiers": [
            {"when": "unique_recipients > 8", "add": 15, "reason": "More than 8 recipients"},
            {"when": "total_amount > 2000000", "add": 10, "reason": "Over 20 lakh"},
            {"when": "all_similar_amounts == true", "add": 10, "reason": "Similar amounts"},
        ],
    },
    "alert_template": {
        "title": "Fan-out: {account_name}",
        "description": "{unique_recipients} recipients <- BDT {total_amount}",
    },
}


def test_fan_out_burst_triggers_on_many_unique_recipients() -> None:
    sender = uuid.uuid4()
    account = make_account(sender, name="Distributor", age_days=200)
    txns = [
        make_txn(src=sender, dst=uuid.uuid4(), amount=60_000, posted_at=NOW + timedelta(minutes=i))
        for i in range(6)
    ]
    hit = evaluate_fan_out_burst(account=account, account_txns=txns, rule_config=FAN_OUT_CONFIG)
    assert hit is not None
    assert hit.evidence["unique_recipients"] == 6
```

Append evaluator:

```python
def evaluate_fan_out_burst(
    *,
    account: Any,
    account_txns: list[Any],
    rule_config: dict[str, Any],
) -> RuleHit | None:
    """Fire when N+ unique recipients receive from this account inside the window."""
    params = rule_config["conditions"]["params"]
    min_recipients = int(params["min_unique_recipients"])
    window = timedelta(minutes=int(params["time_window_minutes"]))
    min_total = float(params["min_total_amount"])

    debits = [t for t in account_txns if t.src_account_id == account.id]
    best_hit: RuleHit | None = None

    for group in _sliding_window_groups(debits, window=window):
        unique = {t.dst_account_id for t in group if t.dst_account_id is not None}
        total_amount = sum(_as_float(t.amount) for t in group)
        if len(unique) < min_recipients or total_amount < min_total:
            continue
        amounts = [_as_float(t.amount) for t in group]
        modifier_map = {
            "unique_recipients > 8": len(unique) > 8,
            "total_amount > 2000000": total_amount > 2_000_000,
            "recipients_at_different_banks == true": False,
            "all_similar_amounts == true": _amounts_similar(amounts),
        }
        evidence = {
            "account_name": getattr(account, "account_name", None) or getattr(account, "account_number", ""),
            "unique_recipients": len(unique),
            "total_amount": f"{total_amount:,.0f}",
            "time_window": int(params["time_window_minutes"]),
        }
        score, reasons = _apply_modifiers(rule_config, evidence, modifier_map)
        candidate = RuleHit(
            account_id=account.id,
            rule_code=rule_config["code"],
            score=score,
            weight=float(rule_config["weight"]),
            reasons=reasons,
            evidence=evidence,
            alert_title=_render_template(rule_config["alert_template"]["title"], evidence),
            alert_description=_render_template(rule_config["alert_template"]["description"], evidence),
        )
        if best_hit is None or candidate.score > best_hit.score:
            best_hit = candidate
    return best_hit
```

Run: `pytest tests/test_evaluator_core.py -k fan_out_burst -q` → PASS.

- [ ] **Step 2.12: Write test + implement `evaluate_structuring`**

Append test:

```python
STRUCTURING_CONFIG = {
    "code": "structuring",
    "title": "Structuring",
    "weight": 5.0,
    "conditions": {
        "trigger": "sub_threshold_clustering",
        "params": {
            "threshold_amount": 1_000_000,
            "margin_pct": 5,
            "min_count": 3,
            "time_window_hours": 24,
        },
    },
    "scoring": {
        "base": 45,
        "modifiers": [
            {"when": "count > 5", "add": 15, "reason": "More than 5 txns"},
            {"when": "same_channel == true", "add": 10, "reason": "Same channel"},
            {"when": "amounts_tightly_clustered == true", "add": 10, "reason": "Tight cluster"},
        ],
    },
    "severity": {"critical": 90, "high": 70, "medium": 50},
    "alert_template": {
        "title": "Structuring: {account_name}",
        "description": "{count} txns avg BDT {avg_amount}",
    },
}


def test_structuring_triggers_on_sub_threshold_cluster() -> None:
    account_id = uuid.uuid4()
    account = make_account(account_id, name="Structurer")
    txns = [
        make_txn(src=account_id, dst=uuid.uuid4(), amount=970_000, posted_at=NOW + timedelta(hours=i), channel="NPSB")
        for i in range(4)
    ]
    hit = evaluate_structuring(account=account, account_txns=txns, rule_config=STRUCTURING_CONFIG)
    assert hit is not None
    assert hit.evidence["count"] == 4
```

Append evaluator:

```python
def evaluate_structuring(
    *,
    account: Any,
    account_txns: list[Any],
    rule_config: dict[str, Any],
) -> RuleHit | None:
    """Fire when N+ transactions cluster just under the CTR threshold."""
    params = rule_config["conditions"]["params"]
    threshold = float(params["threshold_amount"])
    margin_pct = float(params["margin_pct"])
    min_count = int(params["min_count"])
    window = timedelta(hours=int(params["time_window_hours"]))

    lower_bound = threshold * (1 - margin_pct / 100)
    upper_bound = threshold  # just under

    candidates = [
        t
        for t in account_txns
        if t.src_account_id == account.id and lower_bound <= _as_float(t.amount) < upper_bound
    ]
    if len(candidates) < min_count:
        return None

    best_hit: RuleHit | None = None
    for group in _sliding_window_groups(candidates, window=window):
        if len(group) < min_count:
            continue
        amounts = [_as_float(t.amount) for t in group]
        channels = {getattr(t, "channel", None) for t in group}
        avg = sum(amounts) / len(amounts)
        modifier_map = {
            "count > 5": len(group) > 5,
            "same_channel == true": len(channels) == 1 and None not in channels,
            "amounts_tightly_clustered == true": _amounts_similar(amounts, tolerance_pct=2.0),
            "same_day == true": len({_txn_dt(t).date() for t in group}) == 1,
        }
        evidence = {
            "account_name": getattr(account, "account_name", None) or getattr(account, "account_number", ""),
            "count": len(group),
            "avg_amount": f"{avg:,.0f}",
            "hours": int(params["time_window_hours"]),
        }
        score, reasons = _apply_modifiers(rule_config, evidence, modifier_map)
        candidate = RuleHit(
            account_id=account.id,
            rule_code=rule_config["code"],
            score=score,
            weight=float(rule_config["weight"]),
            reasons=reasons,
            evidence=evidence,
            alert_title=_render_template(rule_config["alert_template"]["title"], evidence),
            alert_description=_render_template(rule_config["alert_template"]["description"], evidence),
        )
        if best_hit is None or candidate.score > best_hit.score:
            best_hit = candidate
    return best_hit
```

Run: `pytest tests/test_evaluator_core.py -k structuring -q` → PASS.

- [ ] **Step 2.13: Write test + implement `evaluate_layering`**

Append test:

```python
LAYERING_CONFIG = {
    "code": "layering",
    "title": "Layering",
    "weight": 7.0,
    "conditions": {
        "trigger": "structured_similar_transfers",
        "params": {
            "min_transfer_count": 5,
            "amount_variance_pct": 10,
            "time_window_hours": 48,
            "min_total_amount": 200_000,
        },
    },
    "scoring": {
        "base": 55,
        "modifiers": [
            {"when": "transfer_count > 10", "add": 15, "reason": "Over 10 transfers"},
            {"when": "amount_variance_pct < 5", "add": 10, "reason": "Tight variance"},
        ],
    },
    "severity": {"critical": 90, "high": 70, "medium": 50},
    "alert_template": {
        "title": "Layering: {account_name}",
        "description": "{transfer_count} transfers avg BDT {avg_amount}",
    },
}


def test_layering_triggers_on_similar_clustered_transfers() -> None:
    account_id = uuid.uuid4()
    account = make_account(account_id, name="Layer")
    txns = [
        make_txn(src=account_id, dst=uuid.uuid4(), amount=200_000 + (i * 100), posted_at=NOW + timedelta(hours=i))
        for i in range(6)
    ]
    hit = evaluate_layering(account=account, account_txns=txns, rule_config=LAYERING_CONFIG)
    assert hit is not None
    assert hit.evidence["transfer_count"] == 6
```

Append evaluator:

```python
def evaluate_layering(
    *,
    account: Any,
    account_txns: list[Any],
    rule_config: dict[str, Any],
) -> RuleHit | None:
    """Fire on clusters of similar-amount transfers within the window."""
    params = rule_config["conditions"]["params"]
    min_count = int(params["min_transfer_count"])
    variance_pct = float(params["amount_variance_pct"])
    window = timedelta(hours=int(params["time_window_hours"]))
    min_total = float(params["min_total_amount"])

    debits = [t for t in account_txns if t.src_account_id == account.id]
    best_hit: RuleHit | None = None

    for group in _sliding_window_groups(debits, window=window):
        if len(group) < min_count:
            continue
        amounts = [_as_float(t.amount) for t in group]
        total = sum(amounts)
        if total < min_total:
            continue
        if not _amounts_similar(amounts, tolerance_pct=variance_pct):
            continue
        avg = total / len(amounts)
        observed_variance = max(abs(a - avg) / avg * 100 for a in amounts) if avg else 0
        modifier_map = {
            "transfer_count > 10": len(group) > 10,
            "involves_multiple_banks == true": False,
            "amount_variance_pct < 5": observed_variance < 5,
            "circular_flow_detected == true": False,
        }
        evidence = {
            "account_name": getattr(account, "account_name", None) or getattr(account, "account_number", ""),
            "transfer_count": len(group),
            "avg_amount": f"{avg:,.0f}",
            "variance": f"{observed_variance:.1f}",
            "time_window": int(params["time_window_hours"]),
        }
        score, reasons = _apply_modifiers(rule_config, evidence, modifier_map)
        candidate = RuleHit(
            account_id=account.id,
            rule_code=rule_config["code"],
            score=score,
            weight=float(rule_config["weight"]),
            reasons=reasons,
            evidence=evidence,
            alert_title=_render_template(rule_config["alert_template"]["title"], evidence),
            alert_description=_render_template(rule_config["alert_template"]["description"], evidence),
        )
        if best_hit is None or candidate.score > best_hit.score:
            best_hit = candidate
    return best_hit
```

Run: `pytest tests/test_evaluator_core.py -k layering -q` → PASS.

- [ ] **Step 2.14: Write test + implement `evaluate_first_time_high_value`**

Append test:

```python
FIRST_TIME_CONFIG = {
    "code": "first_time_high_value",
    "title": "First-time high value",
    "weight": 4.0,
    "conditions": {
        "trigger": "new_beneficiary_high_value",
        "params": {
            "min_amount": 500_000,
            "max_account_age_days": 90,
            "no_prior_transactions_to_beneficiary": True,
        },
    },
    "scoring": {
        "base": 50,
        "modifiers": [
            {"when": "amount > 1000000", "add": 20, "reason": "Over 10 lakh"},
            {"when": "account_age_days < 30", "add": 10, "reason": "Very new"},
        ],
    },
    "severity": {"critical": 90, "high": 70, "medium": 50},
    "alert_template": {
        "title": "First-time high value: {account_name}",
        "description": "BDT {amount} -> {beneficiary_name} (age {account_age})",
    },
}


def test_first_time_high_value_triggers_for_new_sender_large_amount() -> None:
    account_id = uuid.uuid4()
    account = make_account(account_id, name="NewBie", age_days=20)
    beneficiary_id = uuid.uuid4()
    txns = [
        make_txn(src=account_id, dst=beneficiary_id, amount=1_500_000, posted_at=NOW),
    ]

    hit = evaluate_first_time_high_value(account=account, account_txns=txns, rule_config=FIRST_TIME_CONFIG)

    assert hit is not None
    assert hit.score >= 50 + 20 + 10
```

Append evaluator:

```python
def evaluate_first_time_high_value(
    *,
    account: Any,
    account_txns: list[Any],
    rule_config: dict[str, Any],
) -> RuleHit | None:
    """Fire on a large first-time transfer from a new account."""
    params = rule_config["conditions"]["params"]
    min_amount = float(params["min_amount"])
    max_age = int(params["max_account_age_days"])

    debits = sorted(
        (t for t in account_txns if t.src_account_id == account.id),
        key=_txn_dt,
    )
    if not debits:
        return None

    best_hit: RuleHit | None = None
    seen_beneficiaries: set[uuid.UUID] = set()
    for txn in debits:
        beneficiary = txn.dst_account_id
        amount = _as_float(txn.amount)
        is_first_time = beneficiary not in seen_beneficiaries
        seen_beneficiaries.add(beneficiary)
        if not is_first_time or amount < min_amount:
            continue
        age = _account_age_days(account, _txn_dt(txn))
        if age > max_age:
            continue

        modifier_map = {
            "amount > 1000000": amount > 1_000_000,
            "beneficiary_at_different_bank == true": False,
            "account_age_days < 30": age < 30,
            "beneficiary_is_flagged == true": False,
        }
        evidence = {
            "account_name": getattr(account, "account_name", None) or getattr(account, "account_number", ""),
            "amount": f"{amount:,.0f}",
            "beneficiary_name": str(beneficiary),
            "account_age": age,
        }
        score, reasons = _apply_modifiers(rule_config, evidence, modifier_map)
        candidate = RuleHit(
            account_id=account.id,
            rule_code=rule_config["code"],
            score=score,
            weight=float(rule_config["weight"]),
            reasons=reasons,
            evidence=evidence,
            alert_title=_render_template(rule_config["alert_template"]["title"], evidence),
            alert_description=_render_template(rule_config["alert_template"]["description"], evidence),
        )
        if best_hit is None or candidate.score > best_hit.score:
            best_hit = candidate
    return best_hit
```

Run: `pytest tests/test_evaluator_core.py -k first_time_high_value -q` → PASS.

- [ ] **Step 2.15: Write test + implement `evaluate_dormant_spike`**

Append test:

```python
DORMANT_CONFIG = {
    "code": "dormant_spike",
    "title": "Dormant spike",
    "weight": 5.0,
    "conditions": {
        "trigger": "balance_spike_after_dormancy",
        "params": {
            "dormant_days": 30,
            "max_prior_balance": 10_000,
            "min_spike_amount": 5_000_000,
        },
    },
    "scoring": {
        "base": 65,
        "modifiers": [
            {"when": "spike_amount > 10000000", "add": 15, "reason": "Over 1 crore"},
            {"when": "dormant_days > 90", "add": 10, "reason": "Long dormancy"},
        ],
    },
    "severity": {"critical": 90, "high": 70, "medium": 50},
    "alert_template": {
        "title": "Dormant spike: {account_name}",
        "description": "BDT {spike_amount} after {dormant_days}d",
    },
}


def test_dormant_spike_triggers_on_large_credit_after_dormancy() -> None:
    account_id = uuid.uuid4()
    account = make_account(account_id, name="Dormie")
    txns = [
        # 120 days ago: tiny balance signal
        make_txn(src=uuid.uuid4(), dst=account_id, amount=1_000, posted_at=NOW - timedelta(days=120)),
        # Today: large credit
        make_txn(src=uuid.uuid4(), dst=account_id, amount=12_000_000, posted_at=NOW),
    ]
    hit = evaluate_dormant_spike(account=account, account_txns=txns, rule_config=DORMANT_CONFIG)
    assert hit is not None
    assert hit.score >= 65 + 15 + 10
```

Append evaluator:

```python
def evaluate_dormant_spike(
    *,
    account: Any,
    account_txns: list[Any],
    rule_config: dict[str, Any],
) -> RuleHit | None:
    """Fire when a large credit arrives after a dormant period."""
    params = rule_config["conditions"]["params"]
    dormant_days = int(params["dormant_days"])
    min_spike = float(params["min_spike_amount"])

    credits = sorted(
        (t for t in account_txns if t.dst_account_id == account.id),
        key=_txn_dt,
    )
    if len(credits) < 2:
        return None

    best_hit: RuleHit | None = None
    for i in range(1, len(credits)):
        prior_activity = credits[:i]
        spike = credits[i]
        spike_amount = _as_float(spike.amount)
        if spike_amount < min_spike:
            continue
        last_prior = max(prior_activity, key=_txn_dt)
        gap_days = (_txn_dt(spike) - _txn_dt(last_prior)).days
        if gap_days < dormant_days:
            continue

        modifier_map = {
            "spike_amount > 10000000": spike_amount > 10_000_000,
            "multiple_npsb_sources == true": False,
            "dormant_days > 90": gap_days > 90,
            "immediate_outflow == true": False,
        }
        evidence = {
            "account_name": getattr(account, "account_name", None) or getattr(account, "account_number", ""),
            "spike_amount": f"{spike_amount:,.0f}",
            "dormant_days": gap_days,
            "source_count": 1,
        }
        score, reasons = _apply_modifiers(rule_config, evidence, modifier_map)
        candidate = RuleHit(
            account_id=account.id,
            rule_code=rule_config["code"],
            score=score,
            weight=float(rule_config["weight"]),
            reasons=reasons,
            evidence=evidence,
            alert_title=_render_template(rule_config["alert_template"]["title"], evidence),
            alert_description=_render_template(rule_config["alert_template"]["description"], evidence),
        )
        if best_hit is None or candidate.score > best_hit.score:
            best_hit = candidate
    return best_hit
```

Run: `pytest tests/test_evaluator_core.py -k dormant_spike -q` → PASS.

- [ ] **Step 2.16: Write test + implement `evaluate_proximity_to_bad`**

Append test:

```python
PROXIMITY_CONFIG = {
    "code": "proximity_to_bad",
    "title": "Proximity",
    "weight": 5.0,
    "conditions": {
        "trigger": "graph_proximity",
        "params": {"max_hops": 2, "target_entity_status": ["active", "confirmed"], "min_target_confidence": 0.6},
    },
    "scoring": {
        "base": 40,
        "modifiers": [
            {"when": "hop_distance == 1", "add": 25, "reason": "Direct link"},
            {"when": "multiple_flagged_neighbors == true", "add": 15, "reason": "Multiple"},
        ],
    },
    "severity": {"critical": 90, "high": 70, "medium": 50},
    "alert_template": {
        "title": "Proximity: {account_name}",
        "description": "{hop_distance} hops from {flagged_entity_name}",
    },
}


def test_proximity_fires_when_account_directly_connects_to_flagged() -> None:
    import networkx as nx
    from app.core.detection.evaluator import evaluate_proximity_to_bad

    account_id = uuid.uuid4()
    flagged_id = uuid.uuid4()
    account_entity_id = str(uuid.uuid4())
    flagged_entity_id = str(flagged_id)

    account = make_account(account_id, name="ProxAcct")
    # account_entity_id maps to the account (set via metadata)
    account.metadata_json = {"entity_id": account_entity_id}

    graph = nx.DiGraph()
    graph.add_node(account_entity_id, type="account", label="ProxAcct", risk_score=10, severity="low")
    graph.add_node(flagged_entity_id, type="account", label="Bad Guy", risk_score=95, severity="critical")
    graph.add_edge(account_entity_id, flagged_entity_id, relation="transacted")

    hit = evaluate_proximity_to_bad(
        account=account,
        account_txns=[],
        rule_config=PROXIMITY_CONFIG,
        graph=graph,
        flagged_entity_ids={flagged_entity_id},
    )
    assert hit is not None
    assert hit.evidence["hop_distance"] == 1
    assert hit.score >= 40 + 25
```

Append evaluator:

```python
def evaluate_proximity_to_bad(
    *,
    account: Any,
    account_txns: list[Any],
    rule_config: dict[str, Any],
    graph: nx.DiGraph | None = None,
    flagged_entity_ids: set[str] | None = None,
) -> RuleHit | None:
    """Fire when the account's entity is within max_hops of a flagged entity.

    Requires a pre-built graph and a set of flagged entity IDs. The pipeline
    passes ``account.metadata_json['entity_id']`` to link accounts to graph nodes.
    """
    if graph is None or not flagged_entity_ids:
        return None
    params = rule_config["conditions"]["params"]
    max_hops = int(params["max_hops"])

    entity_id = (getattr(account, "metadata_json", {}) or {}).get("entity_id")
    if not entity_id or entity_id not in graph.nodes:
        return None

    undirected = graph.to_undirected()
    best_distance: int | None = None
    flagged_reached: list[str] = []
    for target in flagged_entity_ids:
        if target == entity_id or target not in undirected.nodes:
            continue
        try:
            distance = nx.shortest_path_length(undirected, source=entity_id, target=target)
        except nx.NetworkXNoPath:
            continue
        if distance <= max_hops:
            flagged_reached.append(target)
            if best_distance is None or distance < best_distance:
                best_distance = distance

    if best_distance is None:
        return None

    flagged_name = graph.nodes[flagged_reached[0]].get("label", "flagged entity")
    modifier_map = {
        "hop_distance == 1": best_distance == 1,
        "target_confidence > 0.8": False,
        "multiple_flagged_neighbors == true": len(flagged_reached) > 1,
    }
    evidence = {
        "account_name": getattr(account, "account_name", None) or getattr(account, "account_number", ""),
        "hop_distance": best_distance,
        "flagged_entity_name": flagged_name,
        "confidence": "n/a",
    }
    score, reasons = _apply_modifiers(rule_config, evidence, modifier_map)
    return RuleHit(
        account_id=account.id,
        rule_code=rule_config["code"],
        score=score,
        weight=float(rule_config["weight"]),
        reasons=reasons,
        evidence=evidence,
        alert_title=_render_template(rule_config["alert_template"]["title"], evidence),
        alert_description=_render_template(rule_config["alert_template"]["description"], evidence),
    )
```

Run: `pytest tests/test_evaluator_core.py -k proximity -q` → PASS.

- [ ] **Step 2.17: Write test + implement top-level `evaluate_accounts`**

Append test:

```python
ALL_RULES = [
    RAPID_CASHOUT_CONFIG,
    FAN_IN_CONFIG,
    FAN_OUT_CONFIG,
    STRUCTURING_CONFIG,
    LAYERING_CONFIG,
    FIRST_TIME_CONFIG,
    DORMANT_CONFIG,
    PROXIMITY_CONFIG,
]


def test_evaluate_accounts_returns_hits_across_multiple_rules() -> None:
    account_id = uuid.uuid4()
    other = uuid.uuid4()
    account = make_account(account_id, name="MultiHit", age_days=30)

    txns = [
        make_txn(src=other, dst=account_id, amount=2_000_000, posted_at=NOW),
        make_txn(src=account_id, dst=uuid.uuid4(), amount=1_900_000, posted_at=NOW + timedelta(minutes=10)),
    ]

    hits = evaluate_accounts(
        accounts=[account],
        transactions=txns,
        rules=ALL_RULES,
    )

    assert any(h.rule_code == "rapid_cashout" for h in hits)
    assert all(isinstance(h, RuleHit) for h in hits)
```

Append evaluator:

```python
_EVALUATOR_BY_TRIGGER: dict[str, Any] = {
    "credit_then_debit_percentage": evaluate_rapid_cashout,
    "unique_senders_to_recipient": evaluate_fan_in_burst,
    "unique_recipients_from_sender": evaluate_fan_out_burst,
    "sub_threshold_clustering": evaluate_structuring,
    "structured_similar_transfers": evaluate_layering,
    "new_beneficiary_high_value": evaluate_first_time_high_value,
    "balance_spike_after_dormancy": evaluate_dormant_spike,
    "graph_proximity": evaluate_proximity_to_bad,
}


def evaluate_accounts(
    *,
    accounts: list[Any],
    transactions: list[Any],
    rules: list[dict[str, Any]],
    graph: nx.DiGraph | None = None,
    flagged_entity_ids: set[str] | None = None,
) -> list[RuleHit]:
    """Top-level entry point: run every rule against every account.

    Returns a flat list of RuleHit across all accounts and rules. Callers
    (typically ``pipeline.run_scan_pipeline``) group by account for scoring.
    """
    grouped = _group_transactions_by_account(transactions)
    hits: list[RuleHit] = []
    for account in accounts:
        account_txns = grouped.get(account.id, [])
        for rule in rules:
            trigger = rule["conditions"]["trigger"]
            evaluator = _EVALUATOR_BY_TRIGGER.get(trigger)
            if evaluator is None:
                continue
            if trigger == "graph_proximity":
                hit = evaluator(
                    account=account,
                    account_txns=account_txns,
                    rule_config=rule,
                    graph=graph,
                    flagged_entity_ids=flagged_entity_ids,
                )
            else:
                hit = evaluator(
                    account=account,
                    account_txns=account_txns,
                    rule_config=rule,
                )
            if hit is not None:
                hits.append(hit)
    return hits
```

Run all evaluator tests:

```bash
pytest tests/test_evaluator_core.py -q
```

Expected: all tests pass.

- [ ] **Step 2.18: Commit**

```bash
git add engine/app/core/detection/rule_hit.py engine/app/core/detection/evaluator.py engine/tests/test_evaluator_core.py
git commit -m "feat(detection): real rule evaluator with 8 rule implementations and RuleHit output"
```

---

## Task 4: Cross-bank matcher

**Dependency:** Task 3 complete.

**Files:**
- Rewrite: `engine/app/core/matcher.py`
- Create: `engine/tests/test_matcher_core.py`

**Completion criteria:** `run_cross_bank_matching` detects entities with 2+ `reporting_orgs`, upserts `matches` rows, and returns `(list[Match], list[Alert])`.

- [ ] **Step 4.1: Write failing test for `run_cross_bank_matching`**

Create `engine/tests/test_matcher_core.py`:

```python
import uuid
from types import SimpleNamespace

import pytest

from app.core.matcher import run_cross_bank_matching
from app.models.alert import Alert
from app.models.entity import Entity
from app.models.match import Match


class FakeScalarsResult:
    def __init__(self, items: list[object]) -> None:
        self._items = items

    def first(self) -> object | None:
        return self._items[0] if self._items else None


class FakeExecResult:
    def __init__(self, items: list[object]) -> None:
        self._items = items

    def scalars(self) -> FakeScalarsResult:
        return FakeScalarsResult(self._items)


class FakeSession:
    def __init__(self, existing_match: Match | None = None) -> None:
        self.added: list[object] = []
        self.existing_match = existing_match

    async def execute(self, *_args, **_kwargs) -> FakeExecResult:
        return FakeExecResult([self.existing_match] if self.existing_match else [])

    def add(self, obj: object) -> None:
        self.added.append(obj)

    async def flush(self) -> None:
        return None


def make_entity(*, reporting_orgs: list[uuid.UUID], total_exposure: float = 500_000) -> Entity:
    return Entity(
        id=uuid.uuid4(),
        entity_type="account",
        canonical_value="178143000701",
        display_value="178143000701",
        display_name="Rizwana",
        confidence=0.7,
        source="str_cross_ref",
        reporting_orgs=reporting_orgs,
        report_count=len(reporting_orgs),
        total_exposure=total_exposure,
        tags=[],
        metadata_json={},
    )


@pytest.mark.asyncio
async def test_matcher_creates_match_when_two_orgs_report_entity() -> None:
    org_a = uuid.uuid4()
    org_b = uuid.uuid4()
    entity = make_entity(reporting_orgs=[org_a, org_b])
    session = FakeSession()
    str_report = SimpleNamespace(id=uuid.uuid4(), subject_bank="Bank A", subject_account="178143000701")

    matches, alerts = await run_cross_bank_matching(
        session,
        entities=[entity],
        str_report=str_report,
        org_id=org_a,
    )

    assert len(matches) == 1
    match = matches[0]
    assert match.match_type == "account"
    assert match.match_key == "178143000701"
    assert set(match.involved_org_ids) == {org_a, org_b}
    assert match.match_count == 2
    assert match.risk_score >= 50
    assert len(alerts) == 1
    assert alerts[0].source_type == "cross_bank"
    assert alerts[0].alert_type == "cross_bank_match"


@pytest.mark.asyncio
async def test_matcher_skips_entity_reported_by_single_org() -> None:
    single_org = uuid.uuid4()
    entity = make_entity(reporting_orgs=[single_org])
    session = FakeSession()
    str_report = SimpleNamespace(id=uuid.uuid4(), subject_bank="Bank A", subject_account="X")

    matches, alerts = await run_cross_bank_matching(
        session, entities=[entity], str_report=str_report, org_id=single_org
    )

    assert matches == []
    assert alerts == []
```

- [ ] **Step 4.2: Run — expect FAIL (ImportError)**

```bash
cd engine
pytest tests/test_matcher_core.py -q
```

Expected: fails because `run_cross_bank_matching` doesn't exist.

- [ ] **Step 4.3: Rewrite `matcher.py`**

Replace `engine/app/core/matcher.py` contents with:

```python
"""Cross-bank matcher.

Detects when a resolved Entity appears in STRs from 2+ different banks and
creates/updates a ``matches`` row plus a ``cross_bank`` alert.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.alert import Alert
from app.models.entity import Entity
from app.models.match import Match


def _severity_for(score: int) -> str:
    if score >= 90:
        return "critical"
    if score >= 70:
        return "high"
    if score >= 50:
        return "medium"
    return "low"


def _compute_match_score(*, match_count: int, total_exposure: float) -> int:
    score = 50 + (10 * match_count)
    if total_exposure > 10_000_000:
        score += 20
    return min(100, score)


async def _find_existing_match(
    session: AsyncSession,
    *,
    match_type: str,
    match_key: str,
) -> Match | None:
    stmt = (
        select(Match)
        .where(Match.match_type == match_type)
        .where(Match.match_key == match_key)
        .limit(1)
    )
    try:
        result = await session.execute(stmt)
        return result.scalars().first()
    except Exception:
        return None


def _build_alert(
    *,
    entity: Entity,
    match: Match,
    org_id: uuid.UUID,
) -> Alert:
    bank_count = match.match_count
    return Alert(
        id=uuid.uuid4(),
        org_id=org_id,
        source_type="cross_bank",
        source_id=match.id,
        entity_id=entity.id,
        title=f"Cross-bank match: {entity.display_value}",
        description=(
            f"{entity.display_name or entity.display_value} has been reported by "
            f"{bank_count} distinct institutions."
        ),
        alert_type="cross_bank_match",
        risk_score=int(match.risk_score or 0),
        severity=match.severity or "low",
        status="open",
        reasons=[
            {
                "rule": "cross_bank",
                "score": int(match.risk_score or 0),
                "explanation": (
                    f"{entity.display_name or entity.display_value} appears in STRs from "
                    f"{bank_count} banks with total exposure BDT "
                    f"{float(entity.total_exposure or 0):,.0f}."
                ),
            }
        ],
    )


async def run_cross_bank_matching(
    session: AsyncSession,
    *,
    entities: list[Entity],
    str_report: Any | None,
    org_id: uuid.UUID,
) -> tuple[list[Match], list[Alert]]:
    """Scan ``entities`` for cross-bank appearances and upsert matches.

    Returns ``(new_or_updated_matches, new_alerts)``. The caller owns the
    surrounding transaction and must commit.
    """
    matches_out: list[Match] = []
    alerts_out: list[Alert] = []
    now = datetime.now(UTC)

    for entity in entities:
        reporting = list(entity.reporting_orgs or [])
        if len(set(reporting)) < 2:
            continue

        existing = await _find_existing_match(
            session,
            match_type=entity.entity_type,
            match_key=entity.canonical_value,
        )
        involved_orgs = list(set(reporting))
        involved_strs: list[uuid.UUID] = []
        if str_report is not None and getattr(str_report, "id", None) is not None:
            involved_strs.append(str_report.id)

        total_exposure = float(entity.total_exposure or 0)
        match_count = len(involved_orgs)
        score = _compute_match_score(match_count=match_count, total_exposure=total_exposure)
        severity = _severity_for(score)
        previous_severity = existing.severity if existing is not None else None

        if existing is None:
            match = Match(
                id=uuid.uuid4(),
                entity_id=entity.id,
                match_key=entity.canonical_value,
                match_type=entity.entity_type,
                involved_org_ids=involved_orgs,
                involved_str_ids=involved_strs,
                match_count=match_count,
                total_exposure=total_exposure,
                risk_score=score,
                severity=severity,
                status="new",
                notes=[],
                detected_at=now,
            )
            session.add(match)
        else:
            merged_orgs = list({*existing.involved_org_ids, *involved_orgs})
            merged_strs = list({*existing.involved_str_ids, *involved_strs})
            existing.involved_org_ids = merged_orgs
            existing.involved_str_ids = merged_strs
            existing.match_count = len(merged_orgs)
            existing.total_exposure = max(float(existing.total_exposure or 0), total_exposure)
            existing.risk_score = _compute_match_score(
                match_count=existing.match_count, total_exposure=float(existing.total_exposure)
            )
            existing.severity = _severity_for(existing.risk_score)
            existing.detected_at = now
            match = existing

        matches_out.append(match)

        escalated = (
            existing is None
            or (previous_severity or "") != (match.severity or "")
            and _severity_rank(match.severity) > _severity_rank(previous_severity)
        )
        if escalated:
            alerts_out.append(_build_alert(entity=entity, match=match, org_id=org_id))

    for alert in alerts_out:
        session.add(alert)
    if matches_out or alerts_out:
        await session.flush()

    return matches_out, alerts_out


def _severity_rank(severity: str | None) -> int:
    return {"low": 0, "medium": 1, "high": 2, "critical": 3}.get(severity or "", 0)
```

- [ ] **Step 4.4: Run matcher tests — expect PASS**

```bash
cd engine
pytest tests/test_matcher_core.py -q
```

Expected: both tests pass. If the `involved_org_ids` assertion fails due to order, the test uses `set(...)` already — if not, update it.

- [ ] **Step 4.5: Commit**

```bash
git add engine/app/core/matcher.py engine/tests/test_matcher_core.py
git commit -m "feat(detection): cross-bank matcher with match upsert and alert generation"
```

---

## Task 5: Scorer

**Dependency:** Task 2 complete (scorer consumes `RuleHit`).

**Files:**
- Rewrite: `engine/app/core/detection/scorer.py`
- Create: `engine/tests/test_scorer_core.py`

- [ ] **Step 5.1: Write failing scorer test**

Create `engine/tests/test_scorer_core.py`:

```python
import uuid

import pytest

from app.core.detection.rule_hit import RuleHit
from app.core.detection.scorer import calculate_risk_score


def hit(rule: str, score: int, weight: float) -> RuleHit:
    return RuleHit(
        account_id=uuid.uuid4(),
        rule_code=rule,
        score=score,
        weight=weight,
        reasons=[],
        evidence={},
        alert_title=f"{rule} alert",
        alert_description=f"{rule} fired",
    )


def test_empty_hits_returns_low() -> None:
    score, severity, reasons = calculate_risk_score([])
    assert score == 0
    assert severity == "low"
    assert reasons == []


def test_weighted_average_with_two_rules() -> None:
    hits = [hit("rapid_cashout", 90, 8.0), hit("proximity_to_bad", 50, 5.0)]
    score, severity, reasons = calculate_risk_score(hits)

    # Weighted average = (90*8 + 50*5) / (8+5) = (720+250)/13 = 74.6 -> 74
    assert score == 74
    assert severity == "high"
    # Higher weighted contribution comes first
    assert reasons[0]["rule"] == "rapid_cashout"
    assert reasons[0]["weighted_contribution"] > reasons[1]["weighted_contribution"]


def test_score_clamped_at_100() -> None:
    hits = [hit("rapid_cashout", 200, 1.0)]  # Impossible but test the clamp
    score, severity, _ = calculate_risk_score(hits)
    assert score == 100
    assert severity == "critical"


def test_critical_at_90() -> None:
    hits = [hit("layering", 95, 7.0)]
    score, severity, _ = calculate_risk_score(hits)
    assert severity == "critical"
```

- [ ] **Step 5.2: Run — expect FAIL**

```bash
cd engine
pytest tests/test_scorer_core.py -q
```

Expected: fails because the current scorer signature is different.

- [ ] **Step 5.3: Rewrite `scorer.py`**

Replace `engine/app/core/detection/scorer.py` contents with:

```python
"""Risk scorer.

Combines weighted rule hits into a final risk score per account.
"""

from __future__ import annotations

from typing import Any

from app.core.detection.rule_hit import RuleHit


def calculate_risk_score(rule_hits: list[RuleHit]) -> tuple[int, str, list[dict[str, Any]]]:
    """Return ``(score, severity, reasons)`` for a bag of rule hits.

    Formula: weighted average of per-hit scores, clamped to [0, 100].
    Severity bands: >=90 critical, >=70 high, >=50 medium, else low.
    Reasons are sorted by weighted contribution (highest first) for UI ranking.
    """
    if not rule_hits:
        return 0, "low", []

    weight_sum = sum(hit.weight for hit in rule_hits)
    if weight_sum <= 0:
        return 0, "low", []

    weighted_sum = sum(hit.score * hit.weight for hit in rule_hits)
    score = min(100, int(weighted_sum / weight_sum))

    if score >= 90:
        severity = "critical"
    elif score >= 70:
        severity = "high"
    elif score >= 50:
        severity = "medium"
    else:
        severity = "low"

    reasons: list[dict[str, Any]] = []
    for hit in sorted(rule_hits, key=lambda h: h.score * h.weight, reverse=True):
        reasons.append(
            {
                "rule": hit.rule_code,
                "score": hit.score,
                "weight": hit.weight,
                "weighted_contribution": round(hit.score * hit.weight / weight_sum * 100, 1),
                "reasons": hit.reasons,
                "evidence": hit.evidence,
                "explanation": hit.alert_description,
            }
        )

    return score, severity, reasons
```

- [ ] **Step 5.4: Run scorer tests — expect PASS**

```bash
cd engine
pytest tests/test_scorer_core.py -q
```

Expected: all 4 tests pass.

- [ ] **Step 5.5: Commit**

```bash
git add engine/app/core/detection/scorer.py engine/tests/test_scorer_core.py
git commit -m "feat(detection): weighted risk scorer over RuleHit list"
```

---

## Task 6: Pipeline orchestration

**Dependency:** Tasks 2, 3, 4, 5 complete.

**Files:**
- Rewrite: `engine/app/core/pipeline.py`
- Create: `engine/tests/test_pipeline_core.py`

**Completion criteria:** `run_str_pipeline` resolves identifiers and calls the matcher. `run_scan_pipeline` loads transactions, builds the graph, runs evaluator, scores, creates alerts, updates the `detection_run` row. Pipeline tests use fake sessions.

- [ ] **Step 6.1: Rewrite `pipeline.py`**

Replace `engine/app/core/pipeline.py` contents with:

```python
"""Detection pipelines.

Two entry points:

- ``run_str_pipeline``: called from ``services.str_reports.submit_str_report``.
  Resolves the STR subject identifiers to entities and runs cross-bank matching.

- ``run_scan_pipeline``: called from ``services.scanning.queue_run``. Loads
  the org's transactions and accounts, runs every active rule, resolves flagged
  accounts to entities, runs cross-bank matching, creates alerts, and updates
  the ``detection_runs`` row.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.detection.evaluator import evaluate_accounts
from app.core.detection.loader import load_rules
from app.core.detection.rule_hit import RuleHit
from app.core.detection.scorer import calculate_risk_score
from app.core.matcher import run_cross_bank_matching
from app.core.resolver import resolve_identifier, resolve_identifiers_from_str
from app.models.account import Account
from app.models.alert import Alert
from app.models.audit import AuditLog
from app.models.connection import Connection
from app.models.detection_run import DetectionRun
from app.models.entity import Entity
from app.models.match import Match
from app.models.str_report import STRReport
from app.models.transaction import Transaction

_RULES_PATH = Path(__file__).resolve().parent / "detection" / "rules"

_SCAN_SCORE_THRESHOLD = 50


def _load_active_rules() -> list[dict[str, Any]]:
    return load_rules(_RULES_PATH)


async def run_str_pipeline(
    session: AsyncSession,
    *,
    str_report: STRReport,
    org_id: uuid.UUID,
) -> dict[str, Any]:
    """Resolve identifiers from an STR, run cross-bank matching, update the STR."""
    entities = await resolve_identifiers_from_str(
        session, str_report=str_report, org_id=org_id
    )
    matches, alerts = await run_cross_bank_matching(
        session, entities=entities, str_report=str_report, org_id=org_id
    )

    entity_ids = [e.id for e in entities]
    str_report.matched_entity_ids = entity_ids
    str_report.cross_bank_hit = len(matches) > 0
    if matches:
        str_report.auto_risk_score = max(int(m.risk_score or 0) for m in matches)

    session.add(
        AuditLog(
            org_id=org_id,
            user_id=None,
            action="pipeline.str.completed",
            resource_type="str_report",
            resource_id=str_report.id,
            details={
                "entities_resolved": len(entities),
                "cross_bank_matches": len(matches),
                "new_alerts": len(alerts),
            },
        )
    )

    return {
        "entities": entities,
        "matches": matches,
        "alerts": alerts,
    }


async def _load_accounts_and_transactions(
    session: AsyncSession, *, org_id: uuid.UUID
) -> tuple[list[Account], list[Transaction]]:
    accounts_stmt = select(Account).where(Account.org_id == org_id)
    accounts_result = await session.execute(accounts_stmt)
    accounts = list(accounts_result.scalars().all())

    txns_stmt = select(Transaction).where(Transaction.org_id == org_id)
    txns_result = await session.execute(txns_stmt)
    transactions = list(txns_result.scalars().all())

    return accounts, transactions


async def _load_graph_inputs(
    session: AsyncSession,
) -> tuple[list[Entity], list[Connection], set[str]]:
    ent_result = await session.execute(select(Entity))
    entities = list(ent_result.scalars().all())
    con_result = await session.execute(select(Connection))
    connections = list(con_result.scalars().all())
    flagged_ids = {
        str(e.id)
        for e in entities
        if (e.risk_score or 0) >= 70 or (e.severity in {"high", "critical"})
    }
    return entities, connections, flagged_ids


async def _resolve_flagged_account_as_entity(
    session: AsyncSession,
    *,
    account: Account,
    org_id: uuid.UUID,
    score: int,
    severity: str,
    reasons: list[dict[str, Any]],
) -> Entity:
    entity = await resolve_identifier(
        session,
        entity_type="account",
        raw_value=account.account_number,
        org_id=org_id,
        source="pattern_scan",
        display_name=account.account_name or account.account_number,
    )
    entity.risk_score = max(int(entity.risk_score or 0), score)
    entity.severity = severity
    metadata = dict(entity.metadata_json or {})
    metadata["last_scan_reasons"] = reasons
    metadata["last_scan_at"] = datetime.now(UTC).isoformat()
    entity.metadata_json = metadata

    # Link account to its entity for proximity lookups on subsequent runs
    acct_meta = dict(account.metadata_json or {})
    acct_meta["entity_id"] = str(entity.id)
    account.metadata_json = acct_meta

    return entity


def _build_scan_alert(
    *,
    entity: Entity,
    account: Account,
    org_id: uuid.UUID,
    hits: list[RuleHit],
    score: int,
    severity: str,
    reasons: list[dict[str, Any]],
) -> Alert:
    top_hit = max(hits, key=lambda h: h.score * h.weight)
    return Alert(
        id=uuid.uuid4(),
        org_id=org_id,
        source_type="scan",
        source_id=None,
        entity_id=entity.id,
        title=top_hit.alert_title or f"Scan alert: {account.account_number}",
        description=top_hit.alert_description or "Multiple detection rules fired",
        alert_type=top_hit.rule_code,
        risk_score=score,
        severity=severity,
        status="open",
        reasons=reasons,
    )


async def run_scan_pipeline(
    session: AsyncSession,
    *,
    run_id: uuid.UUID,
    org_id: uuid.UUID,
) -> dict[str, Any]:
    """Execute the full scan detection pipeline for an org.

    - Loads the org's accounts + transactions.
    - Builds the shared graph + flagged entity set.
    - Runs every YAML rule via ``evaluate_accounts``.
    - For each account whose combined score >= threshold:
      * resolves the account as an Entity
      * runs cross-bank matching on the resolved entity
      * writes a scan Alert row
    - Updates the DetectionRun row with results summary.
    """
    run: DetectionRun | None = await session.get(DetectionRun, run_id)
    if run is None:
        raise ValueError(f"DetectionRun {run_id} not found")

    run.status = "running"
    run.started_at = datetime.now(UTC)

    accounts, transactions = await _load_accounts_and_transactions(session, org_id=org_id)
    _, _, flagged_entity_ids = await _load_graph_inputs(session)

    # Build a lightweight graph from Entity metadata for proximity lookups.
    # We import lazily to avoid a cycle with the graph package.
    from app.core.graph.builder import build_graph

    ent_rows = (await session.execute(select(Entity))).scalars().all()
    con_rows = (await session.execute(select(Connection))).scalars().all()
    graph = build_graph(list(ent_rows), list(con_rows))

    # Link accounts to entity IDs via metadata if already resolved
    rules = _load_active_rules()
    hits = evaluate_accounts(
        accounts=accounts,
        transactions=transactions,
        rules=rules,
        graph=graph,
        flagged_entity_ids=flagged_entity_ids,
    )

    hits_by_account: dict[uuid.UUID, list[RuleHit]] = {}
    for hit in hits:
        hits_by_account.setdefault(hit.account_id, []).append(hit)

    flagged_accounts_out: list[dict[str, Any]] = []
    alerts_created: list[Alert] = []
    matches_touched: list[Match] = []

    account_by_id = {acct.id: acct for acct in accounts}

    for account_id, account_hits in hits_by_account.items():
        account = account_by_id.get(account_id)
        if account is None:
            continue
        score, severity, reasons = calculate_risk_score(account_hits)
        if score < _SCAN_SCORE_THRESHOLD:
            continue

        entity = await _resolve_flagged_account_as_entity(
            session,
            account=account,
            org_id=org_id,
            score=score,
            severity=severity,
            reasons=reasons,
        )
        matches, alerts = await run_cross_bank_matching(
            session, entities=[entity], str_report=None, org_id=org_id
        )
        matches_touched.extend(matches)

        alert = _build_scan_alert(
            entity=entity,
            account=account,
            org_id=org_id,
            hits=account_hits,
            score=score,
            severity=severity,
            reasons=reasons,
        )
        session.add(alert)
        alerts_created.append(alert)
        alerts_created.extend(alerts)

        total_exposure_hit = sum(
            float(h.evidence.get("total_credit", 0) or 0) for h in account_hits
        )
        flagged_accounts_out.append(
            {
                "entity_id": str(entity.id),
                "account_number": account.account_number,
                "account_name": account.account_name or account.account_number,
                "score": score,
                "severity": severity,
                "summary": alert.description,
                "matched_banks": max(1, len(entity.reporting_orgs or [])),
                "total_exposure": float(entity.total_exposure or total_exposure_hit),
                "tags": list(entity.tags or []),
                "linked_alert_id": str(alert.id),
                "linked_case_id": None,
            }
        )

    run.status = "completed"
    run.completed_at = datetime.now(UTC)
    run.accounts_scanned = len(accounts)
    run.tx_count = len(transactions)
    run.alerts_generated = len(alerts_created)
    run.results = {
        "summary": (
            f"{len(flagged_accounts_out)} account candidate(s) flagged from "
            f"{len(accounts)} accounts and {len(transactions)} transactions."
        ),
        "selected_rules": [rule["code"] for rule in rules],
        "flagged_accounts": flagged_accounts_out,
    }

    session.add(
        AuditLog(
            org_id=org_id,
            user_id=None,
            action="pipeline.scan.completed",
            resource_type="detection_run",
            resource_id=run.id,
            details={
                "accounts_scanned": run.accounts_scanned,
                "alerts_generated": run.alerts_generated,
                "flagged_count": len(flagged_accounts_out),
            },
        )
    )

    return {
        "run_id": str(run.id),
        "flagged_accounts": flagged_accounts_out,
        "alerts": alerts_created,
        "matches": matches_touched,
    }
```

- [ ] **Step 6.2: Write a smoke test for `run_str_pipeline`**

Create `engine/tests/test_pipeline_core.py`:

```python
import uuid
from types import SimpleNamespace

import pytest


class FakeScalarsResult:
    def __init__(self, items: list[object]) -> None:
        self._items = items

    def first(self) -> object | None:
        return self._items[0] if self._items else None

    def all(self) -> list[object]:
        return list(self._items)


class FakeExecResult:
    def __init__(self, items: list[object]) -> None:
        self._items = items

    def scalars(self) -> FakeScalarsResult:
        return FakeScalarsResult(self._items)


class FakeSession:
    def __init__(self) -> None:
        self.added: list[object] = []

    async def execute(self, *_args, **_kwargs) -> FakeExecResult:
        return FakeExecResult([])

    def add(self, obj: object) -> None:
        self.added.append(obj)

    async def flush(self) -> None:
        return None


@pytest.mark.asyncio
async def test_run_str_pipeline_resolves_entities_and_flags_single_bank_without_match() -> None:
    from app.core.pipeline import run_str_pipeline

    org_id = uuid.uuid4()
    session = FakeSession()
    report = SimpleNamespace(
        id=uuid.uuid4(),
        org_id=org_id,
        subject_name="Rizwana Enterprise",
        subject_account="178143000701",
        subject_bank="DBBL",
        subject_phone=None,
        subject_wallet=None,
        subject_nid=None,
        matched_entity_ids=[],
        cross_bank_hit=False,
        auto_risk_score=None,
    )

    result = await run_str_pipeline(session, str_report=report, org_id=org_id)

    assert len(result["entities"]) >= 1
    assert result["matches"] == []
    assert result["alerts"] == []
    assert report.cross_bank_hit is False
    assert len(report.matched_entity_ids) >= 1
```

- [ ] **Step 6.3: Run pipeline test — expect PASS**

```bash
cd engine
pytest tests/test_pipeline_core.py -q
```

Expected: PASS. (The scan pipeline test is deferred to Task 8 end-to-end verification — it requires a real DB.)

- [ ] **Step 6.4: Commit**

```bash
git add engine/app/core/pipeline.py engine/tests/test_pipeline_core.py
git commit -m "feat(detection): real STR and scan pipeline orchestration"
```

---

## Task 7: Wire pipelines into services

**Dependency:** Task 6 complete.

**Files:**
- Modify: `engine/app/services/str_reports.py`
- Modify: `engine/app/services/scanning.py`

**Completion criteria:** `submit_str_report` calls `run_str_pipeline` after status flip. `queue_run` creates a pending `DetectionRun` and calls `run_scan_pipeline`. Existing service tests still pass.

- [ ] **Step 7.1: Modify `submit_str_report`**

In `engine/app/services/str_reports.py`, add to the import block at the top:

```python
from app.core.pipeline import run_str_pipeline
```

Then replace the body of `submit_str_report` (lines 373–404 in the current file) to call the pipeline before committing:

```python
async def submit_str_report(
    session: AsyncSession,
    *,
    report_id: str,
    user: AuthenticatedUser,
    ip: str | None,
) -> STRMutationResponse:
    report, org_name = await _fetch_report_with_org(session, report_id)
    _ensure_editable(report, user)
    _ensure_submission_ready(report)
    previous_status = report.status
    report.status = "submitted"
    report.submitted_by = _as_uuid(user.user_id)
    report.reported_at = report.reported_at or datetime.now(UTC)
    report.metadata_json = _append_lifecycle_event(
        report.metadata_json or {},
        action="submitted",
        user=user,
        from_status=previous_status,
        to_status=report.status,
    )

    org_uuid = _require_uuid(user.org_id, "Authenticated user is missing a valid organization id.")
    try:
        pipeline_result = await run_str_pipeline(
            session, str_report=report, org_id=org_uuid
        )
    except Exception as exc:  # defensive: do not block submission on pipeline failure
        pipeline_result = {"entities": [], "matches": [], "alerts": [], "error": str(exc)}

    await _record_audit(
        session,
        report=report,
        user=user,
        action="str_report.submitted",
        details={
            "from_status": previous_status,
            "to_status": report.status,
            "entities_resolved": len(pipeline_result.get("entities", [])),
            "cross_bank_matches": len(pipeline_result.get("matches", [])),
        },
        ip=ip,
    )
    await session.commit()
    await session.refresh(report)
    return STRMutationResponse(report=serialize_report_detail(report, org_name))
```

- [ ] **Step 7.2: Modify `queue_run`**

In `engine/app/services/scanning.py`, add to the imports:

```python
from app.core.pipeline import run_scan_pipeline
```

Replace `queue_run` (lines 241–291) with:

```python
async def queue_run(
    session: AsyncSession,
    *,
    user: AuthenticatedUser,
    request: ScanQueueRequest,
) -> ScanQueueResponse:
    org_uuid = _as_uuid(user.org_id)
    if org_uuid is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid organization id.")

    now = datetime.now(UTC)
    run = DetectionRun(
        org_id=org_uuid,
        run_type="upload",
        status="pending",
        file_name=(request.file_name or f"{user.org_type}-network-scan-{now:%Y%m%d-%H%M%S}.csv").strip(),
        file_url=None,
        tx_count=0,
        accounts_scanned=0,
        alerts_generated=0,
        results={"summary": "queued", "selected_rules": list(request.selected_rules), "flagged_accounts": []},
        triggered_by=_as_uuid(user.user_id),
        started_at=None,
        completed_at=None,
        error=None,
    )
    session.add(run)
    await session.flush()

    try:
        await run_scan_pipeline(session, run_id=run.id, org_id=org_uuid)
    except Exception as exc:
        run.status = "failed"
        run.error = str(exc)
        run.completed_at = datetime.now(UTC)

    await session.commit()
    await session.refresh(run)

    return ScanQueueResponse(
        run=DetectionRunDetail.model_validate(_serialize_run_detail(run)),
        message=(
            "Detection pipeline executed over current transactions."
            if run.status == "completed"
            else f"Detection run ended with status {run.status}."
        ),
    )
```

- [ ] **Step 7.3: Run the entire engine test suite**

```bash
cd engine
pytest -q
```

Expected: all tests pass, including the existing `test_str_phase4` and `test_scan_phase5` suites. If any of those fail because of the new pipeline calls (e.g., they assert a specific `queue_run` response message), update the assertions to match the new wording. Do NOT revert the pipeline wiring.

- [ ] **Step 7.4: Commit**

```bash
git add engine/app/services/str_reports.py engine/app/services/scanning.py
git commit -m "feat(services): wire STR and scan pipelines into submission + queue flows"
```

---

## Task 8: End-to-end verification against DBBL synthetic

**Dependency:** All previous tasks complete.

**Goal:** Prove that loading the DBBL synthetic dataset and triggering a scan produces real rule hits, real alerts, and real cross-bank matches — via the HTTP API, not via direct Python calls.

**Files:** none modified. This is a verification step whose only artifact is the commit log entry and a short verification note at `docs/superpowers/plans/2026-04-15-intelligence-core-verification.md`.

- [ ] **Step 8.1: Boot the engine locally against the dev database**

```bash
cd engine
uvicorn app.main:app --reload --port 8000
```

Leave running in a separate terminal.

- [ ] **Step 8.2: Confirm readiness**

```bash
curl -s http://localhost:8000/ready | python -m json.tool
```

Expected: `auth`, `database`, and `storage` all report `ok`. (`worker` and AI providers may report degraded — that's acceptable for this verification.)

- [ ] **Step 8.3: Load DBBL synthetic dataset**

If synthetic data is not already loaded, apply it:

```bash
cd engine
python -m seed.load_dbbl_synthetic --apply
```

Expected output: counts of upserted organizations, entities, connections, accounts, transactions, str_reports, matches, alerts, cases. Re-running is idempotent.

- [ ] **Step 8.4: Sanity-check transactions exist**

Run this inline with a Python one-liner (do not create a script):

```bash
cd engine
python -c "import asyncio; from sqlalchemy import func, select; from app.database import SessionLocal; from app.models.transaction import Transaction
async def main():
    async with SessionLocal() as s:
        count = (await s.execute(select(func.count()).select_from(Transaction))).scalar()
        print('transactions:', count)
asyncio.run(main())"
```

Expected: a non-zero transaction count. If zero, the seeder did not populate transactions — stop and investigate.

- [ ] **Step 8.5: Trigger a scan via the API**

Obtain a valid Supabase JWT for a BFIU regulator user (or use the demo persona header if demo mode is enabled), then:

```bash
curl -s -X POST http://localhost:8000/scan/runs \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"file_name":"dbbl-verification.csv","selected_rules":["rapid_cashout","fan_in_burst","fan_out_burst","structuring","layering","dormant_spike","first_time_high_value","proximity_to_bad"]}' | python -m json.tool
```

Expected: a JSON response with `run.status == "completed"`, `run.alerts_generated > 0`, `run.accounts_scanned > 0`, and `run.flagged_accounts` as a non-empty array. Each flagged account should have a non-null `linked_alert_id`.

- [ ] **Step 8.6: Confirm alerts were persisted**

```bash
curl -s http://localhost:8000/alerts -H "Authorization: Bearer <TOKEN>" | python -m json.tool | head -80
```

Expected: at least one alert with `source_type: "scan"` and a populated `reasons` array whose first entry contains a `rule` field matching one of the 8 rule codes. If all alerts still show `source_type: "str_enrichment"` (from the synthetic seeder), the pipeline did not create new alerts — investigate by checking the engine logs for the `pipeline.scan.completed` audit action.

- [ ] **Step 8.7: Confirm cross-bank matches (if any)**

```bash
curl -s http://localhost:8000/intelligence/matches -H "Authorization: Bearer <TOKEN>" | python -m json.tool | head -60
```

Expected: `matches` array includes at least the synthetic matches from the seeder. If the DBBL synthetic includes entities reported by multiple banks, the scan pipeline should have upserted those matches — look for entries with `match_count >= 2`.

- [ ] **Step 8.8: Submit an STR and verify entity resolution**

```bash
curl -s -X POST http://localhost:8000/str-reports \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "subject_name":"Test Subject",
    "subject_account":"178143000701",
    "subject_phone":"+8801712345678",
    "category":"money_laundering",
    "narrative":"Verification STR for pipeline end-to-end check."
  }' | python -m json.tool
```

Capture the returned `report.id`. Then:

```bash
curl -s -X POST http://localhost:8000/str-reports/<REPORT_ID>/submit \
  -H "Authorization: Bearer <TOKEN>" | python -m json.tool
```

Expected: response contains `matched_entity_ids` with at least one UUID and `cross_bank_hit` matching whether the synthetic dataset reports this account from multiple banks.

- [ ] **Step 8.9: Write verification note**

Create `docs/superpowers/plans/2026-04-15-intelligence-core-verification.md`:

```markdown
# Intelligence Core Verification Log — 2026-04-15

## Summary
End-to-end verification of Tasks 1-7 against the DBBL synthetic dataset.

## Environment
- Engine: localhost:8000, feature/intelligence-core branch
- Database: <supabase project id or local>
- Dataset: DBBL synthetic (seed/generated/dbbl_synthetic)

## Results
- /ready: auth=ok, database=ok, storage=ok
- Transactions loaded: <COUNT>
- Scan run id: <UUID>
- Accounts scanned: <N>
- Alerts generated: <N>
- Cross-bank matches: <N>
- STR verification report id: <UUID>
- STR matched_entity_ids: <LIST>
- STR cross_bank_hit: <true|false>

## Rule firings observed
- rapid_cashout: <count>
- fan_in_burst: <count>
- fan_out_burst: <count>
- structuring: <count>
- layering: <count>
- dormant_spike: <count>
- first_time_high_value: <count>
- proximity_to_bad: <count>

## Notes
<any anomalies, zero-count rules to investigate post-merge>
```

Fill in the counts from Step 8.5–8.8.

- [ ] **Step 8.10: Commit verification log**

```bash
git add docs/superpowers/plans/2026-04-15-intelligence-core-verification.md
git commit -m "docs(intelligence-core): capture e2e verification run on DBBL synthetic"
```

- [ ] **Step 8.11: Merge to main**

```bash
git checkout main
git pull --ff-only origin main
git merge --no-ff feature/intelligence-core -m "feat: real intelligence core (tasks 1-7) with DBBL synthetic verification"
git push origin main
```

Expected: CI runs `engine` + `web` jobs. If any fail, diagnose on main — do NOT force-push or revert without understanding the failure.

---

## Post-merge

- Watch the Render deploy for `kestrel-engine` and confirm `/ready` stays green on production.
- Run `POST /admin/synthetic-backfill` against production if production hasn't already been seeded.
- Trigger a production `POST /scan/runs` and confirm it produces the same rule firings as the local verification.
- Tasks 8–9 from the original spec (SAR/CTR types + PDF export) remain — create a follow-up plan for those.

---

## Self-Review Checklist

Before dispatching execution:

1. **Spec coverage:** Tasks 1–7 each map to a section in the CORE prompt. Task 1 covers all 8 YAML rewrites (1.4–1.11). Task 2 covers all 8 evaluators (2.7–2.16). Task 3 covers normalization + resolve + connection linking. Task 4 covers match upsert + alert generation. Task 5 covers weighted average + severity bands. Task 6 covers both STR and scan pipelines. Task 7 wires both services. No spec section is missing.

2. **Placeholders:** no TBD/TODO/"similar to"/"add error handling" strings in any task body.

3. **Type consistency:** `RuleHit` is defined once in Task 2.1 and referenced consistently. `normalize_identifier` signature matches across Task 3 and Task 6. `run_str_pipeline` and `run_scan_pipeline` signatures match between Task 6 and Task 7.

4. **Known gaps kicked down the road (intentional):**
   - Modifier evaluation is a dict lookup, not a true expression evaluator. Good enough for the 8 hard-coded rules; a real DSL is future work.
   - `cross_bank_debit`, `senders_from_multiple_banks`, `beneficiary_at_different_bank`, `beneficiary_is_flagged`, `circular_flow_detected`, `multiple_npsb_sources`, `immediate_outflow`, `target_confidence` modifiers are hardcoded to `False`. They can only become true once richer transaction metadata + graph lookups are wired in.
   - Scan pipeline runs over **all** org transactions every time — no incremental re-runs. Acceptable for the demo.
   - No Celery: detection runs synchronously in the request path. For the DBBL synthetic (~100k transactions) this should complete in under 10 seconds; if it doesn't, that's a separate optimization task.
