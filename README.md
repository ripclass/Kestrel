# Kestrel

A national financial-crime intelligence platform for Bangladesh — built so investigators, bank compliance officers, and BFIU command can work from one shared picture of cross-bank suspicious activity.

> **Live deployment**: published from `main` via the GitHub Actions workflows in `.github/workflows/`. The production URL is configured per environment in Vercel and Render and is not committed to the repo. See `docs/production-plan.md` for environment status.

## What is Kestrel

Bangladesh's existing AML reporting pipeline is built around goAML, which is a filing cabinet — every bank submits STRs into it, but no analyst has a useful surface for connecting reports across banks, tracing money flows, or seeing the same suspect appear in three institutions at once.

Kestrel is the detective layer that sits on top. Banks and MFS providers feed transaction data and STRs in; the BFIU sees a unified intelligence picture across every reporting institution; commercial bank CAMLCOs see the same picture limited to their own perimeter. The same product changes shape by persona: a BFIU analyst sees an alert-and-investigation workspace, a bank compliance officer sees their own posture overlaid with peer-network intelligence, and a BFIU director sees national threat trends, lagging-bank scorecards, and command-level reporting.

Kestrel is built as a standalone product. It can interoperate with goAML via an optional adapter, but it does not depend on goAML for any core workflow.

> **goAML coverage**: for a full feature-by-feature map of Kestrel to goAML — every screen, every workflow, every deliberate exclusion with its rationale — see [`docs/goaml-coverage.md`](docs/goaml-coverage.md). This is the procurement-facing answer to "can Kestrel replace goAML for BFIU?"

## Core capabilities

All items below are live on prod, DB-backed, and cross-mapped to goAML in [`docs/goaml-coverage.md`](docs/goaml-coverage.md).

**Report intake and lifecycle**
- **11 report types** — STR, SAR, CTR, TBML, Complaint, IER, Internal, Adverse Media-STR, Adverse Media-SAR, FIU Escalated, Additional Information File. One lifecycle (draft → submitted → under_review → flagged → confirmed / dismissed), type-specific columns (IER direction + counterparty FIU, TBML LC + HS code + invoice vs declared, adverse-media provenance, supplements link).
- **goAML XML import** — `POST /str-reports/import-xml` accepts the XML banks already emit. Parses header + transactions + subjects, maps submission_code → report_type, ingests transactions tagged with the import batch's `run_id`, resolves every subject into the shared entity pool.
- **goAML XML export** — `GET /str-reports/{id}/export.xml` emits a Kestrel report back in goAML format for peer-FIU handoff or legacy-system interop.
- **AI-assisted enrichment** — "Draft STR from alert" button generates a narrative from alert context; entity extraction auto-populates subjects; narrative drafting + typology suggestion on submit.
- **Additional Information File workflow** — "Supplement this report" action on any STR opens a modal, creates a linked supplement, and shows a "Supplements" section on the parent listing all children.

**Investigation**
- **Universal omnisearch** — find any account, phone, wallet, NID, name, or business across every reporting institution from one search box. Powered by `pg_trgm` fuzzy matching.
- **Entity dossier** — risk score, severity, reporting history, linked alerts + cases, connected entities, two-hop network graph, timeline.
- **Network analysis** — interactive directed graph with amount-weighted edges, beneficiary / wallet / device / phone relationships, suspicious-path counting.
- **Manual diagram builder** — React Flow canvas for case narrative diagrams at `/investigate/diagram`. Save to case or STR as evidence.
- **Saved queries (Profiles)** — per-user + org-shared reusable filters at `/intelligence/saved-queries`.
- **Cross-bank match clusters** — when the same identifier appears across institutions it surfaces as a shared-intelligence cluster with an exposure total.
- **8 pre-built pattern detection rules** — rapid cashout, fan-in / fan-out burst, structuring, layering, first-time high value, dormant spike, proximity to flagged.
- **AI alert explainability** — every alert auto-fetches an AI-generated "why this fired" panel on open. Reasons list carries rule code, score, evidence JSON, recommended action.
- **Catalogue tile grid** at `/investigate/catalogue` — 12 labelled entry points preserving the goAML Catalogue Search vocabulary (Account / Person / Entity / Address / Text / Quick Finder / Transaction / Report / Intelligence Report / Templates / Journal / Dissemination Lookup).

**Case management**
- **8 case variants** — standard, proposal, RFI, operation, project, FIU escalated, complaint, adverse media. Filter pills on the case board drop the view to any variant.
- **Proposals kanban** — pending / approved / rejected columns; manager+ decides via the proposal panel on the case workspace.
- **RFI routing** — analyst-to-analyst requests with `requested_by` + `requested_from` tracking.
- **PDF case pack export** — WeasyPrint-rendered pack at `/cases/{id}/export.pdf` with "Confidential — BFIU" watermark.

**Regulatory cooperation**
- **Information Exchange Request workflow** — dedicated `/iers` surface with Inbound / Outbound tabs, Egmont reference, counterparty FIU, deadline, respond, close.
- **Dissemination tracking** — first-class `disseminations` ledger with DISS-YYMM-##### refs. "Disseminate" action button drops into Alert, Case, Entity dossier, and STR workspaces; emits an audit log entry on every handoff.

**Operational dashboards**
- **Persona-aware command view** — three overview surfaces (director / CAMLCO / analyst) computed from the same intelligence engine.
- **Compliance scorecard** — submission timeliness, alert conversion, peer-network coverage scored per institution.
- **National threat dashboard** — channel-level threat map (RTGS, NPSB, BEFTN, MFS, Cash, Card), trend series, exposure aggregates.
- **Operational statistics** at `/reports/statistics` — Recharts dashboards: reports by type by month, reports by org, CTR volume, disseminations by recipient, case outcomes, avg time-to-review.
- **Pattern scanning with file upload** — `/scan` accepts CSV/XLSX uploads, parses, persists transactions tagged with the run id, and runs the detection pipeline scoped to the upload.
- **Scheduled processes** read-only status page at `/admin/schedules` — declared jobs + live Celery worker ping.

**Administration**
- **Reference tables** at `/admin/reference-tables` — 7 lookup-master tabs (banks + MFS, channels, categories, countries, currencies, agencies, branches). Seeded day-one with 197 rows; regulator admin can extend.
- **Match definitions** at `/admin/match-definitions` — admin-configurable custom match rules alongside the 8 system rules.
- **Rule catalog, team management, API keys** — role-gated admin surfaces.
- **Synthetic regulator backfill** — loads a sanitised synthetic dataset derived from real DBBL bank statements for demo/evaluation.
- **Audit log with X-Request-ID tracing** — every service-layer mutation writes a row; structured JSON logs thread `X-Request-ID` through the engine for incident reconstruction.
- **Readiness probe** at `GET /ready` — covers auth + database + Redis + storage buckets + Celery worker + AI providers. The public landing page reads this live.
- **Incident runbook** at [`docs/RUNBOOK.md`](docs/RUNBOOK.md) — 9 playbooks covering engine 5xx, database connection loss, Celery drop-out, AI provider failure, and the X-Request-ID trace recipe.

**AI abstraction** — internal provider layer (OpenAI / Anthropic / heuristic fallback) with redaction-by-default, prompt registry, invocation audit, and evaluation harness. Prod currently runs on heuristic fallback; set `OPENAI_API_KEY` or `ANTHROPIC_API_KEY` on Render to flip provider routing live.

## Architecture

Kestrel is three deployable units sharing one Postgres schema and one auth model.

```
┌─────────────────────┐         ┌──────────────────────────┐
│  web (Next.js 16)   │  HTTPS  │  engine (FastAPI 0.115)  │
│  Vercel             │ ──────▶ │  Render web + worker     │
└──────────┬──────────┘         └────────────┬─────────────┘
           │                                  │
           │            Supabase Auth         │
           ├──────────────────────────────────┤
           │                                  │
           ▼                                  ▼
   ┌──────────────────────────────────────────────────┐
   │  Supabase Postgres + Storage + Auth (JWKS/HS256) │
   │  Redis (Render) for Celery broker/backend        │
   └──────────────────────────────────────────────────┘
```

The web app proxies every data call through `/api/*` route handlers that forward to the engine with the user's Supabase access token. The engine validates the token, resolves the user's organization/role/persona, and returns RLS-respecting responses. Postgres RLS policies enforce isolation: banks see their own data, regulators see everything, and shared intelligence tables (`entities`, `connections`, `matches`) are visible to every authenticated user.

Architectural roadmap and phased plan: [`docs/production-plan.md`](docs/production-plan.md).

## Stack

| Component | Technology | Deployment |
|---|---|---|
| Web app | Next.js 16.2.2 (App Router), React 19.2.4, TypeScript 5, Tailwind v4, `@xyflow/react` (graphs + manual diagram builder), recharts (statistics dashboards), zustand, zod, `@tanstack/react-table`, date-fns | Vercel |
| API | FastAPI ≥0.115, SQLAlchemy 2 async, asyncpg, pydantic-settings, python-jose, networkx, httpx, **lxml** (goAML XML import), **jinja2** (PDF templates), **openpyxl** (XLSX export), **weasyprint** (PDF case pack), pdfplumber, pandas | Render web service (99 routes) |
| Worker | Celery 5.5 + Redis — currently one `worker.ping` task; pipelines run inline in the request path | Render worker service |
| Database | Postgres 15 with RLS, pgcrypto, pg_trgm — migrations 001–009 | Supabase |
| Auth | Supabase Auth (JWKS or HS256) | Supabase |
| File storage | `kestrel-uploads` (scan upload raw bytes), `kestrel-exports` (reserved) | Supabase Storage |
| Cache / queue | Redis | Render |
| AI providers | OpenAI + Anthropic via internal abstraction with heuristic fallback (currently active on prod — provider keys unset) | Backend-only |
| Runtime pins | Node `22.x` (`web/package.json`), Python `3.12.8` (`engine/.python-version`) | — |

## Local development

Prerequisites: Node 22.x, Python 3.12.8, a Supabase project, a Postgres URL reachable from your machine, and (optionally) Redis.

```bash
git clone <repo-url>
cd Kestrel

# 1. Environment
cp .env.example .env
# Fill in NEXT_PUBLIC_SUPABASE_URL, NEXT_PUBLIC_SUPABASE_ANON_KEY, SUPABASE_SERVICE_ROLE_KEY,
# SUPABASE_JWT_SECRET (or rely on JWKS via SUPABASE_URL), DATABASE_URL, REDIS_URL,
# and optionally OPENAI_API_KEY / ANTHROPIC_API_KEY.

# 2. Database
# Apply all 9 migrations in order via Supabase SQL editor or the Supabase MCP:
#   supabase/migrations/001_schema.sql               (core tables + RLS + triggers)
#   supabase/migrations/002_rules_insert_policy.sql  (RLS fix for system rules)
#   supabase/migrations/003_report_types.sql         (report_type column + cash_transaction_reports)
#   supabase/migrations/004_typologies.sql           (DB-backed typologies library, 5 seed rows)
#   supabase/migrations/005_report_types_expanded.sql (11 report variants + ier/tbml/media/supplements columns)
#   supabase/migrations/006_disseminations.sql       (dissemination ledger + DISS-ref trigger)
#   supabase/migrations/007_case_variants.sql        (cases.variant + proposal decision + RFI routing)
#   supabase/migrations/008_intel_tables.sql         (saved_queries, diagrams, match_definitions, match_executions)
#   supabase/migrations/009_reference_tables.sql     (lookup-master table + 197 seed rows)

# 3. Engine
cd engine
python -m pip install --upgrade pip
python -m pip install -e .[dev]
uvicorn app.main:app --reload --port 8000
# In a second terminal, run the worker (optional but the readiness probe will fail without it):
celery -A app.tasks.celery_app.celery_app worker --loglevel=INFO

# 4. Web
cd ../web
npm install
npm run dev
# Visit http://localhost:3000
```

To populate the database with a sanitized synthetic dataset for demoing the platform end-to-end:

```bash
cd engine
python -m seed.load_dbbl_synthetic            # prints the load plan
python -m seed.load_dbbl_synthetic --apply    # idempotently writes to DATABASE_URL
```

Or, after starting the engine, sign in as a regulator admin and use the **Synthetic backfill** card on `/admin`.

To regenerate the synthetic JSON fixtures from local DBBL PDFs (the source files are not committed to the repo):

```bash
cd engine
python -m seed.dbbl_synthetic
```

Demo mode: when `KESTREL_ENABLE_DEMO_MODE=true` (or no Supabase auth env is configured at all), the engine and web app fall back to a synthesized persona from `KESTREL_DEMO_PERSONA` ∈ `{bfiu_analyst, bank_camlco, bfiu_director}`. Demo mode is for local exploration and demos only — never enable it in production.

## Deployment

Three managed targets, all wired through GitHub Actions:

- **Web → Vercel**. `.github/workflows/deploy-web-production.yml` runs `vercel pull` + `vercel build --prod` + `vercel deploy --prebuilt --prod` on pushes to `main` that touch `web/**`. Requires repo secrets `VERCEL_TOKEN`, `VERCEL_ORG_ID`, `VERCEL_PROJECT_ID`. If any are missing the workflow skips cleanly and writes an explanation to the run summary.
- **Engine + worker → Render**. `engine/render.yaml` declares two services — `kestrel-engine` (FastAPI) and `kestrel-worker` (Celery). `.github/workflows/deploy-engine-production.yml` triggers Render deploy hooks (`RENDER_ENGINE_DEPLOY_HOOK_URL`, `RENDER_WORKER_DEPLOY_HOOK_URL`) on pushes that touch `engine/**` or `supabase/**`.
- **Database → Supabase**. Apply all 9 migrations (`001_schema.sql` → `009_reference_tables.sql`) against the target project. Auth, storage buckets, and JWT signing keys are configured in the Supabase dashboard. Connection details live in environment variables on the engine.

For production operations, see [`docs/RUNBOOK.md`](docs/RUNBOOK.md) — 9 incident playbooks including how to trace a single request via `X-Request-ID`.

CI on every PR and every push to `main` runs `.github/workflows/ci.yml`: web lint+build with Node 22, engine pytest + bytecode compile + seed manifest smoke test on Python 3.12.

The public landing page reads the engine's `/ready` endpoint live, so deployment drift (broken auth config, missing storage buckets, unreachable Redis, unconfigured AI providers) is visible without signing in.

## Project structure

```
kestrel/
├── web/                          Next.js 16 App Router frontend (Vercel)
│   ├── src/app/(public)/         Landing, pricing
│   ├── src/app/(auth)/           Sign in, register, forgot password
│   ├── src/app/(platform)/       39 authenticated pages: overview,
│   │                             investigate (+ catalogue + diagram),
│   │                             intelligence (+ new subject + disseminations
│   │                             + saved queries), alerts, cases, strs,
│   │                             iers, scan, reports (+ statistics),
│   │                             admin (+ match-definitions + reference-tables
│   │                             + schedules)
│   ├── src/app/api/              Next route handlers that proxy to the engine
│   ├── src/components/           Domain components + UI primitives
│   ├── src/lib/                  Supabase clients, engine proxy, normalizers
│   └── proxy.ts                  Supabase session middleware
│
├── engine/                       FastAPI intelligence engine (Render) — 99 routes
│   ├── app/main.py               Router registration (19 routers)
│   ├── app/auth.py               Supabase JWT validation (JWKS + HS256)
│   ├── app/config.py             Pydantic settings
│   ├── app/observability.py      RequestIDMiddleware + structured JSON logs
│   ├── app/routers/              One file per domain (19 files)
│   ├── app/services/             Real DB-backed business logic (27 files)
│   ├── app/models/               SQLAlchemy models (21 files, aligned with
│   │                             migrations 001–009)
│   ├── app/schemas/              Pydantic request/response models per domain
│   ├── app/parsers/              CSV / XLSX / PDF statement + goAML XML parser
│   ├── app/core/                 Detection engine (8 rules + evaluator +
│   │                             scorer + resolver + matcher + pipeline +
│   │                             graph utilities)
│   ├── app/ai/                   Internal AI provider abstraction, prompts,
│   │                             routing, redaction, audit, evaluations
│   ├── app/tasks/                Celery app + (empty) task modules
│   ├── seed/                     Synthetic data generators + DBBL loader
│   ├── tests/                    pytest suites (95 tests)
│   └── render.yaml               Render service declarations
│
├── supabase/migrations/          9 migrations: 001_schema → 009_reference_tables
├── docs/production-plan.md       Phased roadmap and locked decisions
├── docs/goaml-coverage.md        Procurement-facing goAML-to-Kestrel map
├── docs/RUNBOOK.md               Incident playbooks (9 scenarios)
├── .github/workflows/            CI + Vercel + Render deployment
├── .env.example                  All environment variables
├── CLAUDE.md                     Project intelligence for Claude Code sessions
└── README.md                     This file
```

## Production roadmap

All 10 items from the intelligence-core spec and all 13 items from the goAML coverage patch are shipped and live-verified on prod. For the current "what's next" list — landing-page hero rewrite, demo film, scheduled rule execution, remaining graph-lookup modifiers, rule expression DSL, outbound goAML adapter, AI red-team harness — read [`CLAUDE.md`](CLAUDE.md). For the original phased plan see [`docs/production-plan.md`](docs/production-plan.md). For the procurement-facing capability map see [`docs/goaml-coverage.md`](docs/goaml-coverage.md).

## License

No license file is currently included in this repository. All rights reserved by the project owners until a license is published.
