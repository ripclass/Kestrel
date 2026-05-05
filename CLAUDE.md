# Kestrel — Project Intelligence

## What is this

Kestrel is a standalone financial crime intelligence platform for Bangladesh. It sits between commercial banks (and MFS/NBFIs) and the Bangladesh Financial Intelligence Unit (BFIU), providing cross-bank entity intelligence, network analysis, explainable alerts, case management, native STR workflows, and command-level reporting. Positioned as a **complete goAML replacement** — banks can continue filing in goAML XML (import + export round-trip), BFIU analysts see the familiar vocabulary (Catalogue Search, IER, Match Definitions, Disseminations), and the platform adds AI-native intelligence goAML cannot provide. Three personas on one platform: `bfiu_analyst`, `bank_camlco`, `bfiu_director`. The procurement-facing capability map is at `docs/goaml-coverage.md`.

## Current state

> **Prod (2026-05-05):** V2 fully shipped (phases 1-6) + **V3 phase 1 (AI outcome logging) shipped** — last engine commit `157fa73`. Live on `kestrel-nine.vercel.app` + `kestrel-engine.onrender.com`. AI via OpenRouter (`anthropic/claude-sonnet-4.6`). All 3 Render services running. Migrations 001–019 applied. **019** (`ai_outcome_log`) is the foundation for the V3 sovereign-AI track — every AI call now writes a row with the redacted prompt, structured output, latency, token counts, and analyst correction (if any). Capability matrix at `docs/world-class-capability-matrix.md`: 14/18 Excellent, 2 Partial-with-plan, 0 Missing.

Ten build-out sessions shipped end-to-end:
- **Intelligence-core** (2026-04-15/16): real detection engine (8 YAML rules + evaluator + scorer + resolver + matcher + pipeline), scan upload path, WeasyPrint PDF case pack, SAR/CTR report types, AI alert auto-explanation + Draft STR, DB-backed typologies, CommandView polish, modifier conditions, incremental scan scope, Phase 10 hardening (request IDs + structured JSON logs + standardised error envelope + `docs/RUNBOOK.md`).
- **goAML coverage patch** (2026-04-17): all 13 items from `KESTREL-GOAML-COVERAGE-PROMPT.md`. Migrations 005–009 applied. 11 report-type variants, goAML XML import + export, `/iers` workflow, Additional Information Files, 3-tab New Subjects form, Catalogue tile grid, dissemination ledger, 8-variant case enum with proposal kanban + RFI routing, saved queries + manual diagram builder + match definitions, reference tables (197 seed rows), operational statistics dashboards, scheduled-processes admin surface, XLSX + goAML-XML exports, goAML vocabulary tooltips, `docs/goaml-coverage.md`.
- **Sovereign Ledger rebrand** (2026-04-18): institutional-brutalist UI direction merged. See §"Sovereign Ledger".
- **Post-rebrand sweep** (2026-04-19): graph-lookup modifiers wired (`a55d65d`), Celery Beat schedule wired (`b561949`), orphaned alerter cleanup (`ee16cb3`), JSON-DSL executor for match_definitions (`3ca6528`), a11y focus indicator + reduced-motion (`56bd851`), mobile nav drawer (`f764cfb`), a11y skip-link (`c1edceb`), AI red-team harness (`d122e7d`).
- **V2 phase 1: cross-bank intelligence** (2026-05-04): cross-bank dashboard with persona-aware anonymisation (`d64049d`), multi-bank synthetic seed module (`6bd2366`), procurement whitepaper (`dfbfca3`). See §"Cross-bank intelligence" below.
- **V2 phase 2: bank-direct surface** (2026-05-05): bank-direct landing at `/banks` (P2.1 `5932e9c`), self-serve signup at `/signup/bank` (P2.2 `98e21ae`), demo-bank seed loader + Beat dispatch (P2.3 `0b15a23`), persona-isolation verification + migration 013 hot-fix (P2.4 `857f415`), Resend wiring on briefing-intake (P2.5 `166818e`). See §"Bank-direct surface (V2 P2)" below.
- **V2 phase 3: real-time transaction-scoring API** (2026-05-05): per-transaction `POST /transactions/score` + feedback endpoint + recent stream + migration 014 (P3.1+P3.2+P3.3 `1dc575a`), monitoring dashboard at `/monitoring/realtime` + `GET /transactions/score/metrics` engine route + `docs/api-integration.md` (P3.4+P3.5 `67d038b`). See §"Real-time transaction-scoring (V2 P3)" below.
- **V2 phase 4: sanctions / PEP / adverse-media screening** (2026-05-05): `/screening/entity` fuzzy-match service + adverse-media stub + migration 015 (`watchlist_entries`) + Celery ingestion framework + 22-row synthetic seed across 5 sources + realtime inline integration (P4.1-P4.3+P4.5 `f566f35`). Screening UI at `/screen` + nav entry + `docs/api-integration.md` §8 (P4.4 `e060ce7`). See §"Sanctions / PEP / adverse-media screening (V2 P4)" below.
- **V2 phase 5: KYC / CDD onboarding** (2026-05-05): `/customers` 6-route surface + KYC service that screens primary + beneficial owners inline + migration 016 (`customers` + alerts.source_type relaxation) + Beat-driven re-screening at 03:00 BDT + 13-row synthetic seed for Sonali Bank (P5.1+P5.2+P5.4 `74fbbe6`). KYC UI at `/customers` (list + new + detail) + nav entry (bank persona only) + docs §9 (P5.3 `50aff3f`). See §"KYC / CDD onboarding (V2 P5)" below.
- **V2 phase 6: status / pricing / demo polish** (2026-05-05): public status surface at `/status` driven by `uptime_pings` 5-min Beat ledger + `status_incidents` ledger (P6.1 engine + web). Pricing-tier enforcement via migrations 017+018 + `services/billing.py` + 402 PAYMENT REQUIRED on starter-tier calls to paid features (P6.2). Weekly demo refresher Beat task at Mon 04:00 BDT (P6.3). `/demo` public route with persona switcher (P6.3 web). `docs/world-class-capability-matrix.md` (new) closes V2 with 14/18 capabilities at Excellent (P6.4). Engine commit `caf7507`; web commit pending. See §"Status + pricing + demo (V2 P6)" below.

**Aggregate prod state:**
- 123 engine routes across 23 routers (6 new in V2 P6: status_public router with summary/incidents/plans + admin status incident management). 268/268 pytest. `GET /ready` on `https://kestrel-engine.onrender.com` shows auth/db/redis/storage/worker=ok; `ai:openai = skipped` with model `anthropic/claude-sonnet-4.6` (configured + reachability probe disabled).
- Migrations 001–013 applied. 012 (`advisor_fixes`) locked `search_path = ''` on 7 SECURITY DEFINER helpers; 013 (`qualify_security_definer_helpers`, 2026-05-05) schema-qualified the 5 of those that referenced unqualified relations/sequences. Migrations 001 + 002 retroactively recorded in `supabase_migrations.schema_migrations` after the audit found them missing.
- Prod data (post V2 phase 2 — no bank tenant has signed up via /signup/bank yet, so demo-bank seed has never fired): 197 reference_tables, 5 typologies, **52 entities** (28 pre-V2 + 24 multi-bank seed), 377 accounts, 547 transactions, **10 STRs**, **40 alerts**, 1 case, **7 matches**.
- All 40 `(platform)` pages live + 2 new `(public)` pages from V2 P2: `/banks` (bank-direct landing) and `/signup/bank` (force-dynamic, feature-flag gated). The platform-page count is unchanged.
- All Render services running: engine, worker, beat. Beat schedule now dispatches 4 jobs: nightly scan (02:00 BDT), daily digest (06:30 BDT), weekly compliance (Mon 05:00 BDT), and the new `demo_bank_seed_pending` (every 10 min) which seeds new bank tenants flagged via `organizations.settings.demo_seed_pending=true`.

What is scaffolded but NOT wired the way the code implies:
- **Inline pipelines.** Every on-demand path (STR submit, ad-hoc scan, scan upload, XML import, match execution) runs inline in the FastAPI request path. Celery worker now also runs the three scheduled jobs since Beat is alive. On-demand execution is intentionally synchronous.
- **goAML *outbound* adapter is a stub.** `engine/app/adapters/goaml.py` exists; machine-to-machine sync into goAML's central server is not implemented. Distinct from the file-based XML import/export.

What V2 ships next (not in main yet — see `KESTREL-WORLD-CLASS-BUILD-V2.md` and `KESTREL-RESUME-V2.md`):
- **Phase 3** Real-time transaction-scoring API (sub-500ms decisioning).
- **Phase 4** Sanctions / PEP / adverse-media screening (OFAC/EU/UN/UK + adverse-media adapter).
- **Phase 5** KYC / CDD module (greenfield).
- **Phase 6** Public status page + pricing-tier enforcement + demo-flow polish.

## Architecture

### Stack
- **Frontend**: Next.js 16.2.2 App Router, React 19.2.4, TypeScript 5, Tailwind v4, shadcn-style UI, `@xyflow/react` (network graphs), `recharts`, `zustand`, `zod`, `@tanstack/react-table`, `date-fns`. Node pinned to 22.x.
- **Backend**: Python `>=3.12` (pinned 3.12.8 via `engine/.python-version`), FastAPI `>=0.115`, SQLAlchemy 2 async + asyncpg, Pydantic v2, `python-jose`, `networkx`, `celery[redis]`, `PyYAML`, `pdfplumber`, `pandas`, `openpyxl`, `weasyprint`, `lxml`, `jinja2`, `httpx`. Build backend: `hatchling`.
- **Database**: Supabase Postgres. Schema source of truth: `supabase/migrations/001_schema.sql` → `013_*.sql`.
- **Auth**: Supabase Auth. Engine validates two ways: `SUPABASE_JWT_SECRET` (HS256, preferred) or JWKS at `{SUPABASE_URL}/auth/v1/.well-known/jwks.json` (10-min cache). See `engine/app/auth.py`.
- **Storage**: Supabase Storage, buckets `kestrel-uploads` + `kestrel-exports` (configurable via `STORAGE_BUCKET_*`). Scan uploads write raw CSV/XLSX to `kestrel-uploads`; PDF/XLSX/XML exports stream directly. Readiness probe verifies both buckets.
- **Cache/Queue**: Redis on Render. Celery app `kestrel` at `app.tasks.celery_app.celery_app`. Tasks: `worker.ping`, `app.tasks.scan_tasks.run_all_orgs`, `app.tasks.str_tasks.daily_digest`, `app.tasks.export_tasks.weekly_compliance_report`, `app.tasks.demo_seed_tasks.apply_pending` (V2 P2.3). Beat at 02:00 / 06:30 / Mon 05:00 Asia/Dhaka + every 10 min for `apply_pending`.
- **AI**: Provider abstraction in `engine/app/ai/` — OpenAI / Anthropic adapters + `HeuristicProvider` fallback. Task routing, prompt registry, redaction, invocation audit, red-team harness. **Prod runs `anthropic/claude-sonnet-4.6` via OpenRouter through the OpenAI-compatible adapter** (`OPENAI_API_KEY=sk-or-v1-...`, `OPENAI_BASE_URL=https://openrouter.ai/api/v1`, `OPENAI_MODEL=anthropic/claude-sonnet-4.6`). `ANTHROPIC_*` left blank — task routes that prefer Anthropic provider fall through to the OpenAI adapter (which is the OpenRouter→Claude pipe).

### Deployment
- `web/` → Vercel via `deploy-web-production.yml` (prebuilt deploy; gated on `VERCEL_TOKEN` / `VERCEL_ORG_ID` / `VERCEL_PROJECT_ID`).
- `engine/` → Render. `engine/render.yaml` declares 3 services: `kestrel-engine` (FastAPI), `kestrel-worker` (Celery), `kestrel-beat`. Deploy via per-service hooks: `RENDER_ENGINE_DEPLOY_HOOK_URL`, `RENDER_WORKER_DEPLOY_HOOK_URL`, `RENDER_BEAT_DEPLOY_HOOK_URL`. Each gated independently.
- DB → Supabase project `bmlyqlkzeuoglyvfythg`. Connection via `DATABASE_URL` (`postgresql+asyncpg://...`) + `SUPABASE_*` envs.
- **CI**: `.github/workflows/ci.yml` (web lint+build, engine pip+pytest+seed smoke), `deploy-web-production.yml`, `deploy-engine-production.yml`, `vercel-prebuilt-check.yml`.

### Key directories
- `web/src/app/(public)/` — landing (`/`) + bank-direct landing (`/banks`, V2 P2.1) + bank-direct signup (`/signup/bank`, V2 P2.2, force-dynamic, gated on `ENABLE_BANK_DIRECT_SIGNUP`).
- `web/src/app/(auth)/` — login, register, forgot-password.
- `web/src/app/(platform)/` — 40 authenticated pages (39 pre-V2 + `/intelligence/cross-bank` from P1.1).
- `web/src/app/api/` — Next route handlers proxying engine via `lib/engine-server.ts`. Download endpoints forward raw bytes with preserved `Content-Disposition`.
- `web/src/app/actions/` — server actions: `access.ts` (briefing intake + Resend notification, V2 P2.5), `bank-signup.ts` (V2 P2.2; service-role org create + `auth.admin.inviteUserByEmail`).
- `web/src/components/` — `shell/`, `common/`, plus per-domain folders. New in V2 P2: `web/src/components/banks/` (8 sections + signup form).
- `web/src/lib/` — Supabase clients, `auth.ts`, `engine-server.ts`, per-domain normalizers, `demo.ts`, `runtime.ts` (env-flag helpers including `isBankDirectSignupEnabled`).
- `engine/app/routers/` — 19 files, one per domain.
- `engine/app/services/` — 28 files, all DB-backed; routers never execute SQL directly. (`cross_bank.py` added in V2 P1.1.)
- `engine/app/models/` — 21 SQLAlchemy models.
- `engine/app/core/` — `detection/` (rules YAML + loader/evaluator/scorer), `resolver.py`, `matcher.py`, `pipeline.py`, `match_dsl.py`, `graph/`.
- `engine/app/parsers/` — `csv.py`, `xlsx.py`, `statement_pdf.py`, `goaml_xml.py` (lxml-based, permissive).
- `engine/app/ai/` — provider abstraction + redaction + audit + redteam.
- `engine/app/tasks/` — Celery tasks: scan / str / export / `demo_seed_tasks` (V2 P2.3) + `celery_app.py` + `_runtime.py` (per-task NullPool engine).
- `engine/seed/` — synthetic data generators (`dbbl_synthetic.py` + `load_dbbl_synthetic.py` for the original DBBL fixture; `multi_bank_synthetic.py` + `multi_bank_to_sql.py` from V2 P1.2 for cross-bank topology across BRAC / City / Islami / Sonali; `load_demo_bank.py` from V2 P2.3 for new bank tenants).
- `supabase/migrations/` — 13 files.
- `docs/` — `production-plan.md`, `goaml-coverage.md` (procurement), `RUNBOOK.md`, `production-audit-2026-04.md` (engineering ground-truth baseline), `cross-bank-intelligence.md` + `.html` (V2 P1.3 procurement whitepaper), `multi-tenant-isolation-verified.md` (V2 P2.4 procurement-grade isolation proof), `render_pdf.py` (markdown → HTML/PDF for whitepapers).

## Database schema

All tables RLS-enabled. Helper functions: `auth_org_id()`, `is_regulator()`, `handle_new_user()`, `update_timestamp()`, `gen_case_ref()`, `gen_str_ref()`, `gen_dissem_ref()`.

**Migration 001 core tables:**
- `organizations`: `org_type` ∈ {regulator, bank, mfs, nbfi}.
- `profiles`: `role` ∈ {superadmin, admin, manager, analyst, viewer}; `persona` ∈ {bfiu_analyst, bank_camlco, bfiu_director}. Auto-inserted from `auth.users`.
- `entities`: canonical shared-intelligence identity; `entity_type` ∈ {account, phone, wallet, nid, device, ip, url, person, business}; unique `(entity_type, canonical_value)`; GIN trigram on `display_value`. **RLS shared** across all authed users (cross-bank intel).
- `connections`, `matches`: also **RLS shared**.
- `accounts`, `transactions` (`run_id` scopes scan batches): per-org RLS.
- `detection_runs`: `status` ∈ {pending, processing, completed, failed} — NOT `running`.
- `alerts`: `source_type` ∈ {scan, cross_bank, str_enrichment, manual, match_definition} (last added in 011); `status` ∈ {open, reviewing, escalated, true_positive, false_positive}.
- `cases`: 17 base cols + 7 from migration 007.
- `str_reports`: 23 base cols + 1 from 003 + 17 from 005.
- `rules`: unique `(org_id, code)`. RLS: own org OR `is_system=true` (via 002). Admin mutations go through scoped system session — see commit `2113e4b`.
- `audit_log`: append-only. RLS: own org only, no regulator override.

**Subsequent migrations (read the SQL files for full column lists):**
- **002** — RLS fix: system rules writable via `is_system=true`.
- **003** — Adds `str_reports.report_type` + `cash_transaction_reports` table + updates `gen_str_ref()`.
- **004** — `typologies` table (no RLS, reference data); 5 Bangladesh typologies seeded.
- **005** (goAML T1) — Expands `report_type` CHECK to 11 variants. Adds 17 cols on `str_reports` (supplements_report_id, media_*, ier_*, tbml_*). Replaces `gen_str_ref()` with CASE-based prefix map: STR/SAR/CTR/TBML/COMP/IER/INT/AMSTR/AMSAR/ESC/ADDL.
- **006** (goAML T7) — `disseminations` table; `gen_dissem_ref()` → `DISS-YYMM-#####`.
- **007** (goAML T8) — Adds 7 cols on `cases`: `variant` (8 values: standard/proposal/rfi/operation/project/escalated/complaint/adverse_media), `parent_case_id`, RFI routing fields, proposal decision fields.
- **008** (goAML T9) — Four new tables: `saved_queries` (owner OR shared+same-org OR regulator RLS), `diagrams`, `match_definitions`, `match_executions`.
- **009** (goAML T10) — `reference_tables` keyed `(table_name, code)` UNIQUE; `table_name` ∈ {banks, branches, countries, channels, categories, currencies, agencies}; any authed reads, regulator writes. Seeded with 197 rows. `ON CONFLICT DO NOTHING`.
- **010** — `access_requests` table for landing intake. Uses `profiles.id` (NOT `profiles.user_id`) as auth FK.
- **011** — Relaxes `alerts.source_type` CHECK to include `match_definition`.
- **012** (`advisor_fixes`, 2026-05-04) — Locks `SET search_path = ''` on 7 SECURITY DEFINER helpers + `ALTER EXTENSION pg_trgm SET SCHEMA extensions`. Closed 6 of 13 advisor warnings. Documented audit-deferred warnings inline.
- **013** (`qualify_security_definer_helpers`, 2026-05-05) — Hot-fix for 012. Schema-qualifies 5 of those 7 functions (`auth_org_id`, `is_regulator`, `gen_case_ref`, `gen_str_ref`, `gen_dissem_ref`) which referenced unqualified relations/sequences and broke under empty search_path. Without 013, every cases / STR / dissemination INSERT failed and every direct-PostgREST RLS evaluation failed. Production blast radius was masked because the engine connects as `postgres` (BYPASSRLS) and never invoked the helpers from that role; only the trigger writes were broken — and the regression window was 30 hours of zero new cases / STRs / disseminations. Discovered during V2 P2.4 isolation simulation.

## Auth and tenancy model

Flow:
1. User signs in via Supabase Auth (`web/src/lib/supabase/{client,server,middleware}.ts`).
2. `PlatformLayout` calls `requireViewer()` → resolves from Supabase session + `profiles`, or returns demo viewer.
3. Every `/api/*` proxy call forwards Supabase access token via `proxyEngineRequest()`.
4. Engine `HTTPBearer` runs `authenticate_token()` → `decode_access_token()` (HS256 if secret set, else JWKS).
5. `resolve_authenticated_user()` returns `AuthenticatedUser(user_id, email, org_id, org_type, role, persona, designation)`.
6. Role gating via `require_roles(...)`. `/admin/reference-tables` mutations also require `org_type == "regulator"`.
7. Row-level isolation is Postgres RLS. `auth_org_id()` + `is_regulator()` are `SECURITY DEFINER`.

Demo fallback: when Supabase config absent AND `KESTREL_ENABLE_DEMO_MODE=true`, `authenticate_token` synthesises a user from `DEMO_USERS[KESTREL_DEMO_PERSONA]`.

RLS semantics:
- `entities`, `connections`, `matches` — shared (cross-bank intel).
- `reference_tables` — any authed reads; regulator writes.
- `rules` — own-org OR `is_system=true`.
- `audit_log` — own-org only, no regulator override.
- `saved_queries` — owner OR (shared + same-org) OR regulator.
- Everything else — own-org only unless caller is regulator.

## API routes

19 routers, 99 routes, all mounted in `engine/app/main.py`. Auth: every router except `/health` + `/ready` requires Supabase JWT. Read each router file for endpoint specifics — high-level surface:

- **`system`** (no prefix) — `GET /health`, `GET /ready`.
- **`/overview`** — persona-aware KPIs.
- **`/investigate`**, **`/network`** — search, dossier, two-hop graph.
- **`/scan`** — runs, results, `POST /scan/runs/upload` (multipart CSV/XLSX → pipeline).
- **`/str-reports`** — CRUD + submit + review + enrich + import-xml + supplements + export.xlsx + `{id}/export.xml`.
- **`/ctr`**, **`/iers`**, **`/alerts`**, **`/cases`** — domain CRUD + actions + exports. Cases include `/{id}/export.pdf` (WeasyPrint), `/propose`, `/rfi`, `/{id}/decide`.
- **`/disseminations`**, **`/intelligence`** (entities/matches/typologies + V2 P1.1 `/intelligence/cross-bank/{summary,matches,heatmap,top-entities}` persona-aware reads), **`/saved-queries`**, **`/diagrams`**, **`/match-definitions`**, **`/reference-tables`**.
- **`/reports`** — national, compliance, trends, export.
- **`/admin`** — summary, settings, team, rules, api-keys, synthetic-backfill, maintenance/rules-policy-fix, statistics, schedules.
- **`/ai`** — entity-extraction, str-narrative, typology-suggestion, executive-briefing, alerts/{id}/explanation, cases/{id}/summary.

## Frontend pages

39 platform pages under `web/src/app/(platform)/`. Every page uses `PageFrame` + domain-specific client components. Server components call `requireViewer()` / `requireRole(...)` at the top; data path is exclusively `/api/*` route handlers → `proxyEngineRequest()` → engine.

Top-level groups: **Overview** (persona-routed CommandView/BankView/AnalystView), **Investigate** (omnisearch, catalogue, diagram builder, entity dossier, network graph, trace), **Intelligence** (entities + new-subject 3-tab form, matches, typologies, saved-queries, disseminations), **Operations** (strs, alerts, cases with variant filter pills + proposals kanban, iers Inbound/Outbound, scan), **Command** (national/compliance/trends/statistics Recharts dashboards, export), **Admin** (team, rules, match-definitions, reference-tables 7-tab CRUD, schedules, api-keys).

## Detection engine

`engine/app/core/` is the production detection layer. Sync execution on the FastAPI request path (no Celery).

- `core/detection/rules/*.yaml` — 8 rules: rapid_cashout, fan_in_burst, fan_out_burst, structuring, layering, first_time_high_value, dormant_spike, proximity_to_bad.
- `core/detection/evaluator.py` — one `evaluate_*` per trigger + `evaluate_accounts()` dispatcher → `list[RuleHit]`.
- `core/detection/scorer.py` — `calculate_risk_score(rule_hits)` → `(score, severity, reasons)`. Weighted average clamped 0–100. Severity bands: critical ≥90, high ≥70, medium ≥50. **`weighted_contribution` is a percentage summing to ~100, not score-magnitude.**
- `core/resolver.py` — `normalize_identifier`, `resolve_identifier` (exact then pg_trgm fuzzy for person/business), `resolve_identifiers_from_str`, `link_subject_group` (public pairwise `same_owner` helper).
- `core/matcher.py` — `run_cross_bank_matching` for entities with ≥2 `reporting_orgs`; upserts `matches`, emits cross_bank alerts on new/escalated.
- `core/pipeline.py` — `run_str_pipeline`, `run_scan_pipeline` (optional `source_run_id` scopes to upload batch).
- `core/match_dsl.py` — JSON condition tree for custom match definitions; whitelisted fields/ops, max depth 8 / 100 nodes.
- `core/graph/` — `builder.py` (networkx DiGraph), `analyzer.py`, `pathfinder.py`, `export.py`.

**Scan pipeline scope rule:** `scope_org_ids=None` → all banks (regulator); `[uuid]` → that org. Per-account writes (Entity, Match, Alert) attribute to `account.org_id`, not the caller. Threshold `_SCAN_SCORE_THRESHOLD = 50`.

**Modifier conditions:** All 8 rules have full condition + scoring logic. 7 transaction-derived modifiers driven by `account.bank_code` (populated on CSV ingest). 4 graph-lookup modifiers (`proximity_to_flagged ≤ 2`, `involves_multiple_banks`, `circular_flow_detected`, `target_confidence > 0.8`) are wired against the entity graph the pipeline already builds — `_entity_within_hops` (undirected shortest-path), accounts_by_id bank-set, `_entity_in_cycle` (`nx.find_cycle`), and target node `risk_score / 100`. **All four warm up after the first scan** since they need `account.metadata_json["entity_id"]` (assigned on first resolve). `proximity_to_bad` therefore fires from the second scan onward.

**Verification baseline (2026-04-15):** 377 accounts, 547 txns → 10 flagged, 11 alerts (3× rapid_cashout, 6× first_time_high_value, 1× fan_in_burst, 1× cross_bank_match). Divergence without cause → evaluator/scorer regression.

**Match definition execution:** `services/match_definitions.execute_match_definition` validates the DSL, evaluates against every Entity the caller can see, and emits alerts deduped by `(source_id=definition.id, entity_id, status IN open/reviewing/escalated)` so re-execution doesn't double-fire.

## Seed data

**Synthetic DBBL dataset** (`engine/seed/dbbl_synthetic.py` + `load_dbbl_synthetic.py`):
1. `dbbl_synthetic.py` reads curated DBBL PDFs from `F:\New Download\Scammers' Bank statement DBBL` (local-only, never committed), parses via `engine/app/parsers/statement_pdf.py`, sanitises (stable hash-based account numbers + names, scaled amounts, shifted dates), computes `risk_profile`, writes JSON fixtures under `engine/seed/generated/dbbl_synthetic/` (committed).
2. `load_dbbl_synthetic.py::apply_dataset()` idempotently upserts using deterministic UUIDs derived from namespace `8d393384-a67a-4b64-bf0b-7b66b8d5da76`.

**Reference tables (009)**: 197 rows seeded inline — channels, categories, banks+MFS, countries, currencies, agencies. `ON CONFLICT DO NOTHING`.

**Typologies (004)**: 5 Bangladesh-specific.

**Demo bank seed (V2 P2.3)** (`engine/seed/load_demo_bank.py`): per-tenant idempotent loader for new bank workspaces signed up via `/signup/bank`. Each tenant gets ~25 entities (4 cross-bank flagged + 21 single-bank), ~30 internal accounts, ~10k transactions over 180 days (40% NPSB / 25% BEFTN / 15% RTGS / 15% MFS / 5% cash+cheque), 12 alerts (3/5/4 critical/high/medium), 3 STRs at draft/flagged/submitted, 5 cases (2 standard / 1 proposal / 2 RFI), 4 cross-bank Match rows linking to BRAC/City/Islami/Sonali. Per-tenant deterministic UUIDs derived from `org_id` with the shared `NAMESPACE`. Bulk transaction insert via `pg_insert(...).on_conflict_do_nothing()`. After successful apply, sets `settings.demo_seed_pending=false` and records `settings.demo_seed_counts`. Driven by Celery Beat task `app.tasks.demo_seed_tasks.apply_pending` running every 10 min.

**Current prod state (post V2 P2 2026-05-05)**: 7 organizations, 52 entities (28 DBBL + 24 multi-bank), 377 accounts, 547 transactions, 10 STRs, 40 alerts, 1 case, 7 matches (1 pre-existing + 6 multi-bank). No bank tenant has signed up via /signup/bank yet, so the demo bank seed has never fired. Multi-bank seed accounts (64) + transactions (105) + STRs (35) NOT yet applied to prod — committed in seed module, awaiting application.

Regenerate fixtures: `python -m seed.dbbl_synthetic`. Load DBBL: `python -m seed.load_dbbl_synthetic --apply` (or `/admin/synthetic-backfill` as regulator admin). Load multi-bank: `python -m seed.multi_bank_synthetic --apply` (V2 P1.2; deterministic UUIDs share NAMESPACE with DBBL loader). Load demo bank for one tenant: `python -m seed.load_demo_bank --org-id <uuid> --apply` (V2 P2.3); for all pending tenants: `python -m seed.load_demo_bank --apply-pending`.

## Environment variables

Source of truth: `.env.example`.

- **Demo mode**: `KESTREL_ENABLE_DEMO_MODE` + `KESTREL_DEMO_PERSONA` (engine), `NEXT_PUBLIC_ENABLE_DEMO_MODE` + `NEXT_PUBLIC_DEMO_PERSONA` (web).
- **Supabase (web)**: `NEXT_PUBLIC_SUPABASE_URL` + `NEXT_PUBLIC_SUPABASE_ANON_KEY` — if missing, web silently falls back to demo.
- **Supabase (engine)**: `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_ROLE_KEY`. `SUPABASE_JWT_SECRET` enables HS256 (precedence over JWKS).
- **Engine core**: `DATABASE_URL` (`postgresql+asyncpg://`), `REDIS_URL`, `ALLOWED_ORIGINS`.
- **Web → engine proxy**: `ENGINE_URL` (server) / `NEXT_PUBLIC_ENGINE_URL` (client).
- **AI providers**: `OPENAI_API_KEY` + `OPENAI_BASE_URL` + `OPENAI_MODEL`, plus `ANTHROPIC_*` for direct Anthropic. On prod (2026-05-04) the OpenAI adapter is wired to OpenRouter: `OPENAI_API_KEY=sk-or-v1-...`, `OPENAI_BASE_URL=https://openrouter.ai/api/v1`, `OPENAI_MODEL=anthropic/claude-sonnet-4.6`. `ANTHROPIC_*` blank — single model serves all 6 task types via OpenRouter.
- **Bank-direct signup (V2 P2.2)** (web): `ENABLE_BANK_DIRECT_SIGNUP` (default `true`; when `false`, `/signup/bank` returns 404 via `notFound()`). `NEXT_PUBLIC_SITE_URL` (default `https://kestrel-nine.vercel.app`) is the redirect URL on the magic-link invite.
- **Briefing-intake notifications (V2 P2.5)** (web): `RESEND_API_KEY` (auto-provisioned by Vercel Marketplace Resend integration; if missing, the form still succeeds and the row still lands in `access_requests`, the email is just skipped). `BRIEFING_NOTIFY_EMAIL` (default `intake@enso-intelligence.com`). `BRIEFING_FROM_EMAIL` (default `Kestrel <onboarding@resend.dev>`; switch to `Kestrel <noreply@enso-intelligence.com>` once the Resend domain is verified).
- **Hardcoded defaults** not in `.env.example`: `ALGORITHM`, `APP_VERSION`, `ENVIRONMENT`.

## Sovereign Ledger

Institutional-brutalist UI rebrand. **Design direction came from Gemini 3.1** ("national security infrastructure, not SaaS"). Merged `--no-ff` to `main` 2026-04-18 (`92164b1`); preview URL still auto-updates on push: `https://kestrel-git-feature-sovereign-ledger-enso-intelligence.vercel.app`.

**Canonical design doc:** `.claude/skills/kestrel-design/SKILL.md` — read before any UI work.

**Tokens** (scoped under `.platform-surface` in `globals.css`):
- bg `#0F1115` · foreground `#EAE6DA` (bone) · card `#15171C` · border `rgba(234, 230, 218, 0.10)`
- accent + destructive = vermillion `#FF3823` (alarm-only)
- `--radius: 0` · rounded-full pills flattened via global override
- font-sans → IBM Plex Sans · font-mono → IBM Plex Mono (IDs, timestamps, amounts, eyebrows)
- Landing uses parallel `--landing-*` family in same globals.css.

**Patterns:**
- Section frame: `<section className="border border-border">` with `border-b border-border px-6 py-5` header containing `font-mono text-[10px] uppercase tracking-[0.28em] text-muted-foreground` eyebrow prefixed with `<span className="text-accent">┼</span>`. Use `Section` / `Field` / `Meta` helpers where they exist.
- Eyebrow → title → description cadence on every dressed surface.
- Badges/pills inverted-on-active mono strips.
- Errors: `font-mono text-xs uppercase tracking-[0.18em] text-destructive` with `┼ ERROR · {detail}`. Notices: same shape, `text-accent`.
- Three-tone status (muted / foreground / accent) replaces rainbow badge maps.
- Data cells: mono IDs (truncated `··` middle ellipsis), mono tabular-nums amounts, mono uppercase tracking-[0.18em] timestamps.
- Recharts: mono Plex ticks, zero-radius hairline tooltips, grid in 8% bone, monochromatic series.
- React Flow nodes: `borderRadius: 0`, hairline border (vermillion when risk ≥ 90 or alarm), Plex Mono label, bg `#15171C` (alarm-tinted when flagged). Reference: `components/investigate/network-canvas.tsx`, `components/intel/diagram-builder.tsx`.

**KestrelMark** (`web/src/components/common/kestrel-mark.tsx`) is the single source of truth — bone bird + vermillion crosshair on dark, slate bird + bone crosshair on light. Variants: `lockup`/`mark`/`wordmark`. SVG sources next to component. Favicon `web/src/app/icon.svg`, Apple touch icon `web/src/app/apple-icon.tsx`, OG card `web/src/app/opengraph-image.tsx`.

**Phase 6 (polish, non-blocking)**: Lighthouse ≥95 public / ≥90 in-app, a11y sweep, mobile breakpoint pass, refresh `docs/goaml-coverage.md` screenshots, update kestrel-design SKILL.md with final helper-component patterns.

## Cross-bank intelligence (V2 P1)

V2 phase 1 of the world-class build. Three commits on 2026-05-04: `d64049d` (P1.1 dashboard), `6bd2366` (P1.2 multi-bank seed), `dfbfca3` (P1.3 whitepaper).

**Engine** (`engine/app/services/cross_bank.py` + 4 routes under `/intelligence/cross-bank/`):
- `/summary` — top stats (entities flagged across N banks, new this week, high-risk cross-institution count, aggregate exposure, cross-bank alerts count).
- `/matches` — recent cross-bank match clusters with persona-aware anonymisation.
- `/heatmap` — per-bank cross-bank-match counts with severity breakdown.
- `/top-entities` — top entities flagged across institutions by risk × bank-count.

**Persona invariants enforced in the service layer (NOT in the dashboard component):**
- Bank persona NEVER sees other bank names — `_label_orgs_for_user` substitutes `Peer institution 1..N`.
- Bank persona sees `match_key` redacted to last 4 chars via `_anonymize_match_key` (e.g. `····5001`).
- Bank persona only sees match clusters their own `org_id` is part of.
- Regulator persona sees the full picture across the banking system (real bank names, full match keys).

**Web** (`web/src/app/(platform)/intelligence/cross-bank/page.tsx` + `web/src/components/intel/cross-bank-dashboard.tsx`):
Sovereign Ledger styled, hairline section frames, monospace eyebrows, three-tone status, zero radius. 4 sections in order: filter bar (window 7d/30d/90d, severity pills) → 4-tile stats row → heatmap with severity breakdown → recent matches list → top cross-flagged entities. Bank-view footer makes the anonymisation explicit.

**Tests** (`engine/tests/test_cross_bank.py`): 8 pure-helper tests covering persona invariants. Suite went 151 → 159 passing.

**Multi-bank seed** (`engine/seed/multi_bank_synthetic.py` + `multi_bank_to_sql.py`):
Idempotent dataset that brings the prod database to demo-grade for cross-bank scenarios. Topology: 1 marquee 5-bank entity, 2× 3-bank, 3× 2-bank, 18 single-bank. Uses the same `NAMESPACE` UUID5 namespace as the DBBL loader. **Applied to prod 2026-05-04: entities (24) + matches (6) + alerts (17). Accounts (64) + transactions (105) + STRs (35) committed in the seed module but NOT yet applied to prod** — apply via `python -m seed.multi_bank_synthetic --apply` from any env with `DATABASE_URL` set (e.g. `render ssh srv-d7757oidbo4c73e98tlg`).

**Whitepaper** (`docs/cross-bank-intelligence.md`): 2232 words / ~6 pages. Procurement-ready. Every persona-isolation claim is backed by a unit test in `test_cross_bank.py` and an RLS policy verifiable via `pg_policies` on Supabase. Pre-rendered HTML at `docs/cross-bank-intelligence.html` (browser-viewable, Print → PDF works). PDF generation via `python docs/render_pdf.py` from any env with WeasyPrint native deps (Render container has them; local Windows doesn't).

## Bank-direct surface (V2 P2)

V2 phase 2 of the world-class build. Five commits on 2026-05-05: `5932e9c` (P2.1 landing), `98e21ae` (P2.2 signup), `0b15a23` (P2.3 demo seed + Beat), `857f415` (P2.4 isolation verification + migration 013), `166818e` (P2.5 Resend wiring).

**Bank-direct landing** (`web/src/app/(public)/banks/page.tsx` + `web/src/components/banks/banks-*.tsx`): Sovereign Ledger styled, 8 sections — hero with embedded `IntakeForm`, 4-stat ledger, 3-module features (pattern scanner / AI explanation / STR drafting), dedicated cross-bank intelligence section linking to the V2 P1.3 whitepaper, BB Circular 26/2024 callout, three BDT-denominated pricing tiers (Starter Tk 60 lakh / Professional Tk 1.5 crore / Enterprise Tk 4 crore), 4-step operating loop, two-CTA footer (`Provision a workspace` → `/signup/bank`, `File a briefing request` → `#access`). Reuses `PublicHeader`, `PublicFooter`, `IntakeForm`. Static prerendered. The BFIU-facing landing at `/` is untouched.

**Self-serve bank signup** (`web/src/app/(public)/signup/bank/page.tsx` + `web/src/components/banks/bank-signup-form.tsx` + `web/src/app/actions/bank-signup.ts`): server component with `export const dynamic = "force-dynamic"`, `notFound()` when `ENABLE_BANK_DIRECT_SIGNUP=false`. Form fields: bank_name, full_name, role, phone (optional), email, demo_narrative (min 30 chars). Server action: validates input, generates a unique slug (`<slug>-<6-hex>`), inserts an `organizations` row (`org_type='bank'`, `plan='trial'`, `settings.demo_seed_pending=true`, `settings.demo_narrative`, `settings.signup_source='bank-direct'`), invites the user via `auth.admin.inviteUserByEmail` with `raw_user_meta_data` setting `org_id` + `persona='bank_camlco'` + `role='admin'` + `designation` + `phone`. Rolls back the org on invite failure; recognises "already registered" / "already been" and returns a friendly message.

**Demo bank seed** (`engine/seed/load_demo_bank.py` + `engine/app/tasks/demo_seed_tasks.py`): see §"Seed data". Beat-driven every 10 min, picks up tenants flagged via `settings.demo_seed_pending=true`, seeds, flips flag false. New CAMLCO clicks the magic link → lands on `/overview` → sees a populated workspace within ~10 min of signup.

**Persona-isolation verification** (`docs/multi-tenant-isolation-verified.md`): procurement-grade artifact. 8 sections covering the 4-layer isolation architecture (web route gate → engine route gate → service-layer org-type guard → Postgres RLS), verbatim policy citations, file:line citations of regulator-only mutation guards, cross-bank persona invariants, frontend route gates, and live verification on prod 2026-05-05 (RLS simulation as Sonali CAMLCO showing 4/10 STRs visible / 3/49 alerts; cross-bank dashboard rendering peer banks as `PEER INSTITUTION N` with match keys redacted to `····XXXX`; `POST /api/reference-tables` as Sonali → `403 Insufficient role` with captured request_id). Also includes the §7 finding that triggered migration 013.

**Briefing-intake email notifications** (`web/src/app/actions/access.ts`): after every successful `access_requests` insert, send a transactional email via Resend HTTP API. Best-effort: missing `RESEND_API_KEY` → log + early return; non-200 from Resend → log + return; the form-facing response stays `success: true` and the DB row is the source of truth. Reply-to is set to the requester's contact email. Plain-text + HTML bodies, both Sovereign-Ledger flavoured. Configured via Vercel Marketplace Resend integration (writes `RESEND_API_KEY` automatically); destination + From configurable via `BRIEFING_NOTIFY_EMAIL` + `BRIEFING_FROM_EMAIL`.

## Real-time transaction-scoring (V2 P3)

V2 phase 3 of the world-class build. Two commits on 2026-05-05: `1dc575a` (P3.1+P3.2+P3.3 scoring + log + feedback), `67d038b` (P3.4+P3.5 monitoring dashboard + integration docs).

**Engine routes** (`engine/app/routers/realtime.py` mounted at `/transactions`):
- `POST /score` — single-transaction decisioning. Read-only against shared `entities` + `matches` tables; persists `realtime_scoring_log` + `audit_log`. Decision bands: `<30 approve`, `<60 review`, `<80 hold`, `>=80 reject`. Confidence grows with reason count, capped at 0.95. Target p50 < 200 ms / p99 < 500 ms.
- `POST /score/{log_id}/feedback` — bank reports `legitimate` / `fraud` / `unsure`. Foundation for the ML loop in the sovereign-AI track.
- `GET /score/recent?limit=50` — recent stream for the dashboard (bank persona = own org, regulator = cross-system).
- `GET /score/metrics?window_hours=24&top_limit=5` — aggregated decision distribution + latency p50/p95/p99 + cross-bank flag count + top scored last hour.

**Service** (`engine/app/services/realtime_scoring.py`): `score_transaction` composes explainable contributions (`amount_large`/`amount_very_large`/`structuring_suspect`, `channel_cash_like`/`channel_mfs`, `new_account_high_value`, `from_entity_flagged`/`to_entity_flagged`, `from_cross_bank_flagged`/`to_cross_bank_flagged`). All thresholds tuned for BDT-denominated retail+corporate flows. The score is `sum(contributions)` clamped `[0,100]`. Channel allow-list: `NPSB,BEFTN,RTGS,MFS_BKASH,MFS_NAGAD,MFS_ROCKET,CASH,CHEQUE,CARD,WIRE,LC,DRAFT`. `record_feedback` enforces own-org-only updates at the service layer (defense-in-depth on top of the RLS update policy).

**Migration 014** (`014_realtime_scoring_log.sql`): `realtime_scoring_log` (id, org_id, transaction_external_id, request_payload jsonb, score, decision, reasons jsonb, cross_bank_flag, latency_ms, request_id, feedback_received, feedback_outcome, feedback_at, created_at). RLS: own-org-or-regulator on SELECT, own-org only on UPDATE (the feedback endpoint). 4 indexes including PK; CHECK on decision and feedback_outcome.

**Web** (`web/src/app/(platform)/monitoring/realtime/page.tsx` + `web/src/components/monitoring/realtime-dashboard.tsx`): Sovereign Ledger styled. Auto-refreshes every 30s. Sections: filter bar (1h / 24h / 7d), 4-stat tile row (calls in window, latency p50/p95/p99, cross-bank flagged count, reject rate), decision distribution strip (vermillion on REJECT, accent on HOLD, foreground on REVIEW, muted on APPROVE), top-scored last hour, recent stream. Persona-aware footer makes the bank-vs-regulator scope explicit. Two API proxies: `web/src/app/api/realtime/score/recent/route.ts` and `web/src/app/api/realtime/score/metrics/route.ts`.

**Nav**: Operations → "Real-time" pointing at `/monitoring/realtime`. Visible to both bank and regulator personas.

**Tests**: `engine/tests/test_realtime_scoring.py` — 34 pure-helper tests covering decision bands, amount/channel/account-age/entity-risk/cross-bank scoring contributions, percentile interpolation, normalisation. pytest 159 → 193.

**Docs**: `docs/api-integration.md` — full reference for banks' core-banking integration teams. cURL + Python examples, decision bands, reason-code table, error envelope shape, retry semantics, latency expectations.

**Lint regression fixed**: `web/src/components/intel/cross-bank-dashboard.tsx` had a `react-hooks/set-state-in-effect` violation introduced in V2 P1.1 that broke CI for 3 commits. Fixed by lifting `setLoading(true)` + `setError(null)` out of the `useEffect` into the filter click handlers (same pattern used by the new realtime dashboard). CI is now green.

## Sanctions / PEP / adverse-media screening (V2 P4)

V2 phase 4 of the world-class build. Two commits on 2026-05-05: `f566f35` (P4.1+P4.2+P4.3+P4.5 engine + realtime inline + ingestion framework + synthetic seed), pending commit (P4.4 web UI + nav + api-integration docs).

**Engine routes** (`engine/app/routers/screening.py` mounted at `/screening`):
- `POST /entity` — fuzzy-matches a candidate (name + DOB + nationality + NID + passport) against the shared `watchlist_entries` pool. Score weights: name 0.4 / DOB 0.3 / nationality 0.2 / identifier 0.1. Default threshold 0.7. Returns matches sorted descending with `match_reasons` + `matched_entry`.
- `POST /adverse-media` — ComplyAdvantage adapter (`engine/app/services/adverse_media.py`). Returns `provider="stub"` + empty hits when `COMPLYADVANTAGE_API_KEY` is absent.
- `GET /entries?list_source=OFAC&limit=50` — browse the watchlist pool (any authed).
- `POST /entries` — manual upload, regulator-org admins only (BB Domestic uploads).

**Service** (`engine/app/services/screening.py`): `screen_entity` runs read-only against `watchlist_entries`. Uses `func.similarity(WatchlistEntry.primary_name, candidate)` (pg_trgm) with a 0.4 floor + alias fuzzy-match (Jaccard on token sets). Then composes the four weighted contributions into a 0–1 score. Persona-neutral (every authed caller can screen; the watchlist itself is global by design).

**Realtime inline integration** (`engine/app/services/realtime_scoring.py`): when `from_account_metadata` or `to_account_metadata` carries a `name` field, the scorer runs `_screen_party` for each side. A hit at `match_score >= _SANCTIONS_HIT_THRESHOLD = 0.7` adds `_SANCTIONS_HIT_POINTS = 50` via reason class `from_sanctions_hit` / `to_sanctions_hit`. Two hits push the score past the rejection band even when every other signal is benign. `evidence.{from,to}_sanctions_hit` carries `list_source` + `match_score` + `matched_name`.

**Migration 015** (`015_watchlist_entries.sql`): `watchlist_entries` (id, list_source, list_version, entry_type, primary_name, aliases[], date_of_birth, nationality, identifiers jsonb, addresses jsonb, reason, raw_record jsonb, ingested_at, removed_at). Indexes: `gin (primary_name gin_trgm_ops)`, `gin (aliases)`, partial active by source, recency. Unique INDEX (not constraint) on `(list_source, primary_name, list_version, COALESCE(date_of_birth, '1900-01-01'))`. RLS: SELECT-for-any-authed, INSERT/UPDATE/DELETE-for-regulator. Engine ingestion connects as `postgres` (BYPASSRLS) like every other write path.

**Source adapters** (`engine/app/screening/sources/`):
- `ofac.py` — fetches `https://www.treasury.gov/ofac/downloads/sdn.xml`; lxml parser; per-entry aliases / DOB / nationality / identifiers / addresses / program-as-reason.
- `un.py` — fetches `https://scsanctions.un.org/resources/xml/en/consolidated.xml`; parses individual + entity sub-trees separately.
- `uk_ofsi.py` — fetches `https://docs.fcdo.gov.uk/docs/UK-Sanctions-List.csv`; csv.DictReader; column-defensive (different versions ship slight schema variations).
- `eu.py` — placeholder. EU FSF requires credentialed access; live wiring is a Phase 6 task.

**Celery ingestion** (`engine/app/tasks/screening_tasks.py`): `refresh_all` Beat task runs every configured source through `_run_one` and upserts via `pg_insert(...).on_conflict_do_nothing(index_elements=["id"])`. Deterministic UUID5 PKs derived from `(list_source, primary_name, dob)` and the shared `NAMESPACE` make the upsert path simple. **Live ingestion is gated on `KESTREL_WATCHLIST_INGESTION_ENABLED=true`** so external bytes don't pull until the operator turns it on. Beat schedule went 4 → 5 jobs (added `watchlist_refresh_daily` at 02:30 BDT, after the nightly scan).

**Synthetic seed** (`engine/seed/load_watchlist_synthetic.py`): 22 hand-curated entries across OFAC (7) / UN (4) / UK_OFSI (3) / BB_DOMESTIC (4) / PEP (4). Names are deliberately fictional — safe to ship in a public repo. Applied to prod 2026-05-05 via Supabase MCP `execute_sql` (data, not a migration).

**Web** (`web/src/app/(platform)/screen/page.tsx` + `web/src/components/screening/screening-panel.tsx`): Sovereign Ledger styled. Form for name + DOB + nationality + NID + passport + min-score + list filter. Default view shows the most-recent-20 watchlist preview; submitting runs `POST /api/screening/entity` and renders the matches table. Vermillion on score ≥ 0.9 = the highest-confidence hits.

**Tests** (`engine/tests/test_screening.py`): 24 pure-helper tests covering name normalisation, score composition, alias similarity, identifier matching (string + list + nested docs bag), parse_screening_date, and the realtime `_score_sanctions` integration. pytest 193 → 217.

**Live verification:** unauth `POST /screening/entity` returns 401 with the proper error envelope (route mounted with auth dep). `SELECT list_source, count(*) FROM watchlist_entries GROUP BY 1` confirms 22 rows seeded. Auto-deploy on Render + Vercel succeeded.

## KYC / CDD onboarding (V2 P5)

V2 phase 5 of the world-class build. Two commits on 2026-05-05: `74fbbe6` (P5.1+P5.2+P5.4 schema + service + router + Beat task + synthetic seed), pending commit (P5.3 web UI + nav + docs).

**Engine routes** (`engine/app/routers/customers.py` mounted at `/customers`):
- `POST /` — onboard a customer; runs sanctions screening inline on the primary + every beneficial owner; returns the composed decision.
- `GET /?risk_level=high&kyc_status=review&limit=100` — list with filters; bank persona is own-org only, regulator sees all.
- `GET /{id}` — detail with full `screening_results`.
- `PATCH /{id}` — safe-field update (phone / email / address / metadata / beneficial_owners).
- `POST /{id}/review` — CAMLCO review; flips `kyc_status` and stamps `reviewed_at` + `reviewed_by`.
- `POST /{id}/rescreen` — re-run sanctions on demand.

**Service** (`engine/app/services/kyc.py`): `onboard_customer` calls `services.screening.screen_entity` for the primary candidate + each beneficial owner. The composed `risk_score` follows: 0.9+ primary hit ⇒ +95, 0.8+ ⇒ +80, 0.7+ ⇒ +65, below floor ⇒ 0; each beneficial-owner hit adds +10 (capped at +30). Decision bands: `<30 low/approved`, `<60 medium/approved`, `<80 high/review`, `>=80 declined`. **A direct hit at primary score >= 0.9 forces declined regardless of composed score** — onboarding a sanctioned party at any composed score is a regulatory violation.

`update_customer` only touches a `safe_fields` allow-list (phone, email, address, metadata, beneficial_owners) so a PATCH never accidentally rewrites the screening results or the audit-trail timestamps. `review_customer` flips `kyc_status` to one of `approved/declined/review` and stamps `reviewed_at` + `reviewed_by`. `rescreen_customer` re-runs the same path as onboarding but preserves prior manual review decisions unless the new screen forces a decline.

**Migration 016** (`016_customers.sql`): `customers` table with `(org_id, customer_external_id)` unique constraint, RLS own-org-or-regulator on SELECT, own-org INSERT/UPDATE. 5 indexes including a gin_trgm on `full_name` and a partial on `(org_id, last_rescreened_at NULLS FIRST) WHERE kyc_status IN ('approved','review')` for the periodic re-screening Beat task. Also relaxes `alerts.source_type` CHECK to allow the new `kyc_rescreen` value (same drop-and-readd pattern as migration 011).

**Periodic re-screening** (`engine/app/tasks/kyc_tasks.py`): Beat task `kyc_rescreen_active` at 03:00 BDT (after the 02:30 watchlist refresh). Sweeps customers with `kyc_status IN ('approved','review')` whose `last_rescreened_at` is missing or > 7 days old, batched at 500 per run. For each, re-runs `_screen_customer_and_owners`, persists the fresh `screening_results`, and — if the new top primary score `>= 0.9` exceeds the previously-stored top score — emits an `Alert(source_type='kyc_rescreen', severity='high'|'critical')` plus a `Case(variant='escalated', category='kyc')` linked back to the customer. This is the "OFAC just added entry X on Wednesday → existing customer Y now matches" loop. Beat schedule went 5 → 6 jobs.

**Synthetic seed** (`engine/seed/load_customers_synthetic.py`): per-tenant idempotent loader. 25 individuals + 5 businesses, including 2 individuals (Mohammad Karim, Anwar Hossain) whose names match Phase-4 watchlist entries and 1 business (Padma Trading Ltd) whose beneficial owner Tariq Rahman matches a UN entry — so the screening flow returns real "found" results when these customers are screened in the demo. **13 rows applied to Sonali Bank** (`9c222222-…`, the bank_camlco demo persona's tenant) via Supabase MCP `execute_sql`.

**Web** (`web/src/app/(platform)/customers/{page.tsx,new/page.tsx,[id]/page.tsx}` + `web/src/components/customers/{customers-list,customer-onboard-form,customer-detail,shared}.tsx`): three pages — list with filters (kyc_status + risk_level), onboarding form (individual + business with beneficial-owner add/remove), and detail with full screening result tiles, beneficial-owner-by-owner hits, and review actions (Approve / Send to review / Decline / Re-run screening). Sovereign Ledger styled. Vermillion on score ≥ 0.9 = sanctions hit. Three API proxies under `/api/customers/`. Nav entry under Operations, **bank persona only** (regulator doesn't onboard customers — V2 spec).

**Tests** (`engine/tests/test_kyc.py`): 17 pure-helper tests covering decision bands (low/medium/high/declined + direct-hit override), risk-score composition (primary-only / beneficial-owner-only / both), `_matches_to_payload` round-trip, and the Beat task's `_previous_top_primary_score` helper (handles missing / non-dict / non-numeric stored shapes). pytest 217 → 234.

**Live verification:** unauth `POST /customers` returns 401 with proper error envelope (route mounted with auth dep). 13 synthetic customers visible in prod for Sonali Bank. Onboarding form, detail page, review actions, and re-screening all work end-to-end against the live watchlist pool.

## Status + pricing + demo (V2 P6)

V2 phase 6 of the world-class build. Two commits on 2026-05-05: `caf7507` (engine: migrations 017+018 + status service + billing service + Beat tasks + tests), pending commit (web + docs).

**Status surface** (`engine/app/routers/status_public.py` mounted at `/status` with no auth + admin companions at `/admin/status`):
- `GET /status/summary` — public. Per-component current status + 30/90-day uptime % + active incidents.
- `GET /status/incidents` — public. Recent incident feed.
- `GET /status/plans` — public. The three plans for the bank-direct landing.
- `POST /admin/status/incidents` — regulator only. Posts a new incident.
- `POST /admin/status/incidents/{id}/resolve` — regulator only. Closes an incident.
- `GET /admin/status/plan` — authed. Caller's resolved plan + overrides.

**Service** (`engine/app/services/status.py`): `build_status_summary` reads the latest ping per component + computes uptime % from `uptime_pings`. `_overall_status` is worst-of (down > degraded > up; unknown-only is degraded — don't claim up when we don't know). `_uptime_pct` returns 1.0 when there are no pings (degrade gracefully).

**Uptime Beat task** (`engine/app/tasks/status_tasks.py`): `record_uptime_ping` runs every 5 min, calls `services.readiness.build_readiness_report`, and writes one row per component. Collapses `ai:openai` + `ai:anthropic` into a single `ai` component using a worst-of `_is_worse` helper. Failure paths are silenced — a database outage shouldn't make this task itself crash and lose subsequent checks.

**Migration 017** (`017_status.sql`): `uptime_pings` (id bigserial, observed_at, component, status, latency_ms, detail) + `status_incidents` (id uuid, started_at, ended_at, severity, component, summary, message, posted_by). RLS public-read on both; writes regulator-only. 4 indexes.

**Pricing tiers** (`engine/app/services/billing.py`): three plans in code — starter (Tk 60 lakh, 5 seats, 500k transactions/mo, core+cross_bank), professional (Tk 1.5 crore, 15 seats, unlimited, +realtime+sanctions+kyc), enterprise (Tk 4 crore, 50 seats, unlimited, +agentic+priority_support, on_prem_eligible). `resolve_tenant_plan` reads `organizations.plan_id` + `plan_overrides`. `has_feature` allows per-tenant overrides to *enable* a feature but never to *disable* a plan-included one. `require_feature` is a service-layer dependency wrapper that wires into routes — `/transactions/score`, `/screening/entity`, `/screening/adverse-media`, `/customers` (POST) all call it; starter-tier callers receive **402 PAYMENT REQUIRED** with an upgrade message.

**Migration 018** (`018_billing.sql`): adds `plan_id` (CHECK starter/professional/enterprise, default starter), `plan_set_by` (uuid → auth.users), `plan_set_at`, `plan_overrides` (jsonb). Regulator orgs auto-set to enterprise on apply; existing bank tenants bumped to professional via `execute_sql` so the demo flows continue working.

**Demo refresher** (`engine/app/tasks/demo_refresh_tasks.py`): `weekly_demo_refresh` Beat task on Mon 04:00 BDT shifts `transactions.posted_at` and `alerts.created_at` forward by 7 days for any rows older than 7 but newer than 400 days. Idempotent via `organizations.settings.last_demo_refresh_at` on the regulator org — skipped if the last run was within 6 days. **Beat schedule went 6 → 8 jobs**: nightly_scan / daily_digest / weekly_compliance / demo_bank_seed / watchlist_refresh / kyc_rescreen / **uptime_ping_5min** / **weekly_demo_refresh**.

**Web** (`web/src/app/(public)/status/page.tsx` + `web/src/components/status/status-board.tsx`): public status board. Auto-refreshes every 60s. Per-component cards with status tone (vermillion = outage, accent = degraded), 30/90-day uptime %, last-ping relative time, recent incidents with severity tones. SLA footer (99.5% Pro / 99.9% Enterprise). `web/src/app/(public)/demo/page.tsx`: public landing with three persona cards (Bank CAMLCO / BFIU Director / BFIU Analyst) explaining what each persona sees, demo email pointers, sign-in CTA. `web/src/app/(platform)/admin/status/page.tsx`: incident management (regulator+admin only) — post / view / resolve incidents. 3 API proxies.

**Tests** (`engine/tests/test_billing.py` + `test_status_service.py`): 34 new pure-helper tests covering plan resolution, feature flags, override semantics, plan pricing, status worst-of aggregation, ping-status mapping for the Beat task, and AI component collapse. pytest 234 → 268.

**Verification done at end of P6 engine:** Migrations 017 + 018 applied to prod via Supabase MCP. 5 banks bumped to professional, regulator on enterprise, MFS on starter. Engine routes 117 → 123. CI green on `caf7507`. The 402-on-starter behaviour is verified by inspection (regulator + bank both on plans that include the gated features; an MFS tenant on starter would get 402 if it called `/transactions/score`).

## V3 phase 1 — AI outcome logging (shipped 2026-05-05)

V3 phase 1 of `KESTREL-V3-PROMPT.md`. Foundation for the sovereign-AI track: every AI call writes one row to `ai_outcome_log` with the redacted prompt, structured output, latency, token counts, and an optional analyst correction captured later when a CAMLCO edits the AI-drafted output. Two commits on 2026-05-05: `157fa73` (engine), pending (web + UI hooks).

**Engine** (`engine/app/ai/audit.py::record_ai_invocation`): dual-writes — one row to `audit_log` for compliance (existing behaviour, every pre-V3 call site keeps working) + one row to `ai_outcome_log` for the V3 phase 4 fine-tune corpus. Returns the inserted `log_id` (uuid). The `AIOrchestrator.invoke` path now times the provider call with `time.perf_counter()`, extracts optional `prompt_tokens` / `completion_tokens` / `confidence` from `ProviderResponse` (adapters fill in when upstream returns usage), and threads the `outcome_log_id` back through `AIInvocationResult` → `AIInvocationMeta` so UI callers can post a correction later.

**3 new routes** under `/ai/outcomes`:
- `POST /outcomes/{log_id}/correction` — analyst edited the AI output, capture diff + outcome_label.
- `GET /outcomes/dashboard?window_days=30` — per-task accuracy proxy (correction rate), provider distribution, latency, outcome-label histogram.
- `GET /outcomes/recent?limit=50&only_corrected=true` — recent stream for the dashboard.

**Migration 019** (`019_ai_outcome_log.sql`): table + RLS (own-org-or-regulator on SELECT; own-org only on UPDATE for correction capture). 3 indexes including a partial on rows with `analyst_correction IS NOT NULL` so the V3 phase 4 corpus exporter has a fast path.

**Web** (`web/src/app/(platform)/admin/ai-outcomes/page.tsx`): admin/manager/analyst dashboard. 4 stat tiles (invocations / corrections / tasks / providers), per-task accuracy table (vermillion at correction_rate ≥ 30%, accent at ≥ 15%), recent stream with optional only-corrected filter. 3 API proxies. Nav entry under Admin.

**Tests** (`engine/tests/test_ai_outcome.py`): 12 pure-helper tests covering digest determinism, redact-text serialisation (sort_keys + Bangla unicode), outcome view-shape round-trip, has_correction flag. pytest 268 → 280.

**Deferred follow-up** (not blocking P1 close): wire `outcome_log_id` from the AI envelope into the existing AI call sites — STR draft narrative editor (capture diff on edit), alert explanation panel (capture dismiss as `outcome_label='rejected'`), KYC review (capture override as `outcome_label='edited'`). The infrastructure is in place; this is integration touch-up done as the V3 sovereign track's training data accumulates.

## What's next — V3 phases 2-7

V3 phase 1 shipped. Next is **P2 confidence routing** (week 2 of the V3 prompt) — sovereign-first routing pattern in `engine/app/ai/routing.py` with threshold = ∞ initially so every call still routes to Claude. After that: P3 agentic investigations, P4 training pipeline, P5 quality gates, P6 on-prem (conditional), P7 ops maturity.

| V3 phase | Estimate | Strategic unlock |
|---|---|---|
| **P2** Confidence routing | 1 week | Pattern in place; no behavior change yet. Sets up P4 to flip the threshold without a structural rewrite. |
| **P3** Agentic AI investigations | 2-3 weeks | Multi-step investigation agent at `POST /agents/investigate`. Closes the last "Missing" capability from the world-class matrix. |
| **P4** Training pipeline | 2 weeks | LoRA fine-tune harness on Modal/RunPod, sovereign adapter implemented, first cycle run. |
| **P5** Quality gates + gradual rollout | 1 week | Promotion harness, per-task rollout %, automatic rollback Beat task. |
| **P6** On-prem packaging | 4-6 weeks (conditional) | First Tier-3 customer drives this. |
| **P7** Operational maturity | 1-2 weeks (anytime) | Stripe, hard cap enforcement, audit-log retention, latency-regression CI. |

`KESTREL-V3-PROMPT.md` has the canonical task table with full detail.

**Outstanding small-pickups from V2:**
- Set `KESTREL_WATCHLIST_INGESTION_ENABLED=true` on Render to flip daily watchlist ingestion on (still on synthetic seed).
- Provision `COMPLYADVANTAGE_API_KEY` to switch the adverse-media adapter from stub to live.
- EU FSF watchlist credential (1-day wire-up after the credential lands).
- Render Beat deploy hook URL is stale (returns 404). Engine deploys fine via Render's connected-repo path; fix when convenient.
- Apply remaining multi-bank seed chunks (64 accounts + 105 transactions + 35 STRs) via `python -m seed.multi_bank_synthetic --apply`.
- Install Vercel Marketplace Resend integration to flip `RESEND_API_KEY` on (briefing-intake emails currently no-op).

**Outstanding small-pickups:**
- Inside V2 P1: apply the remaining multi-bank-seed chunks (accounts / transactions / STRs) to prod via `python -m seed.multi_bank_synthetic --apply`. The cross-bank dashboard works without these but they'd enrich the entity dossier downstream when bank-persona users click through to a flagged subject.
- Inside V2 P2: install the Vercel Marketplace Resend integration on the kestrel project to flip `RESEND_API_KEY` on (briefing-intake emails currently no-op). Verify `enso-intelligence.com` in Resend (DNS: SPF TXT + DKIM CNAMEs) so From can move from `onboarding@resend.dev` to a Kestrel-branded address.
- The first real signup via `/signup/bank` is also the first live exercise of the demo seed loader, the migration 013 fix, and the V2 P2 isolation guarantees end-to-end.

**Older deferred items still apply:** outbound goAML adapter (`engine/app/adapters/goaml.py` is a stub), demo film production (separate from the procurement whitepaper which is now shipped), `web/src/lib/demo.ts` persona-card fixture cleanup.

## Code conventions

**Python (engine):**
- FastAPI routers in `engine/app/routers/` do only parameter wiring + auth deps + delegation to `engine/app/services/`.
- Services accept `AsyncSession` + keyword-only `user: AuthenticatedUser` and return plain dicts.
- SQLAlchemy 2 async: `select(...)`, `session.execute()`, `.scalars()`. Narrow projections via `select(Model.id, ...)`.
- Helpers `_as_uuid`, `_as_float`, `_iso`, `_safe_int` are duplicated per service file (intentional, low cost).
- Audit logging is manual: insert `AuditLog` row with `action=f"<resource>.<verb>"` and `details=request.model_dump()` before commit.
- All DB-touching code in `engine/app/services/`; routers never execute SQL directly.
- AI provider contracts live in `engine/app/ai/`; nothing else talks to OpenAI/Anthropic.
- Dependency injection via `Annotated[T, Depends(...)]`.
- Test files: `test_<domain>_phase<n>.py` or `test_*_core.py`.

**TypeScript (web):**
- App Router with route groups `(public)`, `(auth)`, `(platform)`.
- Server components call `requireViewer()` / `requireRole(...)` at top; redirect on failure.
- Data fetching: route handlers under `web/src/app/api/**/route.ts` proxy via `proxyEngineRequest`. Components never fetch the engine directly.
- Per-domain normalisers in `web/src/lib/` translate snake_case → camelCase (types in `web/src/types/domain.ts`).
- Client components: `"use client"`, `useState` + `useEffect`, `LoadingState` / `EmptyState` / `ErrorState` commons.
- shadcn-style UI primitives in `web/src/components/ui/` composed by domain components.
- Navigation config-driven via `web/src/components/shell/nav-config.ts` with persona/role filters + optional `aka` (goAML vocabulary) tooltip.
- `PageFrame` is the canonical page wrapper.
- Download endpoints forward raw bytes + preserved `Content-Disposition` — never `NextResponse.json()` a binary.
- No global state library actively used (`zustand` installed but local state + server components cover everything).

## Commands

**Web (`web/`):** `npm install`, `npm run dev` / `build` / `start` / `lint`. Node 22.x.

**Engine (`engine/`):**
- `pip install -e .[dev]`
- `uvicorn app.main:app --reload`
- `celery -A app.tasks.celery_app.celery_app worker --loglevel=INFO`
- `pytest -q` (159 tests)
- `python seed/run.py` — manifest smoke test (CI)
- `python -m seed.dbbl_synthetic` — regenerate JSON fixtures
- `python -m seed.load_dbbl_synthetic [--apply]`

**Import check before pushing**: `python -c "from app.main import app; print(len(app.routes))"`. `py_compile` alone does NOT catch broken imports; Render fails at uvicorn boot. Verify new third-party packages are declared in `pyproject.toml`.

**Database:** apply migrations in order via Supabase SQL editor or Supabase MCP `apply_migration`.

**Deployment:**
- Vercel prod: push `main` touching `web/**` (with `VERCEL_*` secrets).
- Render prod: push `main` touching `engine/**` or `supabase/**` (with `RENDER_*` deploy hooks). Hook ~45–60s; uvicorn startup another ~20s.
- No Makefile, no `justfile`, no local `docker-compose`.

## Known issues

Non-obvious gotchas:

1. **Demo fallback is silent.** `web/src/lib/auth.ts::getCurrentViewer` returns demo viewer when Supabase client is null. Prod has env vars set — only matters if removed.
2. **`detection_runs.status` CHECK** — `pending|processing|completed|failed`. NOT `running` (fix `d55aa90`).
3. **Rule RLS policy chain.** Commits `76b76f8` → `4e1af27` fix admin rule mutations via scoped system session in `services.admin.update_rule_configuration` + `POST /admin/maintenance/rules-policy-fix`. Don't simplify without understanding why direct session failed.
4. **`_load_profile_context` swallows DB errors.** `engine/app/auth.py` catches `Exception` → `None` → falls back to JWT/demo. Broken DB looks like "not provisioned" instead of 500.
5. **Two `supabase` client paths.** `web/src/lib/supabase/` (folder) vs any `supabase.ts` import. Check the folder first.
6. **`proxy.ts` is the Next middleware.** Don't rename — tooling depends on it.
7. **Vercel SSR may 500 during Render redeploy.** Transient; reload after `Application startup complete`.
8. **`weighted_contribution` bug (fix `7aed54f`).** Values above 100 = reintroduced bug.
9. **`py_compile` alone does not catch broken imports.** Run actual `from app.main import app` before pushing. Verify third-party packages declared in `pyproject.toml` (case: `jinja2` transitively local but missing from `pyproject.toml` → Render fresh install failed, fixed `390b2f1`; `lxml` required this for goAML T2).
10. **Error envelope covers Starlette 404s too.** Phase 10 middleware wraps FastAPI `HTTPException`, but Starlette router-level 404s bypass it. Fix `73f09d4` registers separate `StarletteHTTPException` handler. Don't consolidate — Starlette handler catches routes the FastAPI one never sees.
11. **`cases.variant` ≠ `cases.category`.** Migration 007 added `variant` (goAML classification) alongside existing `category` (free-text subject category like `fraud`). `category` already held real prod data — don't conflate them.
12. **`gen_str_ref()` short-code prefix map.** Migration 005 replaced `upper(report_type)` with CASE map (STR/SAR/CTR/TBML/COMP/IER/INT/AMSTR/AMSAR/ESC/ADDL). New `report_type` values need a CASE branch or fall through to long prefixes.
13. **Download proxy routes must forward bytes.** Never `NextResponse.json()` a PDF/XLSX/XML — convert `arrayBuffer()` then `new NextResponse(body, { headers: ... })`. Copy `Content-Disposition` from engine.
14. **`STRDraftUpsert` validator is strict on type-specific fields.** `report_type='ier'` without `ier_direction` + `ier_counterparty_fiu` 422s before router. Supplements need `supplements_report_id`; TBML needs `tbml_counterparty_country`; adverse media needs `media_source`. `POST /str-reports/{id}/supplements` forces both fields server-side.
15. **Observability hook false-positives.** Vercel plugin's `posttooluse-validate` hook fires on every route handler asking for "observability instrumentation." Engine-side structured JSON logs + X-Request-ID already cover every proxied call. Skip these suggestions.
16. **Migration 010 FK gotcha.** `access_requests` references `profiles.id` (the `auth.uid()` FK), NOT `profiles.user_id`. Fixed mid-apply during launch.
17. **Migration 012 + 013 chain.** 012 locked `SET search_path = ''` on 7 SECURITY DEFINER helpers but didn't qualify the relations/sequences inside their bodies — `auth_org_id`, `is_regulator`, `gen_case_ref`, `gen_str_ref`, `gen_dissem_ref` all broke. 013 (2026-05-05) is the hot-fix that schema-qualifies them with `public.profiles`, `public.organizations`, `public.case_ref_seq`, etc. while preserving the `search_path = ''` lock-down. If you ever rewrite one of those functions, keep schema qualifiers in the body or the `search_path = ''` clause will silently break it again. `handle_new_user` was already qualified at 012 time, which is why bank-direct signup (V2 P2.2) wasn't broken even before 013 landed.
