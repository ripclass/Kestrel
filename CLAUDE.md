# Kestrel — Project Intelligence

## What is this

Kestrel is a standalone financial crime intelligence platform for Bangladesh. It is built to sit between commercial banks (and MFS/NBFIs) and the Bangladesh Financial Intelligence Unit (BFIU), providing cross-bank entity intelligence, network analysis, explainable alerts, case management, native STR workflows, and command-level reporting. It is positioned as a **complete goAML replacement** — banks can continue filing in goAML XML (import + export round-trip), BFIU analysts see the familiar vocabulary (Catalogue Search, IER, Match Definitions, Disseminations), and the platform adds AI-native intelligence goAML cannot provide. The product has three personas on one platform: `bfiu_analyst`, `bank_camlco`, `bfiu_director`. The procurement-facing capability map is at `docs/goaml-coverage.md`.

## Current state

> **Prod state (2026-04-18):** Sovereign Ledger rebrand merged to `main` (`92164b1`) and live on `kestrel-nine.vercel.app`. Migration 010 (`access_requests`) applied to prod Supabase. `SUPABASE_SERVICE_ROLE_KEY` is set on the Vercel web project env. The landing intake form writes through to `access_requests`. The rebrand is described in §"Sovereign Ledger" below.

Three full build-out sessions are shipped end-to-end on prod.

**Session 1 — intelligence-core (2026-04-15 → 2026-04-16).** 10 roadmap items from `KESTREL-INTELLIGENCE-CORE-PROMPT.md`: real detection engine (8 YAML rules + evaluator + scorer + resolver + matcher + pipeline), scan upload path, WeasyPrint PDF case pack, SAR/CTR report types, AI alert auto-explanation + Draft STR, DB-backed typologies, CommandView polish, parked modifier conditions wired, incremental scan scope, Phase 10 hardening (request IDs + structured JSON logs + standardised error envelope + `docs/RUNBOOK.md`).

**Session 2 — goAML coverage patch (2026-04-17).** All 13 items from `KESTREL-GOAML-COVERAGE-PROMPT.md`. Migrations `005_report_types_expanded`, `006_disseminations`, `007_case_variants`, `008_intel_tables`, `009_reference_tables` all applied to prod Supabase. Expanded report types to 11 variants (STR, SAR, CTR, TBML, Complaint, IER, Internal, Adverse Media-STR, Adverse Media-SAR, Escalated, Additional Info). Shipped goAML XML import + export, dedicated IER workflow (`/iers`), Additional Information File supplements, 3-tab New Subjects form, Catalogue tile grid, dissemination ledger with "Disseminate" action on Case/Alert/Entity/STR, 8-variant case enum with proposal kanban + RFI routing, saved queries + manual diagram builder + match definitions, reference tables (197 seed rows: 64 banks, 10 channels, 12 categories, 64 countries, 30 currencies, 17 agencies), operational statistics dashboards, scheduled-processes admin surface, XLSX + goAML-XML exports, goAML vocabulary tooltips on every nav entry, and `docs/goaml-coverage.md` — the procurement doc.

**Aggregate prod state:**
- 99 engine routes across 19 routers. 95/95 pytest. `GET /ready` on `https://kestrel-engine.onrender.com` shows auth/db/redis/storage/worker=ok; OpenAI + Anthropic `missing_config` → heuristic fallback is active.
- Migrations 001–009 applied. Prod data: 197 reference_tables rows, 5 typologies, 28 entities, 377 accounts, 547 transactions, 10 STRs, 22 alerts, 1 case. Disseminations / saved_queries / diagrams / match_definitions tables exist and are empty (used only in verification so far).
- All 39 `(platform)` pages under `web/src/app/` are live with real DB-backed data — no scaffold placeholders remain.

What is scaffolded but NOT wired the way the code implies:
- **Celery worker has one ping task.** `engine/app/tasks/*` defines `celery_app` + `worker.ping`. `scan_tasks.py` / `export_tasks.py` / `str_tasks.py` are empty shells. Every pipeline (STR submit, scan run, scan upload, XML import, match execution) runs inline in the FastAPI request path — fine for current load but scheduled execution is not wired.
- **`engine/app/core/alerter.py` is orphaned.** Not imported by any production path. Left to avoid touching `seed/fixtures.py` references.
- **goAML *outbound* adapter is a stub.** `engine/app/adapters/goaml.py` exists; machine-to-machine sync into goAML's central server is not implemented. Distinct from the XML import/export we shipped (those are file-based).
- **`/admin/schedules` is read-only.** The declared jobs list exists but no Celery Beat schedule is populated.

What is missing entirely:
- A real rule expression DSL — the evaluator uses dict-keyed lookup of modifier strings.
- AI red-team / evaluation harness beyond the scaffolding in `engine/app/ai/evaluations.py`.
- Landing page hero rewrite — `kestrel-nine.vercel.app` still leads with deployment health rather than the intelligence story.

## Architecture

### Stack
- **Frontend**: Next.js `16.2.2` App Router (`web/package.json`), React `19.2.4`, TypeScript 5, Tailwind v4, shadcn-style UI components, `@xyflow/react` for network graphs, `recharts` for dashboards, `zustand`, `zod`, `@tanstack/react-table`, `date-fns`. Node pinned to `22.x`.
- **Backend**: Python `>=3.12` (pinned to `3.12.8` via `engine/.python-version`), FastAPI `>=0.115`, SQLAlchemy 2 async + asyncpg, Pydantic v2 settings, `python-jose` for JWT, `networkx` for graphs, `celery[redis]`, `PyYAML`, `pdfplumber`, `pandas`, `openpyxl`, `weasyprint`, `lxml` (for goAML XML import), `jinja2`, `httpx`. Build backend: `hatchling`. See `engine/pyproject.toml`.
- **Database**: Supabase Postgres. Schema source of truth: `supabase/migrations/001_schema.sql` through `009_reference_tables.sql`.
- **Auth**: Supabase Auth. Engine validates tokens two ways: `SUPABASE_JWT_SECRET` (HS256) or JWKS at `{SUPABASE_URL}/auth/v1/.well-known/jwks.json` with a 10-minute cache. Profile lookup joins `profiles` with `organizations` to resolve org/role/persona. See `engine/app/auth.py`.
- **Storage**: Supabase Storage, buckets `kestrel-uploads` and `kestrel-exports` (from `STORAGE_BUCKET_UPLOADS` / `STORAGE_BUCKET_EXPORTS`). The scan upload path writes raw CSV/XLSX to `kestrel-uploads`; PDF case packs + XLSX + XML exports stream directly from the engine rather than staging. Readiness probe verifies both buckets exist.
- **Cache/Queue**: Redis on Render. Celery app `kestrel` at `app.tasks.celery_app.celery_app`. Single `worker.ping` task — used by the readiness probe + the `/admin/schedules` live worker probe.
- **AI**: Internal provider abstraction in `engine/app/ai/`. Adapters: `openai_adapter.py`, `anthropic_adapter.py`, plus a `HeuristicProvider` fallback. Task routing, prompt registry, redaction, invocation audit, and evaluation harness exist. Provider health is merged into `/ready`. **Prod currently runs on heuristic fallback** — both OpenAI and Anthropic show `missing_config` because the API keys haven't been set on Render.

### Deployment
- `web/` → Vercel via `deploy-web-production.yml` (prebuilt deploy; skips cleanly if `VERCEL_TOKEN` / `VERCEL_ORG_ID` / `VERCEL_PROJECT_ID` are not configured).
- `engine/` → Render. `engine/render.yaml` declares two services: `kestrel-engine` (FastAPI web, `uvicorn app.main:app`, healthcheck `/health`) and `kestrel-worker` (Celery, `celery -A app.tasks.celery_app.celery_app worker`). Deploy workflow uses per-service deploy hooks: `RENDER_ENGINE_DEPLOY_HOOK_URL`, `RENDER_WORKER_DEPLOY_HOOK_URL`.
- Database → Supabase project `bmlyqlkzeuoglyvfythg`. Connection via `DATABASE_URL` (`postgresql+asyncpg://...`) plus the `SUPABASE_*` envs.
- **CI**: GitHub Actions.
  - `.github/workflows/ci.yml` — `web` job: Node 22, `npm ci`, `npm run lint`, `npm run build`. `engine` job: Python 3.12, `pip install -e .[dev]`, `compileall`, `pytest -q`, then `python seed/run.py` smoke test.
  - `.github/workflows/deploy-web-production.yml` — `vercel pull` + `vercel build --prod` + `vercel deploy --prebuilt --prod` on `main` pushes that touch `web/**`.
  - `.github/workflows/deploy-engine-production.yml` — triggers Render deploy hooks on `main` pushes that touch `engine/**` or `supabase/**`.
  - `.github/workflows/vercel-prebuilt-check.yml` — manual Vercel build check, skipped unless secrets are present.

### Key directories

- `web/src/app/(public)/` — landing (reads live `/ready`) + pricing.
- `web/src/app/(auth)/` — login, register, forgot-password (Supabase-backed).
- `web/src/app/(platform)/` — 39 authenticated shell pages. Every one is live with DB-backed data.
- `web/src/app/api/` — Next.js proxy routes that forward to the engine via `lib/engine-server.ts` and normalize snake_case → camelCase. Download endpoints (PDF / XLSX / XML) forward raw bytes with preserved `Content-Disposition`.
- `web/src/components/` — `shell/`, `common/`, `overview/`, `investigate/`, `alerts/`, `cases/`, `scan/`, `str-reports/`, `intelligence/`, `iers/`, `disseminations/`, `intel/`, `admin/`, `reports/`, `public/`, `ui/`. All implemented.
- `web/src/lib/` — Supabase clients, `auth.ts`, `engine-server.ts`, per-domain normalizers (`alerts`, `cases`, `investigation`, `overview`, `reports`, `scan`, `str-reports`, `disseminations`, `iers`, `intel`, `admin-intel`, `system`), `demo.ts` (demo viewer fallback).
- `web/src/hooks/` — `use-profile`, `use-realtime`, `use-role`, `use-search`.

**Engine routers** (`engine/app/routers/`, 19 files — one per domain):
`admin.py`, `ai.py`, `alerts.py`, `cases.py`, `ctr.py`, `diagrams.py`, `disseminations.py`, `ier.py`, `intelligence.py`, `investigate.py`, `match_definitions.py`, `network.py`, `overview.py`, `reference_tables.py`, `reports.py`, `saved_queries.py`, `scan.py`, `str_reports.py`, `system.py`.

**Engine services** (`engine/app/services/`, 27 files — all real DB-backed, none are stubs or placeholders):
`admin`, `alerts`, `case_export`, `case_mgmt`, `compliance`, `csv_ingest`, `ctr`, `diagrams`, `disseminations`, `goaml_xml_export` (inverse of Task 2 parser), `goaml_xml_import` (Task 2 import service), `ier` (facade over STR with ier_* columns), `investigation`, `match_definitions`, `new_subject`, `pdf_export` (WeasyPrint), `readiness`, `reference_tables`, `reporting`, `saved_queries`, `scanning`, `schedules` (Celery ping probe + declared-jobs list), `statistics` (goAML-shape aggregator), `storage`, `str_reports`, `xlsx_export` (openpyxl).

**Engine models** (`engine/app/models/`, 21 files):
`account`, `alert`, `audit`, `base`, `case`, `connection`, `ctr`, `detection_run`, `diagram`, `dissemination`, `entity`, `match`, `match_definition` (includes `MatchExecution`), `org`, `profile`, `reference_table`, `rule`, `saved_query`, `str_report`, `transaction`, `typology`.

**Engine core** (`engine/app/core/`):
- `detection/rules/*.yaml` — 8 rules; `detection/loader.py`, `detection/evaluator.py`, `detection/scorer.py`, `detection/rule_hit.py`.
- `resolver.py` — `normalize_identifier`, `resolve_identifier`, `resolve_identifiers_from_str`, `link_subject_group` (public pairwise `same_owner` helper).
- `matcher.py` — `run_cross_bank_matching`.
- `pipeline.py` — `run_str_pipeline`, `run_scan_pipeline`.
- `graph/` — `builder.py`, `analyzer.py`, `pathfinder.py`, `export.py`.
- `alerter.py` — orphaned, do not delete blindly (still referenced by `seed/fixtures.py`).

**Engine parsers** (`engine/app/parsers/`):
- `csv.py`, `xlsx.py`, `statement_pdf.py` — used by the scan upload path + synthetic seed generator.
- `goaml_xml.py` — lxml-based goAML XML intake (Task 2). Permissive, recovers from malformed docs, logs warnings.

- `engine/app/ai/` — provider abstraction, routing, prompts, redaction, audit, evaluations, heuristic fallback.
- `engine/app/schemas/` — Pydantic request/response models per domain.
- `engine/app/tasks/` — Celery app + (empty) task modules.
- `engine/seed/` — synthetic data generators.
- `engine/tests/` — pytest suites.
- `supabase/migrations/` — 9 files; see "Database schema" below.
- `docs/production-plan.md` — original phased roadmap.
- `docs/goaml-coverage.md` — procurement-facing goAML coverage map.
- `docs/RUNBOOK.md` — incident playbooks (Phase 10).

## Database schema

All tables have RLS enabled. Helper functions: `auth_org_id()`, `is_regulator()`, `handle_new_user()`, `update_timestamp()`, `gen_case_ref()`, `gen_str_ref()` (short-code prefix map added in migration 005), `gen_dissem_ref()`.

**Core tables from `001_schema.sql`:**
- `organizations` — 9 cols; `org_type` ∈ {regulator, bank, mfs, nbfi}. RLS: own org or regulator.
- `profiles` — 7 cols; `role` ∈ {superadmin, admin, manager, analyst, viewer}; `persona` ∈ {bfiu_analyst, bank_camlco, bfiu_director}. Auto-inserted from `auth.users` via `on_signup`. RLS: own org or regulator.
- `entities` — 20 cols; canonical shared-intelligence identity. `entity_type` ∈ {account, phone, wallet, nid, device, ip, url, person, business}. Unique `(entity_type, canonical_value)`. GIN trigram on `display_value`. **RLS: shared across all authed users** (intentional for cross-bank intelligence).
- `connections` — 8 cols; directed edges with typed relations. **RLS: shared.**
- `matches` — 13 cols; cross-bank clusters. Unique `(match_type, match_key)`. **RLS: shared.**
- `accounts` — 10 cols; per-org. RLS: own org or regulator.
- `transactions` — 14 cols; `run_id` lets the scan pipeline scope to an upload batch. RLS: own org or regulator.
- `detection_runs` — 14 cols; `status` ∈ {pending, processing, completed, failed} — NOT `running`. RLS: own org or regulator.
- `alerts` — 16 cols; `source_type` ∈ {scan, cross_bank, str_enrichment, manual}; `status` ∈ {open, reviewing, escalated, true_positive, false_positive}. RLS: own org or regulator.
- `cases` — 17 base cols + 7 added in migration 007. RLS: own org or regulator.
- `str_reports` — 23 base cols + 1 from migration 003 + 17 from migration 005. RLS: own org or regulator.
- `rules` — 11 cols; unique `(org_id, code)`. RLS: own org OR `is_system=true` (via migration 002). Admin mutations go through a scoped system session — see commit `2113e4b`.
- `audit_log` — 8 cols; append-only, indexed on `(org_id, created_at desc)`. RLS: own org only, no regulator override.

**`002_rules_insert_policy.sql`:** RLS fix — system rules writable via `is_system=true` on insert + update.

**`003_report_types.sql`:** Adds `str_reports.report_type` (initially CHECK over `str, sar, ctr`) + creates `cash_transaction_reports` (bulk CTR, 11 cols, RLS: own org or regulator) + updates `gen_str_ref()` to use `upper(report_type)` as prefix.

**`004_typologies.sql`:** New `typologies` table — 5 cols (`id`, `title`, `category`, `channels`, `indicators`, `narrative`). Seeded with 5 Bangladesh-specific typologies. No RLS (reference data).

**`005_report_types_expanded.sql`** (goAML Task 1): Expands `str_reports.report_type` CHECK to 11 variants. Adds 17 columns on `str_reports`:
- `supplements_report_id` (FK to str_reports for Additional Information Files).
- `media_source`, `media_url`, `media_published_at` (adverse-media provenance).
- `ier_direction` (CHECK in/out), `ier_counterparty_fiu`, `ier_counterparty_country`, `ier_egmont_ref`, `ier_request_narrative`, `ier_response_narrative`, `ier_deadline`.
- `tbml_invoice_value`, `tbml_declared_value`, `tbml_lc_reference`, `tbml_hs_code`, `tbml_commodity`, `tbml_counterparty_country`.
- Replaces `gen_str_ref()` with a CASE-based prefix map: STR/SAR/CTR/TBML/COMP/IER/INT/AMSTR/AMSAR/ESC/ADDL.
- Indexes on `report_type`, `supplements_report_id`, `ier_direction`.

**`006_disseminations.sql`** (goAML Task 7): New `disseminations` table — 15 cols (org_id, dissemination_ref, recipient_agency, recipient_type, subject_summary, linked_report_ids[], linked_entity_ids[], linked_case_ids[], disseminated_by, disseminated_at, classification, metadata, created_at). Ref trigger `gen_dissem_ref()` → `DISS-YYMM-#####`. RLS: own org or regulator. 4 indexes.

**`007_case_variants.sql`** (goAML Task 8): Adds 7 columns on `cases`:
- `variant` (CHECK over 8 values: standard, proposal, rfi, operation, project, escalated, complaint, adverse_media) — separate from the existing `category` (which is the free-text subject category).
- `parent_case_id` (FK for hierarchies).
- `requested_by`, `requested_from` (RFI routing).
- `proposal_decision` (CHECK over approved/rejected/pending), `proposal_decided_by`, `proposal_decided_at`.
- 5 partial indexes.

**`008_intel_tables.sql`** (goAML Task 9): Four new tables —
- `saved_queries` (13 cols) — per-user + org-shared via `is_shared`. RLS: owner OR (shared AND same-org) OR regulator. 4 policies (SELECT, INSERT, UPDATE, DELETE).
- `diagrams` (10 cols) — manual React Flow canvases. `graph_definition` JSONB holds nodes/edges/positions. RLS: own org or regulator.
- `match_definitions` (12 cols) — custom match rules. `UNIQUE(org_id, name)`. RLS: own org or regulator.
- `match_executions` (7 cols) — FK to `match_definitions` with `ON DELETE CASCADE`. RLS inherits via parent.

**`009_reference_tables.sql`** (goAML Task 10): Single `reference_tables` table (11 cols) keyed on `(table_name, code)` UNIQUE. `table_name` CHECK over `banks, branches, countries, channels, categories, currencies, agencies`. RLS: any authed user reads; regulator-only writes (4 policies). Seeded with 197 rows: 10 channels, 12 categories, 64 banks+MFS (tagged by category), 64 countries, 30 currencies, 17 recipient agencies. `ON CONFLICT DO NOTHING` so re-application is idempotent.

## Auth and tenancy model

Flow:
1. User signs in via Supabase Auth (`web/src/lib/supabase/{client,server,middleware}.ts`).
2. `PlatformLayout` calls `requireViewer()` → either resolves from Supabase session + `profiles`, or returns demo viewer when demo mode is enabled.
3. Every `/api/*` proxy call forwards the Supabase access token via `proxyEngineRequest()`.
4. The engine `HTTPBearer` dep runs `authenticate_token()` → `decode_access_token()`. Prefers HS256 when `SUPABASE_JWT_SECRET` is set; falls back to JWKS (cache TTL 600s).
5. `resolve_authenticated_user()` loads the profile row and returns `AuthenticatedUser(user_id, email, org_id, org_type, role, persona, designation)`.
6. Role gating: `require_roles("analyst","manager","admin","superadmin")`. Additional checks in services (`_require_regulator_admin`, etc.). For `/admin/reference-tables` mutations the service layer also checks `org_type == "regulator"`.
7. Row-level isolation is Postgres RLS. `auth_org_id()` + `is_regulator()` are `SECURITY DEFINER`.

Roles (DB constraint): `superadmin`, `admin`, `manager`, `analyst`, `viewer`.
Personas: `bfiu_analyst`, `bank_camlco`, `bfiu_director`.

Demo fallback: when Supabase auth config absent AND `KESTREL_ENABLE_DEMO_MODE=true`, `authenticate_token` synthesises a user from `DEMO_USERS[KESTREL_DEMO_PERSONA]`.

RLS semantics to remember:
- `entities`, `connections`, `matches` — shared (cross-bank intelligence).
- `reference_tables` — any authed user reads; regulator writes.
- `rules` — own-org OR `is_system=true`.
- `audit_log` — own-org only, no regulator override.
- `saved_queries` — owner OR (shared + same-org) OR regulator.
- Everything else — own-org only unless caller is regulator.

## API routes

19 routers, 99 routes total, all mounted in `engine/app/main.py`.

- **`system`** (no prefix) — `GET /health`, `GET /ready`.
- **`/overview`** — `GET /overview` (persona-aware KPIs).
- **`/investigate`** — search + entity dossier.
- **`/network`** — `GET /network/entity/{id}` (two-hop graph).
- **`/scan`** — list, detail, results, `POST /scan/runs` (on-demand scan), `POST /scan/runs/upload` (multipart CSV/XLSX → parse → tagged txns → pipeline).
- **`/str-reports`** — list + CRUD + `/submit` + `/review` + `/enrich` + `/import-xml` + `/{id}/supplements` (list + create) + `/export.xlsx` (bulk) + `/{id}/export.xml` (goAML format).
- **`/ctr`** — CTR bulk import.
- **`/iers`** — list, `/outbound`, `/inbound`, `/{id}` detail, `/{id}/respond`, `/{id}/close` (manager+).
- **`/alerts`** — list, detail, `/{id}/actions` (promote to case, assign, flag, etc.), `/export.xlsx`.
- **`/cases`** — list, detail, `/{id}/actions`, `/{id}/export.pdf` (WeasyPrint), `/propose`, `/rfi`, `/{id}/decide` (manager+).
- **`/disseminations`** — list, create, detail, `/export.xlsx`.
- **`/intelligence`** — `/entities` (GET search + POST new subject with pairwise same_owner linking + `/export.xlsx`), `/matches`, `/typologies` (DB-backed).
- **`/saved-queries`** — CRUD + `/{id}/record-run`.
- **`/diagrams`** — CRUD (React Flow canvas state in `graph_definition` JSONB).
- **`/match-definitions`** — CRUD (manager+) + `/{id}/execute` (records execution; evaluator wiring is v2).
- **`/reference-tables`** — `GET ?table_name=X` + `GET /tables` (counts) + CRUD (admin+ regulator).
- **`/reports`** — national, compliance, trends, export.
- **`/admin`** — summary, settings, team, rules, api-keys, synthetic-backfill, maintenance/rules-policy-fix, **`/statistics`** (goAML-shape aggregator), **`/schedules`** (declared jobs + live worker probe).
- **`/ai`** — entity-extraction, str-narrative, typology-suggestion, executive-briefing, alerts/{id}/explanation, cases/{id}/summary.

Auth: every router except `/health` + `/ready` requires a Supabase JWT. Role gates applied per endpoint via `require_roles`. RLS enforces tenant isolation at the DB layer.

## Frontend pages

39 platform pages under `web/src/app/(platform)/`. Every one is live with real DB-backed data.

Public:
- `(public)/page.tsx` — landing, reads `/ready` live.
- `(public)/pricing/page.tsx`.

Auth: `(auth)/login`, `register`, `forgot-password` — Supabase forms.

Platform:
- **Overview:** `overview/page.tsx` — routes to `CommandView` (director) / `BankView` (CAMLCO) / `AnalystView` (bfiu_analyst). All fetch `/api/overview`. Analyst view includes a goAML welcome line pointing to `docs/goaml-coverage.md`.
- **Investigate:** `investigate/page.tsx` (omnisearch), `catalogue/page.tsx` (12 goAML-vocabulary tiles), `diagram/page.tsx` (React Flow manual builder), `entity/[id]/page.tsx` (dossier), `network/[id]/page.tsx` (graph), `trace/page.tsx` (shell).
- **Intelligence:** `intelligence/entities/page.tsx`, `entities/new/page.tsx` (Account/Person/Entity tabs), `matches/page.tsx`, `typologies/page.tsx` (DB-backed via migration 004), `saved-queries/page.tsx`, `disseminations/page.tsx` + `[id]/page.tsx`.
- **Operations:** `strs/page.tsx` + `[id]/page.tsx` (STR workspace with XML import card, type-aware sections, Supplement + Disseminate + Export dropdown actions), `alerts/page.tsx` + `[id]/page.tsx` (auto AI explanation + Draft STR + Disseminate), `cases/page.tsx` + `[id]/page.tsx` (variant filter pills, proposals kanban, proposal decision panel, Export to PDF + Disseminate), `iers/page.tsx` + `new/page.tsx` + `[id]/page.tsx` (Inbound/Outbound tabs, respond, close), `scan/page.tsx` + `history/page.tsx` + `[runId]/page.tsx` (upload path wired).
- **Command:** `reports/national`, `compliance`, `trends`, `statistics` (Recharts dashboards over `/admin/statistics`), `export`.
- **Admin:** `admin/page.tsx`, `team`, `rules`, `match-definitions`, `reference-tables` (7-tab CRUD), `schedules` (declared jobs + live Celery workers), `api-keys`.

Every page uses `PageFrame` (common) + domain-specific client components. Server components call `requireViewer()` / `requireRole(...)` at the top; the data path is exclusively `/api/*` route handlers → `proxyEngineRequest()` → engine.

## Detection engine

`engine/app/core/` is the production detection layer. Sync execution on the FastAPI request path (no Celery). Key files:

- `core/detection/rules/*.yaml` — 8 rules (rapid_cashout, fan_in_burst, fan_out_burst, structuring, layering, first_time_high_value, dormant_spike, proximity_to_bad). Loader validates schema.
- `core/detection/evaluator.py` — one `evaluate_*` function per trigger + `evaluate_accounts()` dispatcher returning `list[RuleHit]`.
- `core/detection/scorer.py` — `calculate_risk_score(rule_hits)` → `(score, severity, reasons)`. Weighted average clamped 0–100. Severity bands: critical ≥90, high ≥70, medium ≥50. **`weighted_contribution` is a percentage summing to ~100, not score-magnitude.**
- `core/resolver.py` — `normalize_identifier`, `resolve_identifier` (exact then pg_trgm fuzzy for person/business), `resolve_identifiers_from_str`, `link_subject_group` (public pairwise `same_owner` helper added for the New Subjects form).
- `core/matcher.py` — `run_cross_bank_matching` for entities with ≥2 `reporting_orgs`; upserts `matches`, emits cross_bank alerts on new/escalated.
- `core/pipeline.py` — `run_str_pipeline` (from STR submit) + `run_scan_pipeline` (from scan). `run_scan_pipeline` takes an optional `source_run_id` to scope to a single upload batch.
- `core/graph/` — `builder.py` (networkx DiGraph), `analyzer.py`, `pathfinder.py`, `export.py`.

**Scan pipeline scope rule:** `scope_org_ids=None` → all banks (regulator); `[uuid]` → that org (bank). Per-account writes (Entity, Match, Alert) attribute to `account.org_id`, not the caller. Threshold `_SCAN_SCORE_THRESHOLD = 50`.

**Modifier conditions:** All 8 rules have full condition + scoring logic. Task 6 of the intelligence-core spec wired 7 transaction-derived modifiers (`cross_bank_debit`, `senders_from_multiple_banks`, `recipients_at_different_banks`, `beneficiary_at_different_bank`, `beneficiary_is_flagged`, `multiple_npsb_sources`, `immediate_outflow`) — driven by `account.bank_code` populated on CSV ingest. The 4 graph-lookup modifiers (`proximity_to_flagged <= 2` on rapid_cashout, `involves_multiple_banks` + `circular_flow_detected` on layering, `target_confidence > 0.8` on proximity_to_bad) are wired against the entity graph the pipeline already builds — `_entity_within_hops` (undirected shortest-path), accounts_by_id bank-set, `_entity_in_cycle` (`nx.find_cycle`), and target node `risk_score / 100` respectively. All four warm up after the first scan, since they require `account.metadata_json["entity_id"]`.

**`proximity_to_bad` warm-up:** needs `account.metadata_json["entity_id"]` (assigned on first resolve), so fires from the second scan onward.

**Verification baseline (2026-04-15):** 377 accounts, 547 txns → 10 flagged, 11 alerts (3× rapid_cashout, 6× first_time_high_value, 1× fan_in_burst, 1× cross_bank_match). Divergence without cause → evaluator/scorer regression.

**Alert source types in prod:** `str_enrichment` (seed loader), `scan` (pipeline), `cross_bank` (matcher) — all three coexist.

## Seed data

**Synthetic DBBL dataset** (`engine/seed/dbbl_synthetic.py` + `load_dbbl_synthetic.py`):
1. `dbbl_synthetic.py` reads curated DBBL PDFs from `F:\New Download\Scammers' Bank statement DBBL` (local-only, never committed), parses via `engine/app/parsers/statement_pdf.py`, sanitises (stable hash-based account numbers + names, scaled amounts, shifted dates), computes `risk_profile`, and writes JSON fixtures under `engine/seed/generated/dbbl_synthetic/` (committed: `summary.json`, `organizations.json`, `statements.json`, `entities.json`, `matches.json`, `connections.json`, `transactions.json`, `manifest.json`).
2. `load_dbbl_synthetic.py::apply_dataset()` idempotently upserts into live Supabase tables using deterministic UUIDs derived from namespace `8d393384-a67a-4b64-bf0b-7b66b8d5da76`.

**Reference tables** (migration 009): 197 rows seeded inline in the migration — 10 channels (RTGS, BEFTN, NPSB, MFS, CASH, CHEQUE, CARD, WIRE, LC, DRAFT), 12 AML categories, 64 Bangladesh scheduled banks + MFS providers (tagged by category: state_owned_commercial, state_owned_development, specialized, private_commercial, private_islamic, foreign_commercial, mfs), 64 ISO-3166 country codes focused on BFIU's operational radius, 30 ISO-4217 currency codes, 17 recipient agencies (Bangladesh LE + regulators + Egmont peer FIUs). `ON CONFLICT DO NOTHING` means re-application adds only new rows.

**Typologies** (migration 004): 5 Bangladesh-specific typologies seeded at migration time.

**Current prod state** (from direct SQL against `bmlyqlkzeuoglyvfythg`): synthetic dataset is loaded — 28 entities, 377 accounts, 547 transactions, 10 STRs, 22 alerts, 1 case, 7 organizations. The goAML-patch tables (disseminations, saved_queries, diagrams, match_definitions) are empty in prod — they were only touched in end-to-end verification (records cleaned up after).

To regenerate the synthetic JSON fixtures: `python -m seed.dbbl_synthetic`. To load: `python -m seed.load_dbbl_synthetic --apply`, or via `/admin/synthetic-backfill` as a regulator admin.

Also present under `engine/seed/`: `run.py` (CI smoke test), `organizations.py`, `entities.py`, `patterns.py`, `str_reports.py`, `transactions.py`, `fixtures.py` (in-memory fixtures — used only by orphaned `core/alerter.py` at this point).

## Environment variables

Source of truth: `.env.example`.

- **Demo mode:** `KESTREL_ENABLE_DEMO_MODE` + `KESTREL_DEMO_PERSONA` (engine), `NEXT_PUBLIC_ENABLE_DEMO_MODE` + `NEXT_PUBLIC_DEMO_PERSONA` (web).
- **Supabase (web):** `NEXT_PUBLIC_SUPABASE_URL` + `NEXT_PUBLIC_SUPABASE_ANON_KEY` — if missing, web silently falls back to demo.
- **Supabase (engine):** `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_ROLE_KEY`. `SUPABASE_JWT_SECRET` enables HS256 (takes precedence over JWKS).
- **Engine core:** `DATABASE_URL` (`postgresql+asyncpg://`), `REDIS_URL`, `ALLOWED_ORIGINS`.
- **Web → engine proxy:** `ENGINE_URL` (server) or `NEXT_PUBLIC_ENGINE_URL` (client).
- **AI providers (all optional):** `OPENAI_API_KEY` + `OPENAI_MODEL`, `ANTHROPIC_API_KEY` + `ANTHROPIC_MODEL`. **Neither is set on prod Render** — `/ready` shows both as `missing_config`; heuristic fallback handles every AI task. Set either key to flip provider routing live.
- **Hardcoded defaults** not in `.env.example`: `ALGORITHM`, `APP_VERSION`, `ENVIRONMENT`.

## Sovereign Ledger

Institutional-brutalist UI rebrand living on `feature/sovereign-ledger`. **Design direction came from Gemini 3.1** ("national security infrastructure, not SaaS"). Preview URL auto-updates on push: `https://kestrel-git-feature-sovereign-ledger-enso-intelligence.vercel.app` (Vercel SSO-protected).

**Canonical design doc:** `.claude/skills/kestrel-design/SKILL.md` — always read it before any UI work.

**Tokens** (scoped under `.platform-surface` in `globals.css`):
- bg `#0F1115` · foreground `#EAE6DA` (bone) · card `#15171C` · border `rgba(234, 230, 218, 0.10)`
- accent + destructive = vermillion `#FF3823` (alarm-only)
- `--radius: 0` (zero rounding inside the scope) · rounded-full pills flattened via global override
- font-sans → IBM Plex Sans (humanist body) · font-mono → IBM Plex Mono (IDs, timestamps, amounts, eyebrows)
- The landing uses a parallel `--landing-*` family in the same globals.css — same visual, separate scope.

**Patterns established:**
- Section frame: `<section className="border border-border">` with a `border-b border-border px-6 py-5` header containing a `font-mono text-[10px] uppercase tracking-[0.28em] text-muted-foreground` eyebrow prefixed with `<span className="text-accent">┼</span>`. Use shared helpers `Section` / `Field` / `Meta` where they exist in the rewritten components.
- Eyebrow → title → description cadence is mandatory on every dressed surface.
- Badges / pills inverted-on-active mono strips (filter rows, variant tabs, tab navigation).
- Error strings render as `font-mono text-xs uppercase tracking-[0.18em] text-destructive` with `<span>┼</span> ERROR · {detail}`.
- Notice strings render as `font-mono text-xs uppercase tracking-[0.18em] text-accent` with `<span>┼</span>` prefix.
- Three-tone status (muted / foreground / accent) replaces every rainbow badge map. See `StatusBadge`, `RiskScore`, `SeverityPill`.
- Data cells: mono for IDs (truncated with `··` middle ellipsis), mono tabular-nums for amounts, mono uppercase tracking-[0.18em] for timestamps.
- Recharts: mono Plex tick labels, zero-radius hairline tooltips, grid in 8% bone, monochromatic series palette (vermillion → bone → muted → dim greys).
- React Flow nodes: `borderRadius: 0`, hairline border (vermillion when risk ≥ 90 or selection = alarm), Plex Mono label, bg `#15171C` (alarm-tinted when flagged). See `components/investigate/network-canvas.tsx` and `components/intel/diagram-builder.tsx` for the reference implementation.

**KestrelMark component** (`web/src/components/common/kestrel-mark.tsx`) is the single source of truth for the brand mark. Renders inline SVGs — bone bird silhouette + vermillion registration crosshair on dark surfaces (primary), slate bird + bone crosshair on light surfaces (inverse). Variants: `lockup` / `mark` / `wordmark`. Sizes sm/md/lg. Source SVGs live next to the component (`kestrel-mark.svg`, `kestrel-mark-dark.svg`, `kestrel-wordmark.svg`). Favicon at `web/src/app/icon.svg`, Apple touch icon via `web/src/app/apple-icon.tsx` (ImageResponse, 180×180), OG social card via `web/src/app/opengraph-image.tsx` (1200×630).

**Phase 6 (polish, non-blocking):**
1. Lighthouse ≥ 95 on public, ≥ 90 on in-app.
2. a11y sweep — keyboard, contrast, `prefers-reduced-motion`, screen-reader labels on icon-only buttons.
3. Mobile breakpoint pass.
4. Refresh pre-rebrand screenshots in `docs/goaml-coverage.md` with real Sovereign Ledger captures.
5. Update kestrel-design SKILL.md with final helper-component patterns (Section/Field/Meta) + Recharts palette.

**Launch completed 2026-04-18.** Migration 010 is applied to prod Supabase `bmlyqlkzeuoglyvfythg` (the `access_requests` table, fixed from `profiles.user_id` → `profiles.id` mid-apply because the profiles table uses `id` as the `auth.uid()` FK). `SUPABASE_SERVICE_ROLE_KEY` is set on the Vercel web env. `feature/sovereign-ledger` merged `--no-ff` to `main` and pushed (`92164b1`); Vercel rebuilt prod automatically.

## What to work on next

No KESTREL-*-PROMPT.md items remain. The Sovereign Ledger rebrand is shipped; Phase 6 polish is the only UI work outstanding. Priorities for the next session:

**Blocks first BFIU meeting:**
1. **Demo film production.** Not a code task, but the most important next step. The platform is ready to be shown — a recorded walkthrough of Director → Analyst → CAMLCO personas hitting each of the 13 goAML-coverage items against the synthetic DBBL dataset would compress the first meeting from an hour to ten minutes.

**Post-first-meeting polish:**
3. **Scheduled rule execution wiring.** `/admin/schedules` surfaces three declared jobs with status `not_configured` because no Celery Beat schedule is populated. Move `run_scan_pipeline` into a Celery task, wire the nightly + daily-digest + weekly-compliance jobs into `app.tasks.celery_app.celery_app.conf.beat_schedule`, flip the declared entries from `not_configured` to `scheduled`.
4. **Real rule expression DSL.** Current evaluator uses dict-keyed lookup of modifier strings. A richer DSL (or a hosted rule editor consuming `match_definitions`) would let BFIU analysts define custom rules without editing YAML in git. The match_definitions table + `/admin/match-definitions` UI are ready; the evaluator wiring is the missing piece.
6. **Outbound goAML adapter.** Distinct from the XML import/export we shipped (those are file-based). This is a machine-to-machine adapter that pushes reports into goAML's central server for FIUs running both systems in parallel. `engine/app/adapters/goaml.py` exists as a stub.
7. **AI red-team harness.** Structured adversarial prompts + evaluation scoring for the AI task surface. `engine/app/ai/evaluations.py` has the scaffold; needs a prompt corpus, expected-output fixtures, and a CI gate before real provider keys go live on Render.
8. **Delete orphaned `core/alerter.py`** once `seed/fixtures.py` references are cleaned up (fixtures are themselves orphaned since the DB-backed typologies migration).
9. **Landing-page BBC.** `web/src/lib/demo.ts` still seeds public-page persona cards with hardcoded fixtures — not a correctness issue but should be reviewed against the new intelligence surface.

## Code conventions

Observed by reading the code, not invented:

**Python (engine):**
- FastAPI routers are one-file-per-domain in `engine/app/routers/`; they do only parameter wiring, auth dependencies, and delegation to `engine/app/services/`.
- Services accept `AsyncSession` + keyword-only `user: AuthenticatedUser` and return plain dicts (or typed responses).
- SQLAlchemy 2 async: `select(...)`, `session.execute()`, `.scalars()`. `select(Model.id, ...)` for narrow projections.
- Helpers `_as_uuid`, `_as_float`, `_iso`, `_safe_int` are duplicated per service file (not centralized). Low cost, explicit.
- Audit logging is manual: mutation services insert an `AuditLog` row with `action=f"<resource>.<verb>"` and `details=request.model_dump()` before `await session.commit()`.
- All DB-touching code lives under `engine/app/services/`; routers never execute SQL directly.
- Pydantic `model_validate(dict)` turns service dicts into response models.
- AI provider contracts live in `engine/app/ai/`; nothing else should talk to OpenAI/Anthropic.
- Dependency injection uses `Annotated[T, Depends(...)]` consistently.
- Role gates: `require_roles("analyst","manager","admin","superadmin")`; additional checks in services.
- Test files follow `test_<domain>_phase<n>.py` or `test_*_core.py` naming.

**TypeScript (web):**
- Next.js App Router with route groups: `(public)`, `(auth)`, `(platform)`.
- Server components call `requireViewer()` / `requireRole(...)` at the top; redirect on failure.
- Data fetching: Next route handlers under `web/src/app/api/**/route.ts` which proxy to the engine via `proxyEngineRequest`. Components never fetch the engine directly.
- Per-domain normalisers in `web/src/lib/` translate snake_case engine payloads → camelCase domain types in `web/src/types/domain.ts`.
- Client components use `"use client"`, `useState` + `useEffect`, `LoadingState` / `EmptyState` / `ErrorState` commons.
- shadcn-style UI primitives in `web/src/components/ui/` are composed by domain components.
- Navigation config-driven via `web/src/components/shell/nav-config.ts` with persona/role filters + optional `aka` (goAML vocabulary) tooltip.
- `PageFrame` is the canonical page wrapper (eyebrow, title, description, actions slot).
- Download endpoints forward raw bytes + preserved `Content-Disposition` through the proxy — do not wrap with `NextResponse.json`.
- No global state library is actively used (`zustand` is installed but local state + server components cover everything).

## Commands

**Web (`web/`):**
- `npm install` — install (Node 22.x).
- `npm run dev` — dev server.
- `npm run build` — production build.
- `npm run start` — run the built app.
- `npm run lint` — ESLint via `eslint-config-next`.

**Engine (`engine/`):**
- `pip install -e .[dev]` — install runtime + dev deps.
- `uvicorn app.main:app --reload` — dev API.
- `celery -A app.tasks.celery_app.celery_app worker --loglevel=INFO` — worker (same command as Render).
- `pytest -q` — run tests (95 tests).
- `python seed/run.py` — manifest smoke test (runs in CI).
- `python -m seed.dbbl_synthetic` — regenerate synthetic JSON fixtures from local DBBL PDFs.
- `python -m seed.load_dbbl_synthetic` — print the load plan against `DATABASE_URL`.
- `python -m seed.load_dbbl_synthetic --apply` — upsert the synthetic dataset.

**Import check before pushing** (memory lesson from SAR/CTR rollout): `python -c "from app.main import app; print(len(app.routes))"`. `py_compile` alone does NOT catch broken imports; Render fails at uvicorn boot. Also verify new third-party packages are declared in `pyproject.toml`.

**Database:** apply migrations in order `001` → `009` via Supabase SQL editor or the Supabase MCP `apply_migration` tool.

**Deployment:**
- Vercel production: push to `main` touching `web/**` with `VERCEL_*` secrets set.
- Render production: push to `main` touching `engine/**` or `supabase/**` with `RENDER_*` deploy hook secrets set. Deploy hook completes in ~45–60s; uvicorn startup another ~20s.
- No Makefile, no `justfile`, no local `docker-compose`.

## Known issues

Non-obvious gotchas that trip first-time readers:

1. **Demo fallback is silent.** `web/src/lib/auth.ts::getCurrentViewer` returns demo viewer when Supabase client is null. Production has env vars set — only matters if removed.
2. **`detection_runs.status` CHECK** — `pending|processing|completed|failed` only. NOT `running` (fix: `d55aa90`).
3. **Rule RLS policy chain.** Commits `76b76f8` → `4e1af27` fix admin rule mutations via `scoped system session` in `services.admin.update_rule_configuration` + maintenance endpoint `POST /admin/maintenance/rules-policy-fix`. Don't simplify without understanding why the direct session failed.
4. **`_load_profile_context` swallows DB errors.** `engine/app/auth.py` catches `Exception` → `None` → falls back to JWT/demo. Broken DB looks like "not provisioned" instead of 500.
5. **Two `supabase` client paths.** `web/src/lib/supabase/` (folder) vs any `supabase.ts` import. Check the folder first.
6. **`proxy.ts` is the Next middleware.** Don't rename — tooling depends on it.
7. **Vercel SSR may 500 during Render redeploy.** Transient; reload after `Application startup complete`.
8. **`weighted_contribution` bug (fixed `7aed54f`).** Values above 100 = reintroduced bug.
9. **`py_compile` alone does not catch broken imports.** Before pushing branches with new imports run `cd engine && python -c "from app.main import app"`. Also verify third-party packages are declared in `pyproject.toml` (case: `jinja2` transitively present locally but missing from `pyproject.toml` → Render fresh install failed, fixed `390b2f1`; `lxml` required this for Task 2).
10. **Error envelope covers Starlette 404s too.** The Phase 10 middleware wraps FastAPI `HTTPException`, but Starlette's router-level 404s bypass that handler by default. Fix `73f09d4` registers a separate `StarletteHTTPException` handler. Don't consolidate the two — the Starlette one catches routes the FastAPI handler never sees.
11. **`cases.variant` is separate from `cases.category`.** Migration 007 added `variant` (goAML case classification) alongside the existing `category` (free-text subject category like `fraud`) because `category` already held real data in prod. Don't conflate them.
12. **`gen_str_ref()` short-code prefix map.** Migration 005 replaced the old `upper(report_type)` prefix with a CASE map (STR/SAR/CTR/TBML/COMP/IER/INT/AMSTR/AMSAR/ESC/ADDL). Any new report_type value added to the CHECK constraint needs a new branch in the CASE or it'll fall through to `upper(...)` and produce long prefixes.
13. **Download proxy routes must forward bytes.** Never `NextResponse.json()` a PDF/XLSX/XML response — convert `arrayBuffer()` then `new NextResponse(body, { headers: ... })`. Copy the `Content-Disposition` header from the engine.
14. **`STRDraftUpsert` validator is strict on type-specific fields.** Posting `report_type='ier'` without `ier_direction` + `ier_counterparty_fiu` will 422 at Pydantic validation before the router sees it. Additional Information Files need `supplements_report_id`; TBML needs `tbml_counterparty_country`; adverse media needs `media_source`. When creating supplements via `POST /str-reports/{id}/supplements`, the router forces both fields so the client doesn't need to.
15. **Observability hook false-positives.** The Vercel plugin's `posttooluse-validate` hook fires on every route handler asking for "observability instrumentation." Kestrel's engine-side structured JSON logs + X-Request-ID cover every proxied call; adding per-proxy-route instrumentation would be duplicative. Skip these suggestions.
