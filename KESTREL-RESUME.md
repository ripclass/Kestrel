# Kestrel — resume prompt

Start the next session with this. Full state in `CLAUDE.md`.

---

## Context

Sovereign Ledger rebrand + goAML coverage patch + intelligence-core are all shipped to prod on `main` (commit `dd37cc4`). Engine on Render, web on Vercel (`kestrel-nine.vercel.app`), Supabase prod `bmlyqlkzeuoglyvfythg`. 10 migrations applied. 157 commits. Build + 95/95 pytest passing.

## Constraint this session

**No AI provider keys** (budget). OpenAI + Anthropic both show `missing_config` on `/ready` — heuristic fallback covers every AI surface. Don't plan work that needs a live model call to verify. Everything below is pure infrastructure, detection correctness, or UI polish.

Do **not** spend time on: the demo film (needs real AI to look credible), live AI evaluations, M2M goAML adapter (needs a BFIU endpoint).

## Priority stack — finish the product

Work top-down. Commit + push after each task so prod moves forward incrementally. Verify each against the existing synthetic baseline (**377 accounts, 547 txns → 10 flagged accounts, 11 alerts**) — any divergence is a regression.

### 1. Wire the 4 remaining `False` modifiers

`engine/app/core/detection/evaluator.py`. Four modifier conditions are still hardcoded `False` because they need graph lookups the evaluator doesn't currently do:

- `proximity_to_flagged <= 2` (rapid_cashout)
- `involves_multiple_banks` (layering)
- `circular_flow_detected` (layering)
- `target_confidence > 0.8` (proximity_to_bad)

The pipeline already builds the resolved entity graph (`engine/app/core/graph/builder.py` — networkx DiGraph). Thread it into the evaluator so these four conditions evaluate against it. Add unit tests under `engine/tests/`. Run the synthetic dataset: expect alert counts to go up (more rules firing), not down.

### 2. Wire Celery Beat scheduled rule execution

Currently the worker only has `worker.ping`. Every detection runs inline on the FastAPI request path. Real product needs scheduled execution.

- `engine/app/tasks/scan_tasks.py` is an empty shell. Move `run_scan_pipeline` into a Celery task there.
- Populate `app.tasks.celery_app.celery_app.conf.beat_schedule` with the three declared jobs `/admin/schedules` already surfaces: nightly scan, daily digest, weekly compliance.
- Add a `kestrel-beat` service to `engine/render.yaml` (Celery Beat process — separate from worker).
- Update `services/schedules.py` so the declared jobs flip from `not_configured` to `scheduled` once the beat schedule is populated.

Verify: redeploy engine → `/admin/schedules` shows all three jobs as `scheduled` with next-run timestamps → manually trigger one via Celery and watch `detection_runs` get a new row.

### 3. Delete orphaned `core/alerter.py` + clean `seed/fixtures.py`

`engine/app/core/alerter.py` is not imported by any production path — left only because `seed/fixtures.py` references it. The fixtures themselves are orphaned since the DB-backed typologies migration (004). Confirm no imports outside fixtures.py, then delete both. Run pytest + `python -c "from app.main import app"` before pushing.

### 4. Rule expression DSL on `match_definitions`

Table + CRUD UI already exist (`/admin/match-definitions`). `match_definitions.rule_expression` is a free-text column with no evaluator wiring — `POST /match-definitions/{id}/execute` records an execution row but doesn't actually run anything. Define a small DSL (JSON-shaped condition tree, or a safe subset of Python expressions via `simpleeval` — no `eval`), wire the executor, thread results into the alerts table with `source_type=match_definition`. This is the most visible BFIU-analyst-facing power feature.

### 5. Phase 6 polish where it matters for real users

Not demo polish — product polish. In order:
- **a11y sweep**: keyboard focus rings (currently suppressed in some places by the brutalist override), `aria-label` on every icon-only button (notification bell, sidebar active marker, export dropdown triggers, React Flow node controls), `prefers-reduced-motion` respect on any remaining transitions. Compliance requirement for regulator procurement.
- **Mobile breakpoint pass**: sidebar collapses to a bottom bar or sheet drawer below `lg` (currently hidden entirely). Platform header wraps sensibly on narrow screens. Test the three persona overviews on an iPhone viewport.
- **Lighthouse**: measure both public and in-app. Target ≥ 95 / ≥ 90. Fix whatever the audit surfaces.

Skip the product-mocks.tsx screenshot refresh — file doesn't exist. The `docs/goaml-coverage.md` screenshot refresh can wait until after the demo film anyway.

### 6. AI red-team harness — scaffolding only

`engine/app/ai/evaluations.py` has the skeleton. Without API keys you can't run live scoring, but you can:
- Author the prompt corpus (adversarial STR narratives, ambiguous alert contexts, prompts that should decline).
- Define expected-output fixtures + scoring rubric.
- Wire a pytest gate that runs evaluations against the heuristic provider (catches regressions in the prompt templates + redaction + routing — not provider quality).

When keys come back on, flip the evaluator to hit real providers and the harness is already green.

## Housekeeping

- Deleted `KESTREL-SOVEREIGN-LEDGER-CONTINUITY.md` from tracking; `KESTREL-RESUME.md` is the new resume doc.
- ~35 untracked assets in repo root (logo sources, review screenshots, vestox refs, Kestrel Vision PDFs). Move to a committed `docs/review-assets/` folder or add to `.gitignore`. Currently noise in every `git status`.

## Don't spawn agents for this

Every task above is focused enough to handle directly with Read/Edit/Bash/Grep. Agents are for open-ended exploration, not sequential engineering. Budget-conscious: stay in the main thread, commit often, push after every green test run.

Ready when you are.
