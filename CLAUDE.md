# Kestrel — Project Intelligence

## What is this

Kestrel is a standalone financial crime intelligence platform for Bangladesh. It is built to sit between commercial banks (and MFS/NBFIs) and the Bangladesh Financial Intelligence Unit (BFIU), providing cross-bank entity intelligence, network analysis, explainable alerts, case management, native STR workflows, and command-level reporting. goAML is treated as an optional downstream adapter, not a dependency. The product has three personas on one platform: `bfiu_analyst`, `bank_camlco`, and `bfiu_director`.

## Current state

Phase 1 (infrastructure baseline) and Phase 3 (real auth and tenancy) from `docs/production-plan.md` are largely complete. Phases 4–9 have real database-backed implementations that already query the schema in `supabase/migrations/001_schema.sql`; they are no longer fixture-only. Phase 2 (AI platform) has a full internal subsystem scaffolded in `engine/app/ai/` with providers, prompts, routing, redaction, audit, and a heuristic fallback provider. Phase 10 (production hardening) has not started.

What works end-to-end (with real DB data):
- Supabase Auth → JWT → engine JWKS/HS256 validation → profile lookup → role/persona/org resolution (`engine/app/auth.py`).
- Universal entity search, dossier with reporting history/alerts/cases/timeline, two-hop network graph via networkx (`engine/app/services/investigation.py`).
- Alerts list/detail with audit-logged mutations including alert→case escalation (`engine/app/services/alerts.py`).
- Cases list/detail with audit-logged mutations (`engine/app/services/case_mgmt.py`).
- STR reports native lifecycle: create/update/submit/review/enrich (`engine/app/services/str_reports.py`).
- Overview (persona-aware KPIs + operational notes), compliance scorecard, national threat dashboard, trend series — all computed from real rows (`engine/app/services/reporting.py`).
- Admin surfaces: tenant summary/settings, team directory with mutations, rule catalog with mutations, synthetic backfill plan and apply (`engine/app/services/admin.py`, `engine/app/routers/admin.py`).
- AI invocation surface: entity extraction, STR narrative drafting, typology suggestion, executive briefing, alert explanation, case summary (`engine/app/routers/ai.py`).
- Readiness probe covering auth/db/redis/storage/worker/AI providers at `GET /ready` (`engine/app/services/readiness.py`). The public landing page consumes this report live.

What is scaffolded but NOT wired the way the plan implies:
- **Detection engine core is a placeholder.** `engine/app/core/pipeline.py`, `core/resolver.py`, `core/matcher.py`, and `core/alerter.py` are 5–15 line stubs that delegate back to the investigation/matches services or return fixture alerts from `seed/fixtures.py`. `core/detection/evaluator.py` is a toy function that scores on transaction count alone; `core/detection/scorer.py` averages those scores. Only `core/graph/builder.py` and `core/graph/analyzer.py` contain real networkx logic.
- **Detection rule YAMLs are metadata only.** `engine/app/core/detection/rules/*.yaml` (rapid_cashout, fan_in_burst, fan_out_burst, dormant_spike, layering, proximity_to_bad, structuring, first_time_high_value) contain just `code`, `title`, `weight`, `threshold`. There is no rule-DSL and no expression logic.
- **Scan pipeline has no file upload path.** `POST /scan/runs` in `engine/app/services/scanning.py::queue_run` ignores the uploaded file, selects the top candidate entities from the `entities` table, and writes a `DetectionRun` row synchronously. There is no Supabase Storage upload, no parser invocation, and no Celery queueing in the request path despite the Celery app being declared.
- **Celery worker has one ping task.** `engine/app/tasks/*` defines `celery_app` and a `worker.ping` task and nothing else. `scan_tasks.py`, `export_tasks.py`, `str_tasks.py` exist as modules but are not hooked into any flow.
- **goAML adapter is a stub.** `engine/app/adapters/goaml.py` and related config exist; no sync is implemented.

What is missing entirely:
- Real file upload → parse → persist → alert pipeline for bank analysts.
- Scheduled detection rule execution against persisted transactions.
- Rule DSL and rule evaluation engine.
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
- `/scan` — `GET /scan/runs`, `POST /scan/runs`, `GET /scan/runs/{id}`, `GET /scan/runs/{id}/results`. Read paths are real. `POST /scan/runs` is **synchronous stub-grade**: it selects candidate entities from the `entities` table, persists a `DetectionRun`, returns. No file upload, no parsing, no Celery dispatch.
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
- `scan/page.tsx` — `ScanWorkbench` fetches `/api/scan/runs`. Read is real; queue submission persists a run from entity snapshot (see "Known issues").
- `scan/history/page.tsx`, `scan/[runId]/page.tsx` — real.
- `reports/national/page.tsx`, `compliance/page.tsx`, `trends/page.tsx`, `export/page.tsx` — real.
- `admin/page.tsx` — server-side `fetchAdminSummary()` + `fetchAdminSettings()` + conditional `fetchSyntheticBackfillPlan()`. Real.
- `admin/team/page.tsx`, `rules/page.tsx`, `api-keys/page.tsx` — real.
- `demo/[persona]/route.ts` — demo persona cookie setter (only active when demo mode is enabled).

## Detection engine

`engine/app/core/` is the phase-5/phase-7 placeholder. It is **not** where production detection logic currently lives.

What exists and works:
- `core/graph/builder.py` — builds a `networkx.DiGraph` from `Entity` and `Connection` rows with labels, risk scores, and amount-aware edges.
- `core/graph/analyzer.py` — computes `node_count`, `edge_count`, `max_depth`, and a `suspicious_paths` count gated on `risk_score >= 70`.
- `core/graph/pathfinder.py`, `core/graph/export.py` — graph export helpers used by `services.investigation.get_network_graph`.

What is a stub:
- `core/pipeline.py` — 22 lines. `run_pipeline` calls `resolve_entity` → `match_entity` → `build_alerts`. Used nowhere in production paths.
- `core/resolver.py` — 1-call shim to `services.investigation.search_entities`.
- `core/matcher.py` — filters the output of `services.investigation.list_matches` by `entity_id`.
- `core/alerter.py` — returns fixture alerts from `seed/fixtures.py::ALERTS`.
- `core/detection/evaluator.py` — `evaluate_transactions(transaction_count)` returns hardcoded rule dicts based on integer thresholds.
- `core/detection/scorer.py` — averages the scores from `evaluator`.
- `core/detection/loader.py` — `load_rules(path)` reads YAML files into dicts. The loaded values are never used by any rule-execution code.

Rule files in `core/detection/rules/` contain only `code`, `title`, `weight`, `threshold`:
- `rapid_cashout.yaml`, `fan_in_burst.yaml`, `fan_out_burst.yaml`, `dormant_spike.yaml`, `layering.yaml`, `proximity_to_bad.yaml`, `structuring.yaml`, `first_time_high_value.yaml`.

Real alert records in the database come from `engine/seed/load_dbbl_synthetic.py::_upsert_alerts`, which writes `source_type="str_enrichment"` alerts whose `reasons` JSON is derived from the synthetic statement risk profile.

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

Priority order to reach "a BFIU director's boss watches a 3-minute demo and says 'who built this?'" The premise of the demo is: upload a CSV of bank transactions, Kestrel produces explainable alerts and a cross-bank match, analyst escalates to a case, director sees the new signal on the command view, STR is drafted with AI assistance, and submitted.

1. **Verify live Supabase has the synthetic dataset.** Read `organizations`, `entities`, `alerts`, `matches` counts; if the table is empty, run `POST /admin/synthetic-backfill` from a regulator admin login. Without this, every platform page renders empty states.
2. **Real scan upload path.** Replace the stub in `engine/app/services/scanning.py::queue_run`:
   - Accept multipart upload in `POST /scan/runs` (FastAPI `UploadFile`), validate by extension (`.csv`, `.xlsx`, `.pdf`).
   - Store the raw file in Supabase Storage (`kestrel-uploads` bucket) using `SUPABASE_SERVICE_ROLE_KEY`.
   - Create a `DetectionRun` row with `status="pending"`.
   - Enqueue a Celery task in `engine/app/tasks/scan_tasks.py` that downloads the file, parses via `engine/app/parsers/csv.py` / `xlsx.py` / `statement_pdf.py`, persists `Transaction` rows against the caller's `org_id`, runs the detection pass, writes `flagged_accounts` into `results`, and flips status to `completed`.
   - Return the run id immediately; the frontend already polls `/scan/runs/{id}` and `/scan/runs/{id}/results`.
3. **Real rule evaluation.** The YAML files in `engine/app/core/detection/rules/` are metadata. Pick a rule DSL (recommend: SQLAlchemy-backed Python predicates in `engine/app/core/detection/rules.py` keyed by `code`, loaded alongside the YAML metadata). Implement at minimum `rapid_cashout`, `structuring`, `fan_in_burst`, `proximity_to_bad`. Have them return `(score, reasons, evidence)` triples. Wire the scan task above to run them on the freshly persisted transactions for the run's accounts.
4. **Alert creation from scan.** When a transaction-level rule fires above its threshold, write an `Alert` row with `source_type="scan"`, the rule code in `alert_type`, full `reasons` JSON, and `entity_id` pointing at the account entity. The alert queue + alert detail pages will pick it up automatically.
5. **Cross-bank match detection on new entities.** When scanning inserts a new account/phone/wallet entity, check for existing `entities` rows with the same `canonical_value` reported by a different org and upsert a `matches` row. `services.investigation.list_matches` already surfaces these. The "cross-bank hit" wow moment depends on this.
6. **Alert explanation AI on by default.** `POST /ai/alerts/{alert_id}/explanation` is wired. Call it from `AlertDetail` automatically when an alert is opened and cache the result in the alert's `metadata`. Director and analyst demos both need the "why" panel populated without a click.
7. **STR narrative drafting from an alert.** Add a "Draft STR" action on `AlertDetail` that POSTs to `/ai/str-narrative` with the alert context, then POSTs the result to `/str-reports` as a draft. The lifecycle pages already handle drafts.
8. **Live command view polish.** The director overview runs on real data but `CommandView` should gain: a top-3 lagging-banks list (already in `ComplianceScore` rows), a typology spark (already in `TrendSeriesResponse`), and a "new this hour" cross-bank match ticker. All three can be assembled from existing endpoints without new engine code.
9. **Remove the `typologies` fixture fallback.** `engine/app/routers/intelligence.py::typologies` still returns `seed.fixtures.TYPOLOGIES`. Replace with a DB-backed view or a per-org typology table before the director demo.
10. **Seed verification in production.** Before any demo, run `GET /ready` against the live engine and confirm `auth=ok`, `database=ok`, `redis=ok`, `storage=ok`, `worker=ok`. `worker` will fail today because no Celery worker is doing real work — start the Render worker service and confirm `worker.ping` responds.
11. **Celery worker hookup.** Even without real tasks, `celery -A app.tasks.celery_app.celery_app worker` must be running for the readiness probe to pass. Confirm the Render worker service is deployed.
12. **Phase 10 hardening (do after the demo):** structured logs with request ids, failure taxonomy, runbooks, backup checks, AI eval harness wiring, red-team prompt cases, release controls.

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

1. **`POST /scan/runs` does not use the uploaded file.** It picks candidate entities from the `entities` table and persists a run row synchronously. Demo will look suspicious if anyone watches the network request. See `engine/app/services/scanning.py::queue_run` and `_select_candidate_entities`.
2. **Celery has no real tasks.** `engine/app/tasks/celery_app.py` only exposes `worker.ping`. The modules `scan_tasks.py`, `export_tasks.py`, `str_tasks.py` exist but do nothing hooked up. If the Render worker isn't running, `/ready` reports `worker=error` which bubbles up into a 503.
3. **Detection rule YAMLs are metadata-only.** No rule logic is executed against transactions.
4. **`core/alerter.py` returns fixtures.** The only caller is `core/pipeline.py`, which itself is unused in production paths — but any future wiring into `pipeline.run_pipeline` will get fixture alerts, not DB alerts.
5. **`/intelligence/typologies` returns fixtures.** `engine/app/routers/intelligence.py` imports from `seed.fixtures`. See item 9 in "What to work on next".
6. **Demo viewer fallback is silent in the web layer.** `web/src/lib/auth.ts::getCurrentViewer` returns a demo viewer when `createSupabaseServerClient()` returns null. The production plan says demo mode must not silently activate — confirm `NEXT_PUBLIC_SUPABASE_URL` and `NEXT_PUBLIC_SUPABASE_ANON_KEY` are set in production, or the app will quietly serve demo content.
7. **`engine/app/services/scanning.py` references `entity.metadata_json`** in `_select_candidate_entities` for tx count. If the entity's `metadata` JSON is empty (default), the scan will report `tx_count=0` and look broken. The synthetic loader writes `metadata_json.transaction_count` — other paths may not.
8. **Report export is a placeholder.** `services.pdf_export.build_report_export(report_type)` exists; the router accepts `report_type` as a query param with no validation. If you call it with anything other than what the function handles, expect a raw exception.
9. **`typologies` router dependency imports from `seed.fixtures`.** Removing `seed/fixtures.py` breaks imports in `core/alerter.py` and `routers/intelligence.py`; any refactor needs to handle both.
10. **Rule RLS policy history.** Commits `76b76f8`, `ef93d26`, `8592e8e`, `d01f184`, `2113e4b`, `4e1af27` are a fix-and-follow-up chain for admin rule mutations hitting RLS. The fix is the `scoped system session` pattern in `services.admin.update_rule_configuration` and the maintenance endpoint at `POST /admin/maintenance/rules-policy-fix`. Don't simplify this pattern away without understanding why the direct session didn't work.
11. **`_load_profile_context` swallows DB errors.** `engine/app/auth.py` catches `Exception` from the profile query and returns `None`, which then falls back to JWT claims or demo mode. A broken database will look like "not provisioned for this user" instead of 500.
12. **Two `supabase` clients.** `web/src/lib/supabase/` (folder) and `web/src/lib/supabase.ts` (if present in imports) co-exist. Check `web/src/lib/supabase/` before adding new client helpers.
13. **`proxy.ts` is the Next middleware.** Named `proxy.ts` (not `middleware.ts`) and exports a `proxy` function. Next.js still picks it up due to the repo's custom convention. Don't rename it — there is probably tooling that depends on the name.
