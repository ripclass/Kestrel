# Intelligence Core Verification Log — 2026-04-15

## Status

**Tasks 1–7 complete on `feature/intelligence-core`.** Live API verification
deferred to post-deploy on Render preview/production.

## Branch

- Branch: `feature/intelligence-core`
- Commits ahead of `main`: 8
- Working tree: clean

## Unit test coverage

Final run (local, `pytest -q`):

```
94 passed in 6.20s
```

Net delta vs main (50 tests baseline):

| Suite | Tests | Status |
|-------|-------|--------|
| `test_rules_loader_core.py` | 9 | pass |
| `test_resolver_core.py` | 14 | pass |
| `test_evaluator_core.py` | 13 | pass |
| `test_matcher_core.py` | 3 | pass |
| `test_scorer_core.py` | 4 | pass |
| `test_pipeline_core.py` | 1 | pass |
| **Subtotal new** | **44** | |
| Existing baseline | 50 | pass (no regressions) |
| **Total** | **94** | |

## What unit tests cover

- **Loader:** all 8 YAMLs parse with full schema (code, title, category, weight,
  description, conditions{trigger,params}, scoring{base,modifiers}, severity,
  alert_template). Schema validation failures raise `ValueError`.
- **Resolver:** 9 normalization forms (account/wallet/phone/nid/person/business/
  unknown), exact-match find-or-create on `(entity_type, canonical_value)`,
  fuzzy match path for person/business via `pg_trgm`, `resolve_identifiers_from_str`
  emits 4 entities + 6 directed `same_owner` connections for an STR with
  account/phone/nid/name.
- **Evaluator:** every rule's trigger and one no-trigger path. Score clamping
  at 100 verified for rapid_cashout (60+45 → 100).
- **Matcher:** single-org skip, two-org match creates row + alert, four-org +
  high exposure clamps score to 100 with critical severity.
- **Scorer:** empty hits → `(0,"low",[])`, weighted average correct
  ((90×8 + 50×5)/13 = 74), clamp at 100, severity bands.
- **Pipeline:** `run_str_pipeline` resolves entities and writes audit log
  without cross-bank match for single-org submission.

## What unit tests do NOT cover (must be verified post-deploy)

The unit tests use `SimpleNamespace` fakes and a `FakeSession`. They do not
verify behavior against the actual SQLAlchemy models, RLS policies, asyncpg
quirks, or the DBBL synthetic dataset. The following must be checked
manually after the feature branch deploys to a Render preview or after merge
to main:

### Live API checks

1. **`GET /ready`** — confirm `auth=ok, database=ok, storage=ok`. Worker may
   still be degraded (no real Celery tasks yet), that's expected.
2. **`POST /scan/runs`** as a regulator (BFIU) user with the synthetic dataset
   already loaded:
   - Response `run.status == "completed"`.
   - `run.alerts_generated > 0`.
   - `run.flagged_accounts` is a non-empty array.
   - Each flagged account has a non-null `linked_alert_id`.
3. **`GET /alerts`** — confirm at least one alert with `source_type == "scan"`
   and `reasons[0].rule` matching one of the 8 rule codes.
4. **`GET /intelligence/matches`** — confirm `match_count >= 2` rows surface;
   the synthetic dataset includes cross-bank entities.
5. **`POST /str-reports`** + `POST /str-reports/{id}/submit`:
   - Response `cross_bank_hit` true if subject_account is in the synthetic
     cross-bank set.
   - `matched_entity_ids` contains at least one UUID.
   - Audit log row `pipeline.str.completed` with non-zero `entities_resolved`.

### Rule firings to spot-check

If the synthetic dataset is well-shaped, expect:
- `rapid_cashout` — should fire (DBBL synthetic includes the rapid_cashout
  risk profile, see `engine/seed/dbbl_synthetic.py`).
- `dormant_spike` — should fire on burst_activity statements.
- `proximity_to_bad` — only fires after at least one rule already populated
  a flagged entity (chicken-and-egg on first run; second run picks it up).

If `rapid_cashout` shows zero hits despite being in the synthetic profile,
something in the temporal grouping is wrong — investigate `_txn_dt` and the
sliding window in `evaluate_rapid_cashout`.

## Known gaps (intentional, deferred)

These were called out in the plan's self-review and were NOT fixed in this
branch:

- Modifier conditions are dict-keyed lookups, not a real expression DSL.
  Sufficient for the 8 hardcoded rules.
- `cross_bank_debit`, `senders_from_multiple_banks`, `recipients_at_different_banks`,
  `beneficiary_at_different_bank`, `beneficiary_is_flagged`, `circular_flow_detected`,
  `multiple_npsb_sources`, `immediate_outflow`, `target_confidence > 0.8` modifiers
  are wired to `False` in the evaluator. They become functional once richer
  transaction metadata + graph lookups are wired in.
- `proximity_to_bad` requires `account.metadata_json["entity_id"]` to be set.
  Newly-resolved scan accounts get this assigned, but accounts that have never
  been scanned won't have it — so proximity has a one-scan warm-up before it
  starts firing.
- Scan pipeline runs over **all** of the org's transactions every invocation —
  no incremental/run-scoped filtering. Acceptable for the synthetic dataset
  but would need to be addressed before a real ingest pipeline.
- `app/core/alerter.py` is now orphaned (not imported anywhere). Leaving it
  in place to avoid scope creep; can be removed in a follow-up.
- File upload path is still missing — `queue_run` accepts the request but
  ignores any uploaded file. Detection runs against whatever transactions
  are already in the DB. This is a known item in CLAUDE.md "What to work on
  next" priority 2.

## Risk assessment for merge

Low → medium:

- **Low:** Pure-function modules (loader, scorer, evaluator, normalize_identifier).
  These have unit-test coverage and no DB dependency.
- **Medium:** `submit_str_report` and `queue_run` now call into the pipeline
  synchronously. If the pipeline raises an unexpected exception against real
  DB shapes, both flows have try/except wrappers that fall back gracefully:
  - STR submission still completes (only enrichment is skipped).
  - Scan run is marked `status="failed"` with the exception in `error`.
- **Medium:** The pipeline writes new rows (Entity, Connection, Match, Alert,
  AuditLog) on every scan and STR submission. RLS policies on `entities` /
  `connections` / `matches` are shared (no org filter), so writes by a regulator
  user are visible to all banks — by design, but worth confirming on the first
  production scan.
- **No schema migrations** in this branch. RLS policies and constraints
  unchanged.

## Rollback plan

If anything breaks after merge:

```bash
git checkout main
git revert -m 1 <merge_commit_sha>
git push origin main
```

This reverts the merge in a single new commit and triggers a redeploy with
the previous working state. No data migrations to roll back.
