# Kestrel Intelligence Core — Make It Real

You are working on the Kestrel codebase. The scaffold is complete but the intelligence core — the part that actually detects fraud, resolves entities, matches across banks, and scores risk — is currently stubs. Your job is to replace every stub with real, working logic.

Read the entire `engine/app/core/` directory, `engine/app/services/investigation.py`, `engine/app/services/scanning.py`, `engine/app/services/str_reports.py`, and `supabase/migrations/001_schema.sql` before writing any code. Understand the models, the schema, and the existing service layer.

Do NOT change any existing API routes, schemas, or model definitions unless absolutely necessary. The frontend and API surface are stable. You're implementing the engine internals.

---

## Task 1: Real detection rule definitions

The current YAML rules in `engine/app/core/detection/rules/` only have `code`, `title`, `weight`, and `threshold`. They need full condition logic.

Rewrite each YAML file with this structure:

### rapid_cashout.yaml
```yaml
code: rapid_cashout
title: Rapid cash-out
category: velocity
weight: 8.0
description: >
  Flags accounts that receive credit and transfer out ≥80% within 60 minutes.
  Classic mule account behavior — money lands and exits immediately.

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
      reason: "Credit exceeds ৳10 lakh"
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
  description: "{debit_pct}% of ৳{credit_amount} debited within {time_gap} minutes via {debit_channel}"
```

### fan_in_burst.yaml
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
      reason: "Total inflow exceeds ৳20 lakh"
    - when: senders_from_multiple_banks == true
      add: 10
      reason: "Senders span multiple banks (NPSB transfers)"
    - when: all_similar_amounts == true
      add: 10
      reason: "All incoming amounts are suspiciously similar (±10%)"

severity:
  critical: 90
  high: 70
  medium: 50

alert_template:
  title: "Fan-in burst: {account_name}"
  description: "{unique_senders} unique senders transferred ৳{total_amount} within {time_window} minutes"
```

### fan_out_burst.yaml
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
      reason: "All outgoing amounts are suspiciously similar (±10%)"
    - when: recipients_at_different_banks == true
      add: 10
      reason: "Recipients span multiple banks"
    - when: total_amount > 2000000
      add: 10
      reason: "Total outflow exceeds ৳20 lakh"

severity:
  critical: 90
  high: 70
  medium: 50

alert_template:
  title: "Fan-out burst: {account_name}"
  description: "{unique_recipients} recipients received ৳{total_amount} within {time_window} minutes"
```

### dormant_spike.yaml
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
      reason: "Spike exceeds ৳1 crore"
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
  description: "Account dormant {dormant_days} days, then received ৳{spike_amount} from {source_count} sources"
```

### layering.yaml
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
      reason: "Circular flow detected — funds return to origin path"

severity:
  critical: 90
  high: 70
  medium: 50

alert_template:
  title: "Layering detected: {account_name}"
  description: "{transfer_count} transfers averaging ৳{avg_amount} (±{variance}%) within {time_window} hours"
```

### proximity_to_bad.yaml
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
    target_entity_status: ["active", "confirmed"]
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
  description: "{hop_distance} hop(s) from flagged entity {flagged_entity_name} (confidence: {confidence})"
```

### structuring.yaml
```yaml
code: structuring
title: Structuring
category: pattern
weight: 5.0
description: >
  Multiple transactions just under the CTR reporting threshold (৳10 lakh)
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
  description: "{count} transactions averaging ৳{avg_amount} (just under ৳10 lakh threshold) within {hours} hours"
```

### first_time_high_value.yaml
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
      reason: "Amount exceeds ৳10 lakh"
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
  description: "৳{amount} sent to new beneficiary {beneficiary_name} (account age: {account_age} days)"
```

---

## Task 2: Real detection evaluator

Replace `engine/app/core/detection/evaluator.py` entirely. The new evaluator must:

1. Load all YAML rules via the existing `loader.py`
2. Accept a list of transactions (SQLAlchemy `Transaction` objects) and a list of accounts (`Account` objects)
3. For each account, evaluate every active rule by analyzing that account's transactions:
   - **rapid_cashout**: Find credits followed by ≥X% debits within time window. Calculate actual debit percentage and time gap.
   - **fan_in_burst**: Count unique source accounts sending to this account within time window.
   - **fan_out_burst**: Count unique destination accounts this account sends to within time window.
   - **dormant_spike**: Check if account had low activity/balance before a sudden large credit.
   - **layering**: Find clusters of transfers with similar amounts (within variance %) in time window.
   - **structuring**: Find transactions just under the threshold amount within time window.
   - **first_time_high_value**: Find large transfers to accounts with no prior transaction history.
   - **proximity_to_bad**: This rule requires graph data — accept an optional NetworkX graph and check hop distance to flagged nodes.
4. For each rule that triggers, calculate the score: `base + sum(applicable_modifiers)`
5. Return a list of `RuleHit` dataclasses:
   ```python
   @dataclass
   class RuleHit:
       account_id: str
       rule_code: str
       score: int
       weight: float
       reasons: list[dict]  # [{modifier, score_added, reason_text}]
       evidence: dict        # {debit_pct, time_gap_min, credit_amount, ...}
       alert_title: str      # Formatted from alert_template
       alert_description: str
   ```

Implementation approach:
- Create a function per rule type: `evaluate_rapid_cashout(account_txns, rule_config) -> RuleHit | None`
- Group transactions by account before evaluating
- Use pandas-free pure Python (transactions are already loaded as SQLAlchemy objects — iterate and compute)
- The evaluator should be deterministic: same input → same output

---

## Task 3: Real entity resolver

Replace `engine/app/core/resolver.py`. The resolver is called when:
- A new STR is submitted (extract subject identifiers → find or create entities)
- A pattern scan completes (flagged accounts → find or create entities)
- An analyst manually adds an entity

The resolver must:

1. Accept an identifier (account number, phone, wallet, NID, or name) and its type
2. Normalize the value:
   - Account numbers: strip spaces, uppercase
   - Phone numbers: normalize to standard format (e.g., +880XXXXXXXXXX or 01XXXXXXXXX)
   - NID: strip spaces, numbers only
   - Names: lowercase, trim, collapse whitespace
   - Wallets: strip spaces, uppercase
3. Check for exact match in `entities` table on `(entity_type, canonical_value)`
4. If no exact match and type is 'person' or 'business', do fuzzy match using `pg_trgm` similarity on `display_name` (threshold: 0.6 similarity)
5. If match found:
   - Update `last_seen`, increment `report_count`
   - Add the reporting org to `reporting_orgs` array if not already present
   - If reporting org is new, set `cross_bank_hit = true` on any linked STRs
   - Recalculate `total_exposure`
   - Return the existing entity
6. If no match found:
   - Create new entity with the normalized value
   - Set initial confidence based on source (str_cross_ref: 0.7, manual: 0.8, pattern_scan: 0.6, system: 0.5)
   - Return the new entity
7. After resolving, check if this entity should be linked to other entities:
   - If STR has both `subject_account` and `subject_phone`, create a connection between the account entity and phone entity with relation `same_owner`
   - If STR has `subject_nid`, link NID to account and phone with `same_owner`
   - These connections build the graph that network analysis operates on

```python
async def resolve_identifiers_from_str(
    session: AsyncSession,
    str_report: STRReport,
    org_id: str,
) -> list[Entity]:
    """
    Given an STR report, extract all identifiers (account, phone, wallet, NID, name),
    resolve each to an entity (find existing or create new), create connections between
    them, and return the list of resolved entities.
    """
```

---

## Task 4: Real cross-bank matcher

Replace `engine/app/core/matcher.py`. The matcher runs after entity resolution to detect when the same identifier appears in STRs from different banks.

1. After resolving entities for a new STR, check each resolved entity:
   - How many distinct `org_id` values are in its `reporting_orgs` array?
   - If ≥ 2, this is a cross-bank match
2. For each cross-bank match:
   - Check if a `matches` row already exists for this `(match_type, match_key)`
   - If exists: update `match_count`, `involved_org_ids`, `involved_str_ids`, recalculate `total_exposure` and `risk_score`
   - If new: create a `matches` row with:
     - `match_key` = the canonical entity value
     - `match_type` = the entity type
     - `entity_id` = the entity UUID
     - `involved_org_ids` = array of all reporting org UUIDs
     - `involved_str_ids` = array of all linked STR UUIDs
     - `match_count` = number of banks reporting
     - `risk_score` = base 50 + (10 × match_count) + (20 if total_exposure > 10_000_000)
     - `severity` = critical if score ≥ 90, high if ≥ 70, medium if ≥ 50, low otherwise
3. If a new cross-bank match is created or an existing one escalates in severity, generate an alert:
   - `source_type` = 'cross_bank'
   - `alert_type` = 'cross_bank_match'
   - `title` = "Cross-bank match: {entity_value} flagged by {match_count} banks"
   - `reasons` = [{rule: "cross_bank", score: X, reason: "Flagged by Bank A, Bank B, Bank C"}]

```python
async def run_cross_bank_matching(
    session: AsyncSession,
    entities: list[Entity],
    str_report: STRReport,
    org_id: str,
) -> list[Match]:
    """
    Check resolved entities for cross-bank appearances.
    Create or update match records. Generate alerts for new matches.
    """
```

---

## Task 5: Real scorer

Replace `engine/app/core/detection/scorer.py`. The scorer combines rule hits into a final risk score per entity.

```python
def calculate_risk_score(rule_hits: list[RuleHit]) -> tuple[int, str, list[dict]]:
    """
    Combine multiple rule hits into a single risk score for an entity.
    
    Formula: min(100, sum(hit.score * hit.weight) / sum(hit.weight))
    
    Returns: (score: int, severity: str, reasons: list[dict])
    Where reasons is the combined explainability array for the alert.
    """
    if not rule_hits:
        return 0, "low", []
    
    weighted_sum = sum(hit.score * hit.weight for hit in rule_hits)
    weight_sum = sum(hit.weight for hit in rule_hits)
    score = min(100, int(weighted_sum / weight_sum)) if weight_sum > 0 else 0
    
    severity = (
        "critical" if score >= 90 else
        "high" if score >= 70 else
        "medium" if score >= 50 else
        "low"
    )
    
    reasons = []
    for hit in sorted(rule_hits, key=lambda h: h.score * h.weight, reverse=True):
        reasons.append({
            "rule": hit.rule_code,
            "score": hit.score,
            "weight": hit.weight,
            "weighted_contribution": round(hit.score * hit.weight / weight_sum * 100, 1),
            "reasons": hit.reasons,
            "evidence": hit.evidence,
        })
    
    return score, severity, reasons
```

---

## Task 6: Real pipeline

Replace `engine/app/core/pipeline.py`. The pipeline orchestrates the full detection flow.

### Pipeline A: STR submission pipeline
When a new STR is submitted (`str_reports.py` → `submit_str_report`):
1. Call `resolve_identifiers_from_str()` → get list of resolved entities
2. Call `run_cross_bank_matching()` → check for cross-bank hits
3. Update the STR record with `matched_entity_ids` and `cross_bank_hit`
4. If cross-bank match found, auto-set `auto_risk_score` on the STR
5. Log to audit trail

### Pipeline B: Pattern scan pipeline
When transactions are uploaded for scanning (`scanning.py` → run scan):
1. Parse uploaded file (CSV/XLSX/PDF) into transaction records
2. Insert transactions into `transactions` table with the `run_id`
3. Create or resolve account records for all unique accounts
4. Load all active detection rules
5. Build NetworkX graph from transactions (via `graph/builder.py`)
6. For each account:
   a. Get that account's transactions
   b. Run evaluator with all rules → list of `RuleHit`
   c. If any rules triggered, run scorer → final score
   d. If score ≥ threshold, resolve the account as an entity via resolver
   e. Run cross-bank matcher on resolved entity
   f. Generate alert with full explainability
7. Update `detection_runs` record with results
8. Return summary

```python
async def run_str_pipeline(
    session: AsyncSession,
    str_report: STRReport,
    org_id: str,
) -> dict:
    """Called when an STR is submitted. Resolves entities, checks cross-bank matches."""

async def run_scan_pipeline(
    session: AsyncSession,
    run_id: str,
    org_id: str,
    user: AuthenticatedUser,
) -> dict:
    """Called when a pattern scan completes parsing. Runs full detection → scoring → alerting."""
```

---

## Task 7: Wire the pipeline into existing services

Update `engine/app/services/str_reports.py`:
- In `submit_str_report()`, after changing status to 'submitted', call `run_str_pipeline()`
- Store the returned `matched_entity_ids` on the STR record

Update `engine/app/services/scanning.py`:
- After file parsing is complete and transactions are inserted, call `run_scan_pipeline()`
- Store results summary on the `detection_runs` record

Do NOT change the function signatures or return types of the service functions. The routers and schemas depend on them.

---

## Task 8: Add SAR and CTR report type support

The `str_reports` table and model currently handle only STRs. goAML handles 10+ report types. For a goAML replacement, at minimum add SAR and CTR support.

### Option A (recommended — minimal schema change):
Add a `report_type` column to `str_reports`:
```sql
ALTER TABLE str_reports ADD COLUMN report_type text NOT NULL DEFAULT 'str' 
  CHECK (report_type IN ('str','sar','ctr','tbml','complaint','ier','internal','adverse_media','escalated'));
```

Rename the table conceptually (in code comments and documentation) to `reports` but keep the physical table name `str_reports` to avoid migration complexity.

Update the model, schemas, and services to accept `report_type`. The create/update endpoints should accept a `report_type` field. The list endpoint should allow filtering by `report_type`.

### For CTR specifically:
CTRs are high-volume (38 million per year in Bangladesh). They need a separate lightweight table:
```sql
CREATE TABLE cash_transaction_reports (
    id uuid primary key default gen_random_uuid(),
    org_id uuid not null references organizations(id),
    account_number text not null,
    account_name text,
    transaction_date date not null,
    amount numeric(18,2) not null,
    currency text default 'BDT',
    transaction_type text, -- deposit | withdrawal
    branch_code text,
    reported_at timestamptz default now(),
    metadata jsonb default '{}'
);
CREATE INDEX idx_ctr_org ON cash_transaction_reports(org_id);
CREATE INDEX idx_ctr_account ON cash_transaction_reports(account_number);
CREATE INDEX idx_ctr_date ON cash_transaction_reports(transaction_date DESC);
ALTER TABLE cash_transaction_reports ENABLE ROW LEVEL SECURITY;
CREATE POLICY ctr_org ON cash_transaction_reports FOR ALL 
  USING (org_id = auth_org_id() OR is_regulator());
```

Add a basic CTR router with bulk import endpoint (banks submit thousands of CTRs daily).

---

## Task 9: Real PDF export

Replace the stub in `engine/app/services/pdf_export.py` with a working PDF generator using WeasyPrint.

Create an HTML template for a case pack that includes:
- Case header (case_ref, title, severity, status, dates)
- Summary narrative
- Linked entities table (entity type, value, risk score, reporting banks)
- Linked alerts table (alert type, risk score, rule hits)
- Linked STRs table (report ref, bank, amount, category)
- Timeline of events
- Generated timestamp and "Confidential — BFIU" watermark

```python
async def generate_case_pdf(
    session: AsyncSession,
    case_id: str,
) -> bytes:
    """Generate a PDF case pack for the given case ID. Returns PDF bytes."""
```

---

## Rules for implementation

1. Every function must have a docstring explaining what it does
2. Use `async/await` consistently — all database operations are async via SQLAlchemy
3. Log significant events to `audit_log` table (entity resolved, match created, alert generated)
4. Handle edge cases: empty transaction lists, accounts with no transactions, entities with no connections
5. Do NOT use pandas — keep it pure SQLAlchemy + Python stdlib
6. All monetary values are in BDT (Bangladeshi Taka)
7. All timestamps are timezone-aware (UTC)
8. Test each component by running the DBBL synthetic seeder and verifying alerts are generated

## Verification

After implementation, running this should work end-to-end:
```bash
cd engine
python -m seed.load_dbbl_synthetic --apply  # Load synthetic data
# Then via API:
# POST /api/v1/str-reports  → should trigger entity resolution + cross-bank matching
# POST /api/v1/scan/runs    → should trigger full detection pipeline
# GET /api/v1/alerts        → should return real alerts with explainability
# GET /api/v1/intelligence/matches → should show cross-bank matches
```
