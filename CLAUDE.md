# Kestrel — Project Intelligence

## What is this

Kestrel is a standalone financial crime intelligence platform for Bangladesh. It is built to sit between commercial banks (and MFS/NBFIs) and the Bangladesh Financial Intelligence Unit (BFIU), providing cross-bank entity intelligence, network analysis, explainable alerts, case management, native STR workflows, and command-level reporting. goAML is treated as an optional downstream adapter, not a dependency. The product has three personas on one platform: `bfiu_analyst`, `bank_camlco`, and `bfiu_director`.

## Current state

Phase 1 (infrastructure baseline) and Phase 3 (real auth and tenancy) from `docs/production-plan.md` are largely complete. Phases 4–9 have real database-backed implementations that already query the schema in `supabase/migrations/001_schema.sql`; they are no longer fixture-only. Phase 2 (AI platform) has a full internal subsystem in `engine/app/ai/` with providers, prompts, routing, redaction, audit, and a heuristic fallback provider — and AI alert explanations auto-fetch on open. **Phase 10 (production hardening) — shipped and live-verified** (`3ffd1e4`): per-request IDs, structured JSON logs, standardized error envelope (extended to Starlette 404s in `73f09d4`), and the incident runbook at `docs/RUNBOOK.md` with 9 playbooks.

**All 10 roadmap items from the intelligence-core spec are shipped and verified end-to-end on prod as of 2026-04-17.** Intelligence core merged at `53797d1` (2026-04-15) with follow-ups `d55aa90`, `0d35525`, `7aed54f`. Then in order: AI alert explanation + Draft STR (`0d25d9e`), CommandView polish (`ef6b2e9`), SAR/CTR report types (`62150a9`), WeasyPrint PDF case pack (`706c5cc`), scan upload path + incremental scan scope (`9f01e19`), parked modifier conditions (`042b5ab`), DB-backed typologies (`d64424b`), Phase 10 hardening (`3ffd1e4`). Baseline live verification against the DBBL synthetic dataset on `https://kestrel-engine.onrender.com`: 377 accounts, 547 transactions → 10 flagged accounts, 11 alerts. See `docs/superpowers/plans/2026-04-15-intelligence-core.md` and `2026-04-15-intelligence-core-verification.md` for the core merge, plus the per-task plans under `docs/superpowers/plans/2026-04-16-*` and `2026-04-17-*`.

What works end-to-end (with real DB data):
- Supabase Auth → JWT → engine JWKS/HS256 validation → profile lookup → role/persona/org resolution (`engine/app/auth.py`).
- Universal entity search, dossier with reporting history/alerts/cases/timeline, two-hop network graph via networkx (`engine/app/services/investigation.py`).
- Alerts list/detail with audit-logged mutations including alert→case escalation (`engine/app/services/alerts.py`).
- Cases list/detail with audit-logged mutations (`engine/app/services/case_mgmt.py`).
- STR reports native lifecycle: create/update/submit/review/enrich (`engine/app/services/str_reports.py`). **Submission now invokes `run_str_pipeline` which resolves identifiers + runs cross-bank matching.**
- **Pattern scan pipeline (`engine/app/services/scanning.py::queue_run` → `engine/app/core/pipeline.py::run_scan_pipeline`).** Loads accounts + transactions for the org scope, runs all 8 YAML rules via `evaluate_accounts`, scores via `calculate_risk_score`, resolves flagged accounts as entities, runs cross-bank matching, writes scan + cross_bank alerts, updates the `detection_runs` row. Detection runs synchronously in the request path — no Celery.
- **Scan upload path.** `POST /scan/runs/upload` accepts multipart CSV/XLSX, stores the raw file in `kestrel-uploads`, parses via `engine/app/parsers/`, persists `Transaction` rows tagged with the new `run_id`, and runs the pipeline scoped to that `run_id` only (`run_scan_pipeline(source_run_id=...)`) — this is the incremental scope path.
- **SAR/CTR report types.** `str_reports.report_type` column + separate `cash_transaction_reports` table (migration `003`). STR router filters by `report_type`; `POST /ctr-reports` + bulk-import endpoint exists.
- **PDF case pack export.** `GET /cases/{id}/export.pdf` streams a real WeasyPrint-rendered case pack with "Confidential — BFIU" watermark (`engine/app/services/pdf_export.py`).
- **AI alert explanations auto-fetch.** `AlertDetail` opens → `/api/ai/alerts/{id}/explanation` resolves → cached in alert metadata. "Draft STR" button on the same page POSTs to `/ai/str-narrative` and creates a draft STR.
- **DB-backed typologies library.** `engine/app/models/typology.py` + `typologies` table (migration `004`). `/intelligence/typologies` and `/web/typologies` both hit the DB; fixture removed.
- Overview (persona-aware KPIs + operational notes), compliance scorecard, national threat dashboard, trend series — all computed from real rows (`engine/app/services/reporting.py`). Director `CommandView` includes a cross-bank MatchTicker, typology spark badges, and a lagging-banks highlight.
- Admin surfaces: tenant summary/settings, team directory with mutations, rule catalog with mutations, synthetic backfill plan and apply (`engine/app/services/admin.py`, `engine/app/routers/admin.py`).
- AI invocation surface: entity extraction, STR narrative drafting, typology suggestion, executive briefing, alert explanation, case summary (`engine/app/routers/ai.py`).
- Readiness probe covering auth/db/redis/storage/worker/AI providers at `GET /ready` (`engine/app/services/readiness.py`). The public landing page consumes this report live.
- Observability baseline: per-request `X-Request-ID` middleware, structured JSON logs with request id propagation, standardized error envelope covering both FastAPI HTTPException and Starlette 404s, and `docs/RUNBOOK.md` with 9 incident playbooks.

What is scaffolded but NOT wired the way the plan implies:
- **Celery worker has one ping task.** `engine/app/tasks/*` defines `celery_app` and a `worker.ping` task and nothing else. `scan_tasks.py`, `export_tasks.py`, `str_tasks.py` exist as modules but are not hooked into any flow. All pipelines — including scan upload — run inline in the FastAPI request, not via Celery. This is fine for current load.
- **`engine/app/core/alerter.py` is orphaned.** Not imported by any production path after the intelligence-core merge. Left in place to avoid scope creep — do not delete blindly without checking imports.
- **Four detection modifier conditions remain hardcoded `False`** — see "Detection engine" below. Task 6 wired the other seven.
- **goAML adapter is a stub.** `engine/app/adapters/goaml.py` and related config exist; no sync is implemented.

What is missing entirely:
- Scheduled detection rule execution (currently only on-demand via `POST /scan/runs` or `POST /scan/runs/upload`).
- A real rule expression DSL — current evaluator uses dict-keyed lookup of modifier strings, not parsed expressions.
- Red team / AI eval harness beyond the scaffolding in `engine/app/ai/evaluations.py`.

## Architecture

### Stack
- **Frontend**: Next.js `16.2.2` App Router (`web/package.json`), React `19.2.4`, TypeScript 5, Tailwind v4, shadcn-style UI components, `@xyflow/react` for network graphs, `recharts`, `zustand`, `zod`, `@tanstack/react-table`, `date-fns`. Node pinned to `22.x`.
- **Backend**: Python `>=3.12` (pinned to `3.12.8` via `engine/.python-version`), FastAPI `>=0.115`, SQLAlchemy 2 async + asyncpg, Pydantic v2 settings, `python-jose` for JWT, `networkx` for graphs, `celery[redis]`, `PyYAML`, `pdfplumber`, `pandas`, `openpyxl`, `weasyprint`, `httpx`. Build backend: `hatchling`. See `engine/pyproject.toml`.
- **Database**: Supabase Postgres. Schema: `supabase/migrations/001_schema.sql`. RLS patch: `supabase/migrations/002_rules_insert_policy.sql`.
- **Auth**: Supabase Auth. Engine validates tokens two ways: `SUPABASE_JWT_SECRET` (HS256) or JWKS at `{SUPABASE_URL}/auth/v1/.well-known/jwks.json` with a 10-minute cache. Profile lookup joins `profiles` with `organizations` to resolve org/role/persona. See `engine/app/auth.py`.
- **Storage**: Supabase Storage, buckets `kestrel-uploads` and `kestrel-exports` (from `STORAGE_BUCKET_UPLOADS` / `STORAGE_BUCKET_EXPORTS`). The scan upload path writes raw CSV/XLSX uploads to `kestrel-uploads`; PDF case-pack exports stream directly from `/cases/{id}/export.pdf` rather than staging to `kestrel-exports` (bucket is still provisioned for future use). Readiness probe verifies both.
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

`engine/app/core/` is the production detection layer. Sync execution on the FastAPI request path (no Celery). Key files:

- `core/detection/rules/*.yaml` — 8 rules with code, trigger, params, scoring, severity, alert_template. Loader: `loader.py` validates schema on load.
- `core/detection/evaluator.py` — one `evaluate_*` function per trigger type + `evaluate_accounts()` dispatcher returning `list[RuleHit]` (defined in `rule_hit.py`).
- `core/detection/scorer.py` — `calculate_risk_score(rule_hits)` → `(score, severity, reasons)`. Weighted average clamped 0–100. Bands: critical ≥90, high ≥70, medium ≥50. **`weighted_contribution` is a percentage summing to ~100, not score-magnitude.**
- `core/resolver.py` — normalize + resolve identifiers (exact match, then pg_trgm fuzzy for person/business). Source-derived confidence: `str_cross_ref: 0.7`, `manual: 0.8`, `pattern_scan: 0.6`, `system: 0.5`. `resolve_identifiers_from_str` extracts STR subjects and emits `same_owner` connections.
- `core/matcher.py` — `run_cross_bank_matching`: for entities with ≥2 `reporting_orgs`, upserts `matches`, emits `cross_bank` alerts on new/escalated. Risk: `min(100, 50 + 10×count + (20 if exposure > 1 crore))`.
- `core/pipeline.py` — `run_str_pipeline` (from STR submit: resolve → match → mutate STR) and `run_scan_pipeline` (from scan: load accounts/txns → evaluate → score → resolve → match → write alerts/run).
- `core/graph/` — `builder.py` (networkx DiGraph), `analyzer.py` (metrics + suspicious_paths gated on risk ≥70), `pathfinder.py`, `export.py`.

**Scan pipeline scope rule (load-bearing):** `scope_org_ids=None` → all banks (regulator); `[uuid]` → that org (bank). Per-account writes (Entity, Match, Alert) attribute to `account.org_id` (the bank), not the caller. Threshold: `_SCAN_SCORE_THRESHOLD = 50`.

**`core/alerter.py` is orphaned** — not imported post-merge. Left to avoid `seed/fixtures.py` reference churn.

**Modifier conditions: 7 wired by Task 6 (`042b5ab`), 4 still hardcoded `False`** (need graph lookups the evaluator doesn't do yet):
- Wired: `cross_bank_debit` (rapid_cashout), `senders_from_multiple_banks` (fan_in_burst), `recipients_at_different_banks` (fan_out_burst), `beneficiary_at_different_bank` + `beneficiary_is_flagged` (first_time_high_value), `multiple_npsb_sources` + `immediate_outflow` (dormant_spike). All driven by `account.bank_code` populated on CSV ingest (`35d3055`) — synthetic accounts backfilled.
- Still `False`: `proximity_to_flagged <= 2` (rapid_cashout), `involves_multiple_banks` + `circular_flow_detected` (layering), `target_confidence > 0.8` (proximity_to_bad).

**`proximity_to_bad` warm-up:** needs `account.metadata_json["entity_id"]` (assigned on first resolve), so fires from the second scan onward.

**Verification baseline (2026-04-15):** 377 accounts, 547 txns → 10 flagged, 11 alerts (3× rapid_cashout, 6× first_time_high_value, 1× fan_in_burst, 1× cross_bank_match). Divergence without cause → evaluator/scorer regression.

**Alert source types in prod:** `str_enrichment` (seed loader), `scan` (pipeline), `cross_bank` (matcher) — all three coexist.

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

Source of truth: `.env.example`. Critical gotchas only (see that file for the full list):

- **Demo mode:** `KESTREL_ENABLE_DEMO_MODE` + `KESTREL_DEMO_PERSONA` (engine), `NEXT_PUBLIC_ENABLE_DEMO_MODE` + `NEXT_PUBLIC_DEMO_PERSONA` (web).
- **Supabase (web):** `NEXT_PUBLIC_SUPABASE_URL` + `NEXT_PUBLIC_SUPABASE_ANON_KEY` — if missing, web silently falls back to demo.
- **Supabase (engine):** `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_ROLE_KEY`. `SUPABASE_JWT_SECRET` enables HS256 (takes precedence over JWKS).
- **Engine core:** `DATABASE_URL` (must be `postgresql+asyncpg://`), `REDIS_URL`, `ALLOWED_ORIGINS`.
- **Web→engine proxy:** `ENGINE_URL` (server) or `NEXT_PUBLIC_ENGINE_URL` (client).
- **AI providers (all optional):** `OPENAI_API_KEY`, `ANTHROPIC_API_KEY` + model overrides. Unset → heuristic fallback if `AI_FALLBACK_ENABLED=true`.
- **Hardcoded defaults** not in `.env.example`: `ALGORITHM`, `APP_VERSION`, `ENVIRONMENT`.

## What to work on next

**All 10 roadmap items from the intelligence-core spec are shipped and live-verified on prod as of 2026-04-17.** No "next up" work queued. Completed tasks with shipping commits and verification shape:

| # | Item | Shipped in | Verified by |
|---|------|------------|-------------|
| 1 | SAR/CTR report types | `62150a9` + chain | SQL + UI |
| 2 | WeasyPrint PDF case pack | `706c5cc` + chain | Real PDF (18 KB, 2 pages) |
| 3 | Scan upload path | `9f01e19` + chain | Live CSV upload |
| 4 | AI alert explanation auto-call | `0d25d9e` | Browser test |
| 5 | Draft STR from alert | `0d25d9e` | Browser test |
| 6 | Parked modifier conditions | `042b5ab` + `35d3055` | Alert with `recipients_at_different_banks` firing +10 |
| 7 | Incremental scan scope | `9f01e19` (`source_run_id`) | Verified via Task 3 |
| 8 | Command view polish | `ef6b2e9` + `0c53fc1` | Browser test |
| 9 | Typologies DB-backed | `d64424b` + chain | 5 typologies from live DB |
| 10 | Phase 10 hardening — shipped and live-verified | `3ffd1e4` + `73f09d4` | Structured logs + envelope + runbook |

**Candidates for the next roadmap** (not prioritized — no active commitment):
- Scheduled / cron-driven scan execution (today only on-demand via `/scan/runs` or `/scan/runs/upload`).
- Graph lookups for the remaining four `False` modifiers (`proximity_to_flagged`, `involves_multiple_banks`, `circular_flow_detected`, `target_confidence > 0.8`).
- Real rule expression DSL (replacing the dict-keyed modifier lookup).
- AI eval / red-team harness beyond the scaffolding in `engine/app/ai/evaluations.py`.
- goAML adapter — currently a stub.
- Delete orphaned `engine/app/core/alerter.py` after confirming no seed/fixture references remain.
- Move heavy pipelines into Celery tasks once load justifies it (`engine/app/tasks/scan_tasks.py` etc. are empty shells).

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
- Apply migrations in order: `001_schema.sql`, `002_rules_insert_policy.sql`, `003_report_types.sql` (SAR/CTR), `004_typologies.sql` (DB-backed typologies library).

**Deployment:**
- Vercel production: push to `main` with `web/**` changes and `VERCEL_*` secrets set. Workflow handles prebuilt deploy.
- Render production: push to `main` with `engine/**` or `supabase/**` changes and `RENDER_*` deploy hook secrets set.
- No Makefile. No `justfile`. No local `docker-compose`.

## Known issues

Already covered in Current state / Detection engine: Celery has only ping (pipelines run inline), four modifier conditions still hardcoded `False`, `alerter.py` orphaned, goAML stub.

Non-obvious gotchas:

1. **Demo fallback is silent.** `web/src/lib/auth.ts::getCurrentViewer` returns demo viewer when Supabase client is null. Production has env vars set — only matters if removed.
2. **`detection_runs.status` CHECK** — `pending|processing|completed|failed` only. NOT `running` (fix: `d55aa90`).
3. **Rule RLS policy chain.** Commits `76b76f8` through `4e1af27` fix admin rule mutations via `scoped system session` in `services.admin.update_rule_configuration` + maintenance endpoint `POST /admin/maintenance/rules-policy-fix`. Don't simplify without understanding why the direct session failed.
4. **`_load_profile_context` swallows DB errors.** `engine/app/auth.py` catches `Exception` → `None` → falls back to JWT/demo. Broken DB looks like "not provisioned" instead of 500.
5. **Two `supabase` client paths.** `web/src/lib/supabase/` (folder) vs any `supabase.ts` import. Check the folder first.
6. **`proxy.ts` is the Next middleware.** Don't rename — tooling depends on it.
7. **Vercel SSR may 500 during Render redeploy.** Transient; reload after `Application startup complete`.
8. **`weighted_contribution` bug (fixed `7aed54f`).** Values above 100 = reintroduced bug.
9. **`py_compile` alone does not catch broken imports.** The SAR/CTR rollout shipped a missing import (`ctr.py` referenced a non-existent `app.models.organization`); local `py_compile` passed, Render deploy failed at uvicorn boot. Before pushing branches with new imports, run `cd engine && python -c "from app.main import app"`. Also verify third-party packages are declared in `pyproject.toml` (case: `jinja2` transitively present locally but missing from `pyproject.toml` → Render fresh install failed, fixed `390b2f1`).
10. **Error envelope covers Starlette 404s too.** The Phase 10 middleware wraps FastAPI `HTTPException`, but Starlette's router-level 404s (unknown path, unmatched method) bypass that handler by default. Fix `73f09d4` registers a separate `StarletteHTTPException` handler. Don't consolidate the two handlers — the Starlette one catches routes FastAPI's handler never sees.
