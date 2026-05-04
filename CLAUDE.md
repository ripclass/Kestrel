# Kestrel — Project Intelligence

## What is this

Kestrel is a standalone financial crime intelligence platform for Bangladesh. It sits between commercial banks (and MFS/NBFIs) and the Bangladesh Financial Intelligence Unit (BFIU), providing cross-bank entity intelligence, network analysis, explainable alerts, case management, native STR workflows, and command-level reporting. Positioned as a **complete goAML replacement** — banks can continue filing in goAML XML (import + export round-trip), BFIU analysts see the familiar vocabulary (Catalogue Search, IER, Match Definitions, Disseminations), and the platform adds AI-native intelligence goAML cannot provide. Three personas on one platform: `bfiu_analyst`, `bank_camlco`, `bfiu_director`. The procurement-facing capability map is at `docs/goaml-coverage.md`.

## Current state

> **Prod (2026-05-04):** V2 phase 1 (cross-bank intelligence) shipped to `main` — last commit `dfbfca3`. Live on `kestrel-nine.vercel.app`. AI flipped from heuristic → `anthropic/claude-sonnet-4.6` via OpenRouter (`OPENAI_BASE_URL=https://openrouter.ai/api/v1`). `kestrel-beat` Render service provisioned (`srv-d7sajha8qa3s73e1spv0`) — Beat schedule now actually dispatches.

Five build-out sessions shipped end-to-end:
- **Intelligence-core** (2026-04-15/16): real detection engine (8 YAML rules + evaluator + scorer + resolver + matcher + pipeline), scan upload path, WeasyPrint PDF case pack, SAR/CTR report types, AI alert auto-explanation + Draft STR, DB-backed typologies, CommandView polish, modifier conditions, incremental scan scope, Phase 10 hardening (request IDs + structured JSON logs + standardised error envelope + `docs/RUNBOOK.md`).
- **goAML coverage patch** (2026-04-17): all 13 items from `KESTREL-GOAML-COVERAGE-PROMPT.md`. Migrations 005–009 applied. 11 report-type variants, goAML XML import + export, `/iers` workflow, Additional Information Files, 3-tab New Subjects form, Catalogue tile grid, dissemination ledger, 8-variant case enum with proposal kanban + RFI routing, saved queries + manual diagram builder + match definitions, reference tables (197 seed rows), operational statistics dashboards, scheduled-processes admin surface, XLSX + goAML-XML exports, goAML vocabulary tooltips, `docs/goaml-coverage.md`.
- **Sovereign Ledger rebrand** (2026-04-18): institutional-brutalist UI direction merged. See §"Sovereign Ledger".
- **Post-rebrand sweep** (2026-04-19): graph-lookup modifiers wired (`a55d65d`), Celery Beat schedule wired (`b561949`), orphaned alerter cleanup (`ee16cb3`), JSON-DSL executor for match_definitions (`3ca6528`), a11y focus indicator + reduced-motion (`56bd851`), mobile nav drawer (`f764cfb`), a11y skip-link (`c1edceb`), AI red-team harness (`d122e7d`).
- **V2 phase 1: cross-bank intelligence** (2026-05-04): cross-bank dashboard with persona-aware anonymisation (`d64049d`), multi-bank synthetic seed module (`6bd2366`), procurement whitepaper (`dfbfca3`). See §"Cross-bank intelligence" below.

**Aggregate prod state:**
- 103 engine routes across 19 routers (4 new under `/intelligence/cross-bank/` from V2 P1.1). 159/159 pytest. `GET /ready` on `https://kestrel-engine.onrender.com` shows auth/db/redis/storage/worker=ok; `ai:openai = skipped` with model `anthropic/claude-sonnet-4.6` (configured + reachability probe disabled).
- Migrations 001–012 applied. 012 (`advisor_fixes`) locks `search_path = ''` on 7 SECURITY DEFINER helpers. Migrations 001 + 002 retroactively recorded in `supabase_migrations.schema_migrations` after the audit found them missing.
- Prod data (post V2 phase 1): 197 reference_tables, 5 typologies, **52 entities** (28 pre-V2 + 24 multi-bank seed), 377 accounts, 547 transactions, **10 STRs** (multi-bank seed STRs not yet on prod — see §"Cross-bank intelligence"), **40 alerts** (22 pre-V2 + 17 V2 cross-bank + 1 dedupe overlap), 1 case, **7 matches** (1 pre-existing DBBL + 6 V2 cross-bank).
- All 40 `(platform)` pages live (39 pre-V2 + 1 cross-bank dashboard added by P1.1) with real DB-backed data.
- All Render services running: engine, worker, **beat** (provisioned 2026-05-04 — was missing during the audit; Beat schedule was dispatching to nothing for ~15 days until that fix).

What is scaffolded but NOT wired the way the code implies:
- **Inline pipelines.** Every on-demand path (STR submit, ad-hoc scan, scan upload, XML import, match execution) runs inline in the FastAPI request path. Celery worker now also runs the three scheduled jobs since Beat is alive. On-demand execution is intentionally synchronous.
- **goAML *outbound* adapter is a stub.** `engine/app/adapters/goaml.py` exists; machine-to-machine sync into goAML's central server is not implemented. Distinct from the file-based XML import/export.

What V2 ships next (not in main yet — see `KESTREL-WORLD-CLASS-BUILD-V2.md` and `KESTREL-RESUME-V2.md`):
- **Phase 2** Bank-direct surface (landing + signup + bank-tenant demo seed + persona-isolation verification + request-demo wiring).
- **Phase 3** Real-time transaction-scoring API (sub-500ms decisioning).
- **Phase 4** Sanctions / PEP / adverse-media screening (OFAC/EU/UN/UK + adverse-media adapter).
- **Phase 5** KYC / CDD module (greenfield).
- **Phase 6** Public status page + pricing-tier enforcement + demo-flow polish.

## Architecture

### Stack
- **Frontend**: Next.js 16.2.2 App Router, React 19.2.4, TypeScript 5, Tailwind v4, shadcn-style UI, `@xyflow/react` (network graphs), `recharts`, `zustand`, `zod`, `@tanstack/react-table`, `date-fns`. Node pinned to 22.x.
- **Backend**: Python `>=3.12` (pinned 3.12.8 via `engine/.python-version`), FastAPI `>=0.115`, SQLAlchemy 2 async + asyncpg, Pydantic v2, `python-jose`, `networkx`, `celery[redis]`, `PyYAML`, `pdfplumber`, `pandas`, `openpyxl`, `weasyprint`, `lxml`, `jinja2`, `httpx`. Build backend: `hatchling`.
- **Database**: Supabase Postgres. Schema source of truth: `supabase/migrations/001_schema.sql` → `012_*.sql`.
- **Auth**: Supabase Auth. Engine validates two ways: `SUPABASE_JWT_SECRET` (HS256, preferred) or JWKS at `{SUPABASE_URL}/auth/v1/.well-known/jwks.json` (10-min cache). See `engine/app/auth.py`.
- **Storage**: Supabase Storage, buckets `kestrel-uploads` + `kestrel-exports` (configurable via `STORAGE_BUCKET_*`). Scan uploads write raw CSV/XLSX to `kestrel-uploads`; PDF/XLSX/XML exports stream directly. Readiness probe verifies both buckets.
- **Cache/Queue**: Redis on Render. Celery app `kestrel` at `app.tasks.celery_app.celery_app`. Tasks: `worker.ping`, `app.tasks.scan_tasks.run_all_orgs`, `app.tasks.str_tasks.daily_digest`, `app.tasks.export_tasks.weekly_compliance_report`. Beat at 02:00 / 06:30 / Mon 05:00 Asia/Dhaka.
- **AI**: Provider abstraction in `engine/app/ai/` — OpenAI / Anthropic adapters + `HeuristicProvider` fallback. Task routing, prompt registry, redaction, invocation audit, red-team harness. **Prod runs `anthropic/claude-sonnet-4.6` via OpenRouter through the OpenAI-compatible adapter** (`OPENAI_API_KEY=sk-or-v1-...`, `OPENAI_BASE_URL=https://openrouter.ai/api/v1`, `OPENAI_MODEL=anthropic/claude-sonnet-4.6`). `ANTHROPIC_*` left blank — task routes that prefer Anthropic provider fall through to the OpenAI adapter (which is the OpenRouter→Claude pipe).

### Deployment
- `web/` → Vercel via `deploy-web-production.yml` (prebuilt deploy; gated on `VERCEL_TOKEN` / `VERCEL_ORG_ID` / `VERCEL_PROJECT_ID`).
- `engine/` → Render. `engine/render.yaml` declares 3 services: `kestrel-engine` (FastAPI), `kestrel-worker` (Celery), `kestrel-beat`. Deploy via per-service hooks: `RENDER_ENGINE_DEPLOY_HOOK_URL`, `RENDER_WORKER_DEPLOY_HOOK_URL`, `RENDER_BEAT_DEPLOY_HOOK_URL`. Each gated independently.
- DB → Supabase project `bmlyqlkzeuoglyvfythg`. Connection via `DATABASE_URL` (`postgresql+asyncpg://...`) + `SUPABASE_*` envs.
- **CI**: `.github/workflows/ci.yml` (web lint+build, engine pip+pytest+seed smoke), `deploy-web-production.yml`, `deploy-engine-production.yml`, `vercel-prebuilt-check.yml`.

### Key directories
- `web/src/app/(public)/` — landing + pricing.
- `web/src/app/(auth)/` — login, register, forgot-password.
- `web/src/app/(platform)/` — 40 authenticated pages (39 pre-V2 + `/intelligence/cross-bank` from P1.1).
- `web/src/app/api/` — Next route handlers proxying engine via `lib/engine-server.ts`. Download endpoints forward raw bytes with preserved `Content-Disposition`.
- `web/src/components/` — `shell/`, `common/`, plus per-domain folders.
- `web/src/lib/` — Supabase clients, `auth.ts`, `engine-server.ts`, per-domain normalizers, `demo.ts`.
- `engine/app/routers/` — 19 files, one per domain.
- `engine/app/services/` — 28 files, all DB-backed; routers never execute SQL directly. (`cross_bank.py` added in V2 P1.1.)
- `engine/app/models/` — 21 SQLAlchemy models.
- `engine/app/core/` — `detection/` (rules YAML + loader/evaluator/scorer), `resolver.py`, `matcher.py`, `pipeline.py`, `match_dsl.py`, `graph/`.
- `engine/app/parsers/` — `csv.py`, `xlsx.py`, `statement_pdf.py`, `goaml_xml.py` (lxml-based, permissive).
- `engine/app/ai/` — provider abstraction + redaction + audit + redteam.
- `engine/seed/` — synthetic data generators (`dbbl_synthetic.py` + `load_dbbl_synthetic.py` for the original DBBL fixture; `multi_bank_synthetic.py` + `multi_bank_to_sql.py` from V2 P1.2 for cross-bank topology across BRAC / City / Islami / Sonali).
- `supabase/migrations/` — 11 files.
- `docs/` — `production-plan.md`, `goaml-coverage.md` (procurement), `RUNBOOK.md`, `production-audit-2026-04.md` (engineering ground-truth baseline), `cross-bank-intelligence.md` + `.html` (V2 P1.3 procurement whitepaper), `render_pdf.py` (markdown → HTML/PDF for whitepapers).

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

**Current prod state (post V2 P1.2 partial application 2026-05-04)**: 7 organizations, 52 entities (28 DBBL + 24 multi-bank), 377 accounts, 547 transactions, 10 STRs, 40 alerts, 1 case, 7 matches (1 pre-existing + 6 multi-bank). Multi-bank seed accounts (64) + transactions (105) + STRs (35) NOT yet applied to prod — committed in seed module, awaiting application.

Regenerate fixtures: `python -m seed.dbbl_synthetic`. Load DBBL: `python -m seed.load_dbbl_synthetic --apply` (or `/admin/synthetic-backfill` as regulator admin). Load multi-bank: `python -m seed.multi_bank_synthetic --apply` (V2 P1.2; deterministic UUIDs share NAMESPACE with DBBL loader).

## Environment variables

Source of truth: `.env.example`.

- **Demo mode**: `KESTREL_ENABLE_DEMO_MODE` + `KESTREL_DEMO_PERSONA` (engine), `NEXT_PUBLIC_ENABLE_DEMO_MODE` + `NEXT_PUBLIC_DEMO_PERSONA` (web).
- **Supabase (web)**: `NEXT_PUBLIC_SUPABASE_URL` + `NEXT_PUBLIC_SUPABASE_ANON_KEY` — if missing, web silently falls back to demo.
- **Supabase (engine)**: `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_ROLE_KEY`. `SUPABASE_JWT_SECRET` enables HS256 (precedence over JWKS).
- **Engine core**: `DATABASE_URL` (`postgresql+asyncpg://`), `REDIS_URL`, `ALLOWED_ORIGINS`.
- **Web → engine proxy**: `ENGINE_URL` (server) / `NEXT_PUBLIC_ENGINE_URL` (client).
- **AI providers**: `OPENAI_API_KEY` + `OPENAI_BASE_URL` + `OPENAI_MODEL`, plus `ANTHROPIC_*` for direct Anthropic. On prod (2026-05-04) the OpenAI adapter is wired to OpenRouter: `OPENAI_API_KEY=sk-or-v1-...`, `OPENAI_BASE_URL=https://openrouter.ai/api/v1`, `OPENAI_MODEL=anthropic/claude-sonnet-4.6`. `ANTHROPIC_*` blank — single model serves all 6 task types via OpenRouter.
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

## What to work on next

V2 phase 1 (cross-bank intelligence) shipped. Phases 2–6 still pending. Continuity prompt: **`KESTREL-RESUME-V2.md`** (rooted in `KESTREL-WORLD-CLASS-BUILD-V2.md`).

| Phase | Estimate | Unlock |
|---|---|---|
| **P2** Bank-direct surface (landing/signup/demo seed/persona verification/request-demo wiring) | 4–5 days | Banks can self-serve a demo without BFIU being involved at all. The biggest go-to-market unlock. |
| **P3** Real-time scoring API | 5–6 days | The biggest enterprise capability gap. Sub-500ms decisioning with explainable reasons. |
| **P4** Sanctions/PEP/adverse-media screening | 5–6 days | Closes the second-biggest capability gap. OFAC/EU/UN/UK ingestion + screening API + UI. |
| **P5** KYC/CDD module | 5 days | Greenfield. Closes the third gap. |
| **P6** Status page + pricing tiers + demo polish | 3–4 days | Credibility layer. |

**Outstanding small-pickups inside Phase 1**: apply the remaining multi-bank-seed chunks (accounts/transactions/STRs) to prod via `python -m seed.multi_bank_synthetic --apply`. The cross-bank dashboard works without these (matches + entities are enough), but they'd enrich the entity dossier downstream when bank-persona users click through to a flagged subject.

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
- `pytest -q` (95 tests)
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
