# Kestrel — Project Intelligence

## What is this

Kestrel is a standalone financial crime intelligence platform for Bangladesh. It is built to sit between commercial banks (and MFS/NBFIs) and the Bangladesh Financial Intelligence Unit (BFIU), providing cross-bank entity intelligence, network analysis, explainable alerts, case management, native STR workflows, and command-level reporting. goAML is treated as an optional downstream adapter, not a dependency. The product has three personas on one platform: `bfiu_analyst`, `bank_camlco`, and `bfiu_director`.

## Current state

Phase 1 (infrastructure baseline) and Phase 3 (real auth and tenancy) from `docs/production-plan.md` are largely complete. Phases 4–9 have real database-backed implementations that already query the schema in `supabase/migrations/001_schema.sql`; they are no longer fixture-only. Phase 2 (AI platform) has a full internal subsystem scaffolded in `engine/app/ai/` with providers, prompts, routing, redaction, audit, and a heuristic fallback provider. Phase 10 (production hardening) has not started.

**As of 2026-04-15 the intelligence core (Phases 5 + 7) is real and verified live on prod.** The `feature/intelligence-core` branch was merged to main at commit `53797d1`; follow-up fixes in `d55aa90`, `0d35525`, `7aed54f`. End-to-end verification on `https://kestrel-engine.onrender.com` against the live DBBL synthetic dataset produced 10 flagged accounts + 11 alerts (10 scan + 1 cross-bank) from 377 accounts and 547 transactions. See `docs/superpowers/plans/2026-04-15-intelligence-core.md` for the implementation plan and `2026-04-15-intelligence-core-verification.md` for the verification log.

What works end-to-end (with real DB data):
- Supabase Auth → JWT → engine JWKS/HS256 validation → profile lookup → role/persona/org resolution (`engine/app/auth.py`).
- Universal entity search, dossier with reporting history/alerts/cases/timeline, two-hop network graph via networkx (`engine/app/services/investigation.py`).
- Alerts list/detail with audit-logged mutations including alert→case escalation (`engine/app/services/alerts.py`).
- Cases list/detail with audit-logged mutations (`engine/app/services/case_mgmt.py`).
- STR reports native lifecycle: create/update/submit/review/enrich (`engine/app/services/str_reports.py`). **Submission now invokes `run_str_pipeline` which resolves identifiers + runs cross-bank matching.**
- **Pattern scan pipeline (`engine/app/services/scanning.py::queue_run` → `engine/app/core/pipeline.py::run_scan_pipeline`).** Loads accounts + transactions for the org scope, runs all 8 YAML rules via `evaluate_accounts`, scores via `calculate_risk_score`, resolves flagged accounts as entities, runs cross-bank matching, writes scan + cross_bank alerts, updates the `detection_runs` row. Detection runs synchronously in the request path — no Celery.
- Overview (persona-aware KPIs + operational notes), compliance scorecard, national threat dashboard, trend series — all computed from real rows (`engine/app/services/reporting.py`).
- Admin surfaces: tenant summary/settings, team directory with mutations, rule catalog with mutations, synthetic backfill plan and apply (`engine/app/services/admin.py`, `engine/app/routers/admin.py`).
- AI invocation surface: entity extraction, STR narrative drafting, typology suggestion, executive briefing, alert explanation, case summary (`engine/app/routers/ai.py`).
- Readiness probe covering auth/db/redis/storage/worker/AI providers at `GET /ready` (`engine/app/services/readiness.py`). The public landing page consumes this report live.

What is scaffolded but NOT wired the way the plan implies:
- **Scan pipeline has no file upload path.** `POST /scan/runs` accepts the request body but ignores any uploaded file. Detection runs against whatever transactions are already in the `transactions` table (loaded via the synthetic seeder or future ingest). There is no Supabase Storage upload and no parser invocation in the request path.
- **Celery worker has one ping task.** `engine/app/tasks/*` defines `celery_app` and a `worker.ping` task and nothing else. `scan_tasks.py`, `export_tasks.py`, `str_tasks.py` exist as modules but are not hooked into any flow. The new pipelines run inline in the FastAPI request, not via Celery.
- **`engine/app/core/alerter.py` is orphaned.** Not imported by any production path after the merge. Left in place to avoid scope creep — do not delete blindly without checking imports.
- **Many detection modifier conditions are hardcoded `False`** — see "Detection engine" section below for the full list.
- **goAML adapter is a stub.** `engine/app/adapters/goaml.py` and related config exist; no sync is implemented.

What is missing entirely:
- Real file upload → parse → persist → alert pipeline for bank analysts.
- Scheduled detection rule execution (currently only on-demand via `POST /scan/runs`).
- A real rule expression DSL — current evaluator uses dict-keyed lookup of modifier strings, not parsed expressions.
- SAR/CTR report types (Tasks 8–9 from the original intelligence-core spec — deferred).
- Real WeasyPrint PDF case pack export (`engine/app/services/pdf_export.py` is a placeholder).
- Production observability (structured logs, failure taxonomy, runbooks).
- Red team / AI eval harness beyond the scaffolding in `engine/app/ai/evaluations.py`.

## Architecture

### Stack
- **Frontend**: Next.js `16.2.2` App Router (`web/package.json`), React `19.2.4`, TypeScript 5, Tailwind v4, shadcn-style UI components, `@xyflow/react` for network graphs, `recharts`, `zustand`, `zod`, `@tanstack/react-table`, `date-fns`. Node pinned to `22.x`.
- **Backend**: Python `>=3.12` (pinned to `3.12.8` via `engine/.python-version`), FastAPI `>=0.115`, SQLAlchemy 2 async + asyncpg, Pydantic v2 settings, `python-jose` for JWT, `networkx` for graphs, `celery[redis]`, `PyYAML`, `pdfplumber`, `pandas`, `openpyxl`, `weasyprint`, `httpx`. Build backend: `hatchling`. See `engine/pyproject.toml`.
- **Database**: Supabase Postgres. Schema: `supabase/migrations/001_schema.sql`. RLS patch: `supabase/migrations/002_rules_insert_policy.sql`.
- **Auth**: Supabase Auth. Engine validates tokens two ways: `SUPABASE_JWT_SECRET` (HS256) or JWKS at `{SUPABASE_URL}/auth/v1/.well-known/jwks.json` with a 10-minute cache. Profile lookup joins `profiles` with `organizations` to resolve org/role/persona. See `engine/app/auth.py`.
- **Storage**: Supabase Storage, buckets `kestrel-uploads` and `kestrel-exports` (from `STORAGE_BUCKET_UPLOADS` / `STORAGE_BUCKET_EXPORTS`). The readiness probe verifies both buckets exist. No code currently uploads or downloads.
- **Cache/Queue**: Redis on Render. Celery app name `kestrel` at `app.tasks.celery_app.celery_app`. Single `worker.ping` task declared — used by the readiness probe only.
- **AI**: Internal provider abstraction in `engine/app/ai/`. Adapters: `openai_adapter.py`, `anthropic_adapter.py`, plus a `HeuristicProvider` fallback. Task routing, prompt registry, redaction, invocation audit, and evaluation harness exist. Provider health is merged into `/ready`. Configured via `OPENAI_API_KEY` / `ANTHROPIC_API_KEY` and model overrides; unset ⇒ not configured ⇒ heuristic fallback if `AI_FALLBACK_ENABLED=true`.

### Deployment
- `web/` → Vercel via `deploy-web-production.yml` (prebuilt deploy; skips cleanly if `VERCEL_TOKEN` / `VERCEL_ORG_ID` / `VERCEL_PROJECT_ID` are not configured).
- `engine/` → Render. `engine/render.yaml` declares two services: `kestrel-engine` (FastAPI web, `uvicorn app.main:app`, healthcheck `/health`) and `kestrel-worker` (Celery, `celery -A app.tasks.celery_app.celery_app worker`). Deploy workflow uses per-service deploy hooks: `RENDER_ENGINE_DEPLOY_HOOK_URL`, `RENDER_WORKER_DEPLOY_HOOK_URL`. No live URL is committed to the repo.
- Database → Supabase. Connection via `DATABASE_URL` (`postgresql+asyncpg://...`) plus the `SUPABASE_*` envs for auth and storage.
- **CI**: GitHub Actions.
  - `.github/workflows/ci.yml` — `web` job: Node 22, `npm ci`, `npm run lint`, `npm run build`. `engine` job: Python 3.12, `pip install -e .[dev]`, `compileall`, `pytest -q`, then `python seed/run.py` as a smoke test.
  - `.github/workflows/deploy-web-production.yml` — `vercel pull` + `vercel build --prod` + `vercel deploy --prebuilt --prod` on `main` pushes that touch `web/**`.
  - `.github/workflows/deploy-engine-production.yml` — triggers Render deploy hooks on `main` pushes that touch `engine/**` or `supabase/**`.
  - `.github/workflows/vercel-prebuilt-check.yml` — manual Vercel build check, skipped unless secrets are present.

### Key directories
- `web/src/app/(public)/` — landing + pricing (implemented, reads live `/ready`).
- `web/src/app/(auth)/` — login, register, forgot-password (UI + Supabase client).
- `web/src/app/(platform)/` — authenticated shell pages (all implemented; mix of server-component DB fetches and client fetches to `/api/*`).
- `web/src/app/api/` — Next.js proxy routes that forward to the engine via `lib/engine-server.ts` and normalize payloads back into the web domain types. This is the data path for all platform pages.
- `web/src/components/` — shell, common, overview, investigate, alerts, cases, scan, STRs, intelligence, reports, admin, public, UI primitives. Mostly implemented.
- `web/src/lib/` — Supabase clients (`supabase/client.ts`, `server.ts`, `middleware.ts`), `auth.ts`, `engine-server.ts` (engine proxy), per-domain normalizers (`alerts.ts`, `cases.ts`, `investigation.ts`, `overview.ts`, `reports.ts`, `scan.ts`, `str-reports.ts`, `admin.ts`, `system.ts`), `demo.ts` (fixtures used only for landing persona cards and the viewer fallback).
- `web/src/hooks/` — `use-profile`, `use-realtime`, `use-role`, `use-search`. `use-search` hits `/api/investigate/search`.
- `engine/app/routers/` — one router per domain, registered in `app/main.py`.
- `engine/app/services/` — real DB-backed business logic (investigation, alerts, case_mgmt, str_reports, scanning, reporting, admin, compliance, readiness, pdf_export).
- `engine/app/core/` — **placeholder**. Pipeline/resolver/matcher/alerter are stubs. Only `core/graph/*` and `core/matcher.py→services` delegation are real.
- `engine/app/core/detection/rules/` — 8 YAML metadata files; no DSL.
- `engine/app/ai/` — provider abstraction, routing, prompts, redaction, audit, evaluations, heuristic fallback.
- `engine/app/models/` — SQLAlchemy models aligned to `supabase/migrations/001_schema.sql`.
- `engine/app/schemas/` — Pydantic request/response models per domain.
- `engine/app/parsers/` — `csv.py`, `xlsx.py`, `statement_pdf.py` (used by synthetic seed generator only).
- `engine/app/tasks/` — Celery app + unused task modules.
- `engine/seed/` — synthetic data generators (see "Seed data").
- `engine/tests/` — pytest suites for phase-1 baseline, scaffold, AI, auth, STR, scan, alerts/cases, reports, admin, synthetic dataset, schema alignment, rules RLS policy.
- `supabase/migrations/` — `001_schema.sql` (all core tables, RLS, triggers, auth hooks) and `002_rules_insert_policy.sql` (RLS fix that now lives in production).
- `docs/production-plan.md` — the canonical roadmap.

## Database schema

Source of truth: `supabase/migrations/001_schema.sql`. All tables have RLS enabled. Helper functions: `auth_org_id()` (current user's org), `is_regulator()` (user belongs to a `regulator` org), `handle_new_user()` (profile row on `auth.users` insert), `update_timestamp()`, `gen_case_ref()`, `gen_str_ref()`.

- `organizations` — 9 columns; `org_type` ∈ {`regulator`,`bank`,`mfs`,`nbfi`}. RLS: visible to own org or regulators.
- `profiles` — 7 columns; `role` ∈ {`superadmin`,`admin`,`manager`,`analyst`,`viewer`}; `persona` ∈ {`bfiu_analyst`,`bank_camlco`,`bfiu_director`}. Auto-inserted from `auth.users.raw_user_meta_data` via `on_signup`. RLS: own org or regulator.
- `entities` — 20 columns; canonical shared-intelligence identity. `entity_type` ∈ {`account`,`phone`,`wallet`,`nid`,`device`,`ip`,`url`,`person`,`business`}. Unique on `(entity_type, canonical_value)`. GIN trigram index on `display_value`. **RLS: shared across all authenticated users.**
- `connections` — 8 columns; directed edges between entities with typed relation and evidence JSON. Unique on `(from,to,relation)`. RLS: shared.
- `str_reports` — 23 columns; native STR lifecycle with `status` ∈ {`draft`,`submitted`,`under_review`,`flagged`,`confirmed`,`dismissed`}, `category` ∈ {`fraud`,`money_laundering`,`terrorist_financing`,`tbml`,`cyber_crime`,`other`}. RLS: own org or regulator. `gen_str_ref` trigger generates `STR-YYMM-######`.
- `matches` — 13 columns; cross-bank match clusters. Unique on `(match_type, match_key)`. RLS: shared.
- `accounts` — 10 columns; per-org bank accounts. Unique on `(org_id, account_number)`. RLS: own org or regulator.
- `transactions` — 14 columns; posted transactions with source/destination accounts. RLS: own org or regulator.
- `detection_runs` — 14 columns; persisted scan executions with `run_type` ∈ {`upload`,`scheduled`,`str_triggered`,`api`} and `results` JSONB (stores `summary`, `selected_rules`, `flagged_accounts`). RLS: own org or regulator.
- `alerts` — 16 columns; `source_type` ∈ {`scan`,`cross_bank`,`str_enrichment`,`manual`}; `status` ∈ {`open`,`reviewing`,`escalated`,`true_positive`,`false_positive`}. RLS: own org or regulator.
- `cases` — 17 columns; `status` ∈ {`open`,`investigating`,`escalated`,`pending_action`,`closed_confirmed`,`closed_false_positive`}. `gen_case_ref` trigger generates `KST-YYMM-#####`. RLS: own org or regulator.
- `rules` — 11 columns; unique on `(org_id, code)`. RLS: own org OR `is_system=true` (applies to both `using` and `with check`, per migration 002). System rules are writable via the scoped system session path in the admin service — see commit `2113e4b`.
- `audit_log` — 8 columns; append-only, indexed on `(org_id, created_at desc)`. RLS: own org only.

## Auth and tenancy model

The auth flow:
1. User signs in via Supabase Auth in the web app (`web/src/lib/supabase/client.ts`, `server.ts`, `middleware.ts`).
2. `PlatformLayout` calls `requireViewer()` (`web/src/lib/auth.ts`) which either resolves the viewer from Supabase session + `profiles` or returns a demo viewer if demo mode is enabled.
3. Every `/api/*` proxy call passes the Supabase access token to the engine via `proxyEngineRequest()` in `web/src/lib/engine-server.ts`.
4. The engine `HTTPBearer` dependency runs `authenticate_token()` → `decode_access_token()` in `engine/app/auth.py`. When `SUPABASE_JWT_SECRET` is set it uses HS256; otherwise it fetches JWKS from `{SUPABASE_URL}/auth/v1/.well-known/jwks.json` and verifies signatures (cache TTL 600s).
5. `resolve_authenticated_user()` looks up the profile row via `_load_profile_context()` and returns an `AuthenticatedUser` with `user_id`, `email`, `org_id`, `org_type`, `role`, `persona`, `designation`.
6. Route-level role gating uses `require_roles("analyst","manager","admin","superadmin")` and the admin service adds an extra `org_type == "regulator"` guard on privileged endpoints like synthetic backfill.
7. Row-level isolation is enforced by Postgres RLS policies, not by code. `auth_org_id()` and `is_regulator()` are `SECURITY DEFINER` functions.

Roles (database constraint): `superadmin`, `admin`, `manager`, `analyst`, `viewer`.
Personas (database constraint): `bfiu_analyst`, `bank_camlco`, `bfiu_director`.

Demo fallback: when Supabase auth config is absent AND `KESTREL_ENABLE_DEMO_MODE=true`, `authenticate_token` returns a synthesized user from `DEMO_USERS` keyed by `KESTREL_DEMO_PERSONA`.

RLS semantics to remember:
- `entities`, `connections`, `matches` — shared across all authenticated users. This is intentional for cross-bank intelligence.
- Everything else — own-org only unless the caller is regulator (via `is_regulator()`).
- `rules` — own-org OR `is_system=true`.
- `audit_log` — own-org only, no regulator override.

## API routes

All routers live in `engine/app/routers/` and are mounted in `engine/app/main.py`.

- `system.router` (no prefix) — `GET /health`, `GET /ready`. Real implementation. `readiness.py` probes auth config, db, redis, storage buckets, Celery worker, AI providers.
- `/overview` — `GET /overview` → real, persona-aware KPIs from DB (`services.reporting.build_overview`).
- `/investigate` — `GET /investigate/search`, `GET /investigate/entity/{entity_id}` → real SQLAlchemy queries, trigram-ish ILIKE search (`services.investigation`).
- `/network` — `GET /network/entity/{entity_id}` → real two-hop graph built with `core.graph.builder.build_graph`.
- `/scan` — `GET /scan/runs`, `POST /scan/runs`, `GET /scan/runs/{id}`, `GET /scan/runs/{id}/results`. All paths real. `POST /scan/runs` creates a `pending` `DetectionRun`, calls `run_scan_pipeline` synchronously, and returns the completed (or failed) run. Still no file upload — the pipeline scans whatever transactions are already in the DB. Regulator callers scan all banks; bank callers scan only their own org.
- `/str-reports` — full CRUD + `/submit`, `/review`, `/enrich`. Real service implementation.
- `/alerts` — `GET /alerts`, `GET /alerts/{id}`, `POST /alerts/{id}/actions`. Real, audit-logged, supports alert→case promotion.
- `/cases` — `GET /cases`, `GET /cases/{id}`, `POST /cases/{id}/actions`. Real, audit-logged.
- `/intelligence` — `GET /intelligence/entities`, `GET /intelligence/matches` (real DB), `GET /intelligence/typologies` (returns fixture `TYPOLOGIES` from `seed/fixtures.py`).
- `/reports` — `GET /reports/national`, `GET /reports/compliance`, `GET /reports/trends`, `POST /reports/export` (PDF export goes through `services.pdf_export.build_report_export`).
- `/admin` — `summary`, `settings`, `team` (GET + PATCH), `rules` (GET + PATCH), `api-keys`, `synthetic-backfill` (GET plan + POST apply), `maintenance/rules-policy-fix`. Rule and team mutations use a scoped system session because of the RLS policy on `rules`.
- `/ai` — `POST /entity-extraction`, `/str-narrative`, `/typology-suggestion`, `/executive-briefing`, `/alerts/{id}/explanation`, `/cases/{id}/summary`. All go through `AIOrchestrator` with provider routing, prompt registry, redaction, and audit logging.

The web side mirrors this with thin Next route handlers in `web/src/app/api/*/route.ts` that call `proxyEngineRequest` and normalize field names (e.g., `snake_case` → `camelCase`).

## Frontend pages

Every page lives under `web/src/app/`. "Implemented with real data" means the page (or its child client components) fetches from `/api/*` proxy routes that forward to the engine and hit the database.

Public:
- `(public)/page.tsx` — landing. Implemented. Reads `/ready` live via `fetchDeploymentReadiness`. Demo persona cards pull from `lib/demo.ts`.
- `(public)/pricing/page.tsx` — implemented.

Auth:
- `(auth)/login/page.tsx`, `register/page.tsx`, `forgot-password/page.tsx` — Supabase-backed forms.

Platform (all inside `(platform)` shell with sidebar + topbar, `requireViewer`-gated):
- `overview/page.tsx` — switches between `CommandView` (director), `BankView` (CAMLCO), `AnalystView`. All three fetch `/api/overview`. Real data.
- `investigate/page.tsx` — Omnisearch component hits `/api/investigate/search`. Real.
- `investigate/entity/[id]/page.tsx` — server-side `fetchEntityDossier(id)` → real dossier. Real.
- `investigate/network/[id]/page.tsx` — network canvas. Real graph via `/network/entity/{id}`.
- `investigate/trace/page.tsx` — scaffolded page shell.
- `intelligence/entities/page.tsx` — server-side `fetchSharedEntities()`. Real.
- `intelligence/matches/page.tsx` — real.
- `intelligence/typologies/page.tsx` — **fixture-backed** via engine `TYPOLOGIES`.
- `alerts/page.tsx`, `alerts/[id]/page.tsx` — `AlertQueue` + detail both fetch `/api/alerts`. Real.
- `cases/page.tsx`, `cases/[id]/page.tsx` — real.
- `strs/page.tsx`, `strs/[id]/page.tsx` — real.
- `scan/page.tsx` — `ScanWorkbench` fetches `/api/scan/runs`. Both list and queue submission run the real pipeline against persisted transactions.
- `scan/history/page.tsx`, `scan/[runId]/page.tsx` — real.
- `reports/national/page.tsx`, `compliance/page.tsx`, `trends/page.tsx`, `export/page.tsx` — real.
- `admin/page.tsx` — server-side `fetchAdminSummary()` + `fetchAdminSettings()` + conditional `fetchSyntheticBackfillPlan()`. Real.
- `admin/team/page.tsx`, `rules/page.tsx`, `api-keys/page.tsx` — real.
- `demo/[persona]/route.ts` — demo persona cookie setter (only active when demo mode is enabled).

## Detection engine

`engine/app/core/` is the production detection layer as of the 2026-04-15 intelligence-core merge. Sync execution on the FastAPI request path. No Celery.

**Layered architecture:**

1. **YAML rule definitions** — `core/detection/rules/*.yaml`. Each rule has `code`, `title`, `category`, `weight`, `description`, `conditions{trigger,params}`, `scoring{base,modifiers}`, `severity{critical,high,medium}`, and `alert_template{title,description}`. Loader: `core/detection/loader.py` validates the schema on load.

2. **Per-rule evaluators** — `core/detection/evaluator.py`. One pure-Python function per rule, dispatched by `conditions.trigger`:
   - `evaluate_rapid_cashout` (`credit_then_debit_percentage`)
   - `evaluate_fan_in_burst` (`unique_senders_to_recipient`)
   - `evaluate_fan_out_burst` (`unique_recipients_from_sender`)
   - `evaluate_structuring` (`sub_threshold_clustering`)
   - `evaluate_layering` (`structured_similar_transfers`)
   - `evaluate_first_time_high_value` (`new_beneficiary_high_value`)
   - `evaluate_dormant_spike` (`balance_spike_after_dormancy`)
   - `evaluate_proximity_to_bad` (`graph_proximity` — needs the entity graph + flagged set)
   - Top-level `evaluate_accounts(accounts, transactions, rules, graph, flagged_entity_ids)` runs all rules over all accounts and returns a flat `list[RuleHit]`.
   - Each `RuleHit` (defined in `core/detection/rule_hit.py`) carries `account_id`, `rule_code`, `score`, `weight`, `reasons`, `evidence`, `alert_title`, `alert_description`.

3. **Scorer** — `core/detection/scorer.py::calculate_risk_score(rule_hits)` returns `(score, severity, reasons)`. Score is the weighted average of per-hit scores, clamped 0–100. Severity bands: critical ≥90, high ≥70, medium ≥50, else low. `reasons` are sorted by weighted contribution. **Note:** `weighted_contribution` is a percentage of total weighted score, summing to ~100 (not score-magnitude). Single-hit alerts read 100.0.

4. **Resolver** — `core/resolver.py`. `normalize_identifier(entity_type, raw)` for account/wallet/phone/nid/person/business. `resolve_identifier()` does exact match on `(entity_type, canonical_value)`, then `pg_trgm` fuzzy match on `display_name` for person/business types. `resolve_identifiers_from_str(session, str_report, org_id)` extracts subjects from an STR and emits pairwise `same_owner` directed connections between non-person entities. New entities are added with `source`-derived initial confidence (`str_cross_ref: 0.7`, `manual: 0.8`, `pattern_scan: 0.6`, `system: 0.5`). Existing entities have `last_seen`, `report_count`, `reporting_orgs` updated in place.

5. **Cross-bank matcher** — `core/matcher.py::run_cross_bank_matching(entities, str_report, org_id)`. For each entity with ≥2 distinct `reporting_orgs`, upserts a row in `matches` keyed on `(match_type, match_key)`, computes risk score `min(100, 50 + 10×match_count + (20 if exposure > 1 crore))`, derives severity, and emits a `cross_bank` alert when the match is new or the severity rank increases. Returns `(matches, alerts)`.

6. **Pipelines** — `core/pipeline.py`:
   - `run_str_pipeline(session, *, str_report, org_id)` — called from `services.str_reports.submit_str_report`. Resolves identifiers, runs cross-bank matching, mutates the STR with `matched_entity_ids`, `cross_bank_hit`, and `auto_risk_score`. Writes a `pipeline.str.completed` audit log entry.
   - `run_scan_pipeline(session, *, run_id, org_id, scope_org_ids=None)` — called from `services.scanning.queue_run`. `scope_org_ids=None` scans every bank's accounts (regulator scope); a list filters to those orgs. For each account whose combined score ≥ `_SCAN_SCORE_THRESHOLD` (50), resolves the account as an Entity (via `resolve_identifier`), runs cross-bank matching, writes a scan `Alert`, and appends the account to `flagged_accounts_out`. **Per-account writes (Entity, Match, Alert) attribute to `account.org_id` (the bank that owns the account), not the caller — so banks see their own alerts even when a regulator triggered the scan.** Updates the `DetectionRun` row with `status='completed'`, `accounts_scanned`, `tx_count`, `alerts_generated`, and `results.flagged_accounts`. Writes `pipeline.scan.completed` audit log entry.

7. **Graph** (unchanged from before the merge):
   - `core/graph/builder.py` — builds a `networkx.DiGraph` from `Entity` and `Connection` rows with labels, risk scores, and amount-aware edges.
   - `core/graph/analyzer.py` — computes `node_count`, `edge_count`, `max_depth`, and a `suspicious_paths` count gated on `risk_score >= 70`.
   - `core/graph/pathfinder.py`, `core/graph/export.py` — graph export helpers used by `services.investigation.get_network_graph`.

**`core/alerter.py` is orphaned** after the merge — not imported by any production path. Left in place to avoid touching `seed/fixtures.py` references; safe to delete in a follow-up but not now.

**Modifier conditions hardcoded to `False` in the evaluator** (will become functional once richer transaction metadata or cross-bank graph lookups are wired in):
- `cross_bank_debit == true`, `proximity_to_flagged <= 2` (rapid_cashout)
- `senders_from_multiple_banks == true` (fan_in_burst)
- `recipients_at_different_banks == true` (fan_out_burst)
- `multiple_npsb_sources == true`, `immediate_outflow == true` (dormant_spike)
- `involves_multiple_banks == true`, `circular_flow_detected == true` (layering)
- `target_confidence > 0.8` (proximity_to_bad)
- `beneficiary_at_different_bank == true`, `beneficiary_is_flagged == true` (first_time_high_value)

**`proximity_to_bad` warm-up:** the rule needs `account.metadata_json["entity_id"]` to look up the account's node in the graph. The scan pipeline assigns this when it resolves a flagged account, so proximity has a one-scan warm-up before it starts firing on subsequent runs.

**Live verification baseline (2026-04-15, BFIU director scan against DBBL synthetic):** 377 accounts, 547 transactions, 10 flagged accounts, 11 alerts (3× `rapid_cashout` high, 6× `first_time_high_value`, 1× `fan_in_burst` medium, 1× `cross_bank_match` critical for entity `3502735816440` reported by 4 banks). If a future scan's numbers diverge wildly from these without an obvious cause, look for a regression in the evaluator or scorer.

**Real alert records pre-merge** came from `engine/seed/load_dbbl_synthetic.py::_upsert_alerts`, which writes `source_type="str_enrichment"` alerts. Those still exist in prod. New scan alerts have `source_type="scan"` and new cross-bank alerts have `source_type="cross_bank"` — all three shapes coexist.

## Seed data

Two mechanisms exist.

**In-memory fixtures** (`engine/seed/fixtures.py`):
- Hand-crafted `EntitySearchResult`, `NetworkGraph`, `EntityDossier`, `AlertDetail`, `CrossBankMatch`, `TypologySummary`, `DetectionRunSummary`, `FlaggedAccount`, `CaseWorkspace`, `ComplianceScore` for the "Rizwana Enterprise" scenario. Used by: the intelligence typologies endpoint, `core/alerter.py::build_alerts`, and as cloneable reference data. Not written to the database by production code.

**Synthetic DBBL generator** (`engine/seed/dbbl_synthetic.py` + `load_dbbl_synthetic.py`):
1. `dbbl_synthetic.py` reads a curated subset of real DBBL PDFs from `F:\New Download\Scammers' Bank statement DBBL` (local-only, never committed), runs them through `engine/app/parsers/statement_pdf.py`, sanitizes them (stable hash-based account numbers and names, scaled amounts, shifted dates), computes a `risk_profile` with rules for `rapid_cashout`, `mfs_fanout`, `cash_exit`, `burst_activity`, `high_turnover`, and writes JSON fixtures under `engine/seed/generated/dbbl_synthetic/` (which ARE committed: `summary.json`, `organizations.json`, `statements.json`, `entities.json`, `matches.json`, `connections.json`, `transactions.json`, `manifest.json`).
2. `load_dbbl_synthetic.py::apply_dataset()` idempotently upserts those JSON rows into live Supabase tables (`organizations`, `entities`, `connections`, `accounts`, `transactions`, `str_reports`, `matches`, `alerts`, `cases`) using deterministic UUIDs derived from the stable namespace `8d393384-a67a-4b64-bf0b-7b66b8d5da76`.

The loader can be invoked two ways:
- Locally: `python -m seed.load_dbbl_synthetic` prints a plan; `--apply` writes to whatever `DATABASE_URL` resolves to.
- Via the engine: `POST /admin/synthetic-backfill` (regulator admin/superadmin only) calls the same `apply_dataset` function — this is what the "Synthetic Backfill" card on `/admin` uses.

The generator target bank (`source_bank`) is hardcoded to Dutch-Bangla Bank PLC. Alerts generated from the synthetic dataset are attributed to the BFIU org. Whether the live Supabase currently has synthetic data loaded depends on whether `/admin/synthetic-backfill` has been run against it — check with a read of the `entities` table or via the admin summary card.

Also present: `engine/seed/run.py` (CI smoke test that asserts the generated manifest exists), `engine/seed/organizations.py`, `engine/seed/entities.py`, `engine/seed/patterns.py`, `engine/seed/str_reports.py`, `engine/seed/transactions.py`.

## Environment variables

Source of truth: `.env.example`. Grouped by role, with required/optional notes. Field status in the live deployment is **unknown from the repo** — this list describes what the code reads.

Shared:
- `NODE_ENV` — optional.
- `KESTREL_ENABLE_DEMO_MODE` — required to enable demo fallback on engine side (default `false` in `Settings`, `true` in `.env.example`).
- `KESTREL_DEMO_PERSONA` — selects which `DEMO_USERS` persona the fallback returns.
- `NEXT_PUBLIC_ENABLE_DEMO_MODE`, `NEXT_PUBLIC_DEMO_PERSONA` — web-side mirrors.

Supabase:
- `NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_ANON_KEY` — required for web to create a server client. If missing, `createSupabaseServerClient` returns null and the app falls back to demo.
- `SUPABASE_URL`, `SUPABASE_ANON_KEY` — engine-side. Used for JWKS URL and storage probe.
- `SUPABASE_SERVICE_ROLE_KEY` — required for the engine's storage readiness probe and any service-role DB access.
- `SUPABASE_JWT_SECRET` — enables HS256 verification path; takes precedence over JWKS.
- `SUPABASE_JWKS_URL` — optional override; defaults to `{SUPABASE_URL}/auth/v1/.well-known/jwks.json`.

Engine:
- `ENGINE_PORT` — default 8000.
- `DATABASE_URL` — required; must be `postgresql+asyncpg://...`.
- `REDIS_URL` — required; used by Celery broker/backend and readiness probe.
- `ALLOWED_ORIGINS` — comma-separated CORS origins.
- `STORAGE_BUCKET_UPLOADS`, `STORAGE_BUCKET_EXPORTS` — bucket names probed at `/ready`.
- `GOAML_SYNC_ENABLED`, `GOAML_BASE_URL`, `GOAML_API_KEY` — optional; no sync implemented.

AI providers (all optional):
- `OPENAI_API_KEY`, `OPENAI_BASE_URL`, `OPENAI_ORGANIZATION`, `OPENAI_MODEL`.
- `ANTHROPIC_API_KEY`, `ANTHROPIC_BASE_URL`, `ANTHROPIC_VERSION`, `ANTHROPIC_MODEL`.
- `AI_REDACTION_MODE` — default `redact`.
- `AI_ENABLE_EXTERNAL_PROBES` — whether readiness probes the external provider.
- `AI_PROVIDER_TIMEOUT_SECONDS`.
- `AI_FALLBACK_ENABLED` — defaults true; enables `HeuristicProvider`.

Web:
- `ENGINE_URL` (server) or `NEXT_PUBLIC_ENGINE_URL` (client) — required for `proxyEngineRequest`.

Intentionally omitted from `.env.example` (hardcoded defaults in `config.py`): `ALGORITHM`, `APP_VERSION`, `ENVIRONMENT` (the last is set per-service in `render.yaml` / Vercel env).

## What to work on next

Priority order to reach "a BFIU director's boss watches a 3-minute demo and says 'who built this?'" Tasks 2–5 from the previous version of this section are now **done** (intelligence-core merge). Updated list:

1. **SAR/CTR report types (Task 8 from intelligence-core spec).** Add `report_type` column to `str_reports` and a separate `cash_transaction_reports` table per the spec at `KESTREL-INTELLIGENCE-CORE-PROMPT.md`. The endpoints + schemas + UI lists need to filter and group by report type. CTR endpoint needs a bulk import path.
2. **Real PDF case pack export (Task 9 from intelligence-core spec).** Replace the placeholder `engine/app/services/pdf_export.py::generate_case_pdf` with a WeasyPrint-backed implementation rendering case header, summary, linked entities, alerts, STRs, timeline, and the "Confidential — BFIU" watermark.
3. **Real scan upload path.** `queue_run` still ignores any uploaded file — detection runs against whatever transactions are already in the DB. Add multipart `UploadFile` handling, store the raw file in `kestrel-uploads` (Supabase Storage), parse via `engine/app/parsers/csv.py` / `xlsx.py` / `statement_pdf.py`, persist `Transaction` rows tagged with `run_id`, and only THEN run the pipeline. Bonus: move execution to a Celery task in `engine/app/tasks/scan_tasks.py` so the request returns immediately.
4. **Wire the AI alert explanation by default.** `POST /ai/alerts/{alert_id}/explanation` is implemented but not auto-called. Call it from `AlertDetail` when an alert opens and cache the result in the alert's `metadata`. Director and analyst demos both need the "why" panel populated without a click.
5. **STR narrative drafting from an alert.** Add a "Draft STR" action on `AlertDetail` that POSTs to `/ai/str-narrative` with the alert context, then POSTs the result to `/str-reports` as a draft. The lifecycle pages already handle drafts.
6. **Wire the parked modifier conditions.** Several rule modifiers (`cross_bank_debit`, `senders_from_multiple_banks`, `recipients_at_different_banks`, `beneficiary_at_different_bank`, `beneficiary_is_flagged`, `circular_flow_detected`, `multiple_npsb_sources`, `immediate_outflow`, `target_confidence > 0.8`) are hardcoded `False` in the evaluator. They become functional once each transaction carries the right metadata (counterparty bank code) or a graph lookup is added.
7. **Incremental scan scope.** Today `run_scan_pipeline` re-evaluates all transactions in scope on every invocation. For the demo this is fine; for any real ingest path it needs `run_id`-tagged or time-windowed filtering.
8. **Live command view polish.** The director overview runs on real data but `CommandView` should gain a top-3 lagging-banks list, a typology spark, and a "new this hour" cross-bank match ticker. All three can be assembled from existing endpoints.
9. **Remove the `typologies` fixture fallback.** `engine/app/routers/intelligence.py::typologies` still returns `seed.fixtures.TYPOLOGIES`. Replace with a DB-backed view or a per-org typology table.
10. **Phase 10 hardening:** structured logs with request ids, failure taxonomy, runbooks, backup checks, AI eval harness wiring, red-team prompt cases, release controls.

## Code conventions

Observed by reading the code, not invented:

**Python (engine):**
- FastAPI routers are one-file-per-domain in `engine/app/routers/`; they do nothing except parameter wiring, auth dependencies, and delegation to `engine/app/services/`.
- Services accept the `AsyncSession` plus a keyword-only `user: AuthenticatedUser` and return plain dicts that routers wrap in Pydantic response models.
- SQLAlchemy 2 async style: `select(...)`, `session.execute()`, `.scalars()`. Use `select(Model.id, ...)` for narrow projections.
- Helper functions `_as_uuid`, `_as_float`, `_iso`, `_safe_int` are duplicated per service file (each file owns its own). Not centralized.
- Audit logging is manual: services that mutate state insert an `AuditLog` row with `action=f"<resource>.<verb>"` and `details=request.model_dump()` before `await session.commit()`.
- All DB-touching code lives under `engine/app/services/`; routers never execute SQL directly.
- Pydantic `model_validate(dict)` is used everywhere to turn service dicts into response models.
- Redaction and AI call contracts live in `engine/app/ai/`; nothing else should talk to OpenAI/Anthropic.
- Dependency injection uses `Annotated[T, Depends(...)]` consistently.
- Role gates: `require_roles("analyst","manager","admin","superadmin")`; additional checks live in services (`_require_regulator_admin`).
- Test files follow `test_<domain>_phase<n>.py` naming.

**TypeScript (web):**
- Next.js App Router with route groups: `(public)`, `(auth)`, `(platform)`.
- Server components call `requireViewer()` or `requireRole(...)` at the top of the file and throw a redirect on failure.
- Data fetching uses Next route handlers under `web/src/app/api/**/route.ts` which proxy to the engine via `proxyEngineRequest`. No component fetches the engine directly.
- Per-domain normalizer modules in `web/src/lib/` translate engine snake_case payloads into web camelCase domain types in `web/src/types/domain.ts`.
- Client components use `"use client"`, load state via `useState` + `useEffect`, show `LoadingState` / `EmptyState` / `ErrorState` common components.
- shadcn-style UI primitives live in `web/src/components/ui/` and are composed by domain components.
- Navigation is config-driven via `web/src/components/shell/nav-config.ts` with persona/role filters.
- `PageFrame` is the canonical page wrapper (eyebrow, title, description, actions slot).
- No global state library is actively used beyond `zustand` being installed; state is local to client components or comes from server components.

## Commands

From the actual files:

**Web (`web/`):**
- `npm install` — install. Node must be 22.x.
- `npm run dev` — Next dev server.
- `npm run build` — production build.
- `npm run start` — run the built app.
- `npm run lint` — ESLint via `eslint-config-next`.

**Engine (`engine/`):**
- `pip install -e .[dev]` — install runtime + dev dependencies (pytest, pytest-asyncio).
- `uvicorn app.main:app --reload` — dev API.
- `celery -A app.tasks.celery_app.celery_app worker --loglevel=INFO` — worker (same command as Render).
- `pytest -q` — run tests.
- `python seed/run.py` — manifest smoke test (runs in CI).
- `python -m seed.dbbl_synthetic` — regenerate synthetic JSON fixtures from local DBBL PDFs.
- `python -m seed.load_dbbl_synthetic` — print the load plan against `DATABASE_URL`.
- `python -m seed.load_dbbl_synthetic --apply` — actually upsert the synthetic dataset.

**Database:**
- Apply `supabase/migrations/001_schema.sql` to the target Supabase project (via Supabase SQL editor or CLI).
- Then apply `supabase/migrations/002_rules_insert_policy.sql`.

**Deployment:**
- Vercel production: push to `main` with `web/**` changes and `VERCEL_*` secrets set. Workflow handles prebuilt deploy.
- Render production: push to `main` with `engine/**` or `supabase/**` changes and `RENDER_*` deploy hook secrets set.
- No Makefile. No `justfile`. No local `docker-compose`.

## Known issues

Verified by reading the code, not guessed:

1. **`POST /scan/runs` ignores any uploaded file.** Detection runs against whatever transactions are already in the DB. Acceptable for the synthetic dataset but the upload → parse → persist path is still missing. See `engine/app/services/scanning.py::queue_run`.
2. **Celery has no real tasks.** `engine/app/tasks/celery_app.py` only exposes `worker.ping`. The modules `scan_tasks.py`, `export_tasks.py`, `str_tasks.py` exist but do nothing hooked up. The new pipelines run inline in the FastAPI request, not via Celery. If the Render worker isn't running, `/ready` reports `worker=error` which bubbles up into a 503.
3. **Several rule modifiers hardcoded to `False`.** See "Detection engine" → "Modifier conditions hardcoded to False". The trigger logic itself is real; only certain bonus modifiers are inert until richer transaction metadata is wired in.
4. **`core/alerter.py` is orphaned.** Not imported by any production path after the intelligence-core merge. Used to return fixtures; safe to delete in a follow-up but currently kept around to avoid touching `seed/fixtures.py` references.
5. **`/intelligence/typologies` returns fixtures.** `engine/app/routers/intelligence.py` imports from `seed.fixtures`. See item 9 in "What to work on next".
6. **Demo viewer fallback is silent in the web layer.** `web/src/lib/auth.ts::getCurrentViewer` returns a demo viewer when `createSupabaseServerClient()` returns null. Confirm `NEXT_PUBLIC_SUPABASE_URL` and `NEXT_PUBLIC_SUPABASE_ANON_KEY` are set in production, or the app will quietly serve demo content. (Note: production has these set — the live Vercel deployment authenticates against real Supabase.)
7. **`detection_runs.status` CHECK constraint** allows only `pending|processing|completed|failed`. NOT `running`. The intelligence-core merge had to ship a follow-up fix (`d55aa90`) for this — don't reintroduce `running` anywhere.
8. **Report export PDF is a placeholder.** `services.pdf_export.build_report_export(report_type)` exists; the router accepts `report_type` as a query param with no validation. Real WeasyPrint case pack is Task 9 from the intelligence-core spec, deferred.
9. **`typologies` router dependency imports from `seed.fixtures`.** Removing `seed/fixtures.py` would also need to handle `core/alerter.py` (orphan, see #4).
10. **Rule RLS policy history.** Commits `76b76f8`, `ef93d26`, `8592e8e`, `d01f184`, `2113e4b`, `4e1af27` are a fix-and-follow-up chain for admin rule mutations hitting RLS. The fix is the `scoped system session` pattern in `services.admin.update_rule_configuration` and the maintenance endpoint at `POST /admin/maintenance/rules-policy-fix`. Don't simplify this pattern away without understanding why the direct session didn't work.
11. **`_load_profile_context` swallows DB errors.** `engine/app/auth.py` catches `Exception` from the profile query and returns `None`, which then falls back to JWT claims or demo mode. A broken database will look like "not provisioned for this user" instead of 500.
12. **Two `supabase` clients.** `web/src/lib/supabase/` (folder) and `web/src/lib/supabase.ts` (if present in imports) co-exist. Check `web/src/lib/supabase/` before adding new client helpers.
13. **`proxy.ts` is the Next middleware.** Named `proxy.ts` (not `middleware.ts`) and exports a `proxy` function. Next.js still picks it up due to the repo's custom convention. Don't rename it — there is probably tooling that depends on the name.
14. **Vercel SSR `/scan` may briefly 500 during a Render redeploy.** The page itself is minimal but during the engine's drain/restart window, transient SSR fetches can fail. Reload after the engine reports `Application startup complete` in `render logs`. Not a code bug.
15. **`weighted_contribution` was a real bug, fixed in `7aed54f`.** The pre-fix formula multiplied by 100 unnecessarily, producing values like 8000.0 instead of percentages. If you see contribution values above 100, you've reintroduced the bug.
