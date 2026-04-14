# Kestrel

A national financial-crime intelligence platform for Bangladesh — built so investigators, bank compliance officers, and BFIU command can work from one shared picture of cross-bank suspicious activity.

> **Live deployment**: published from `main` via the GitHub Actions workflows in `.github/workflows/`. The production URL is configured per environment in Vercel and Render and is not committed to the repo. See `docs/production-plan.md` for environment status.

## What is Kestrel

Bangladesh's existing AML reporting pipeline is built around goAML, which is a filing cabinet — every bank submits STRs into it, but no analyst has a useful surface for connecting reports across banks, tracing money flows, or seeing the same suspect appear in three institutions at once.

Kestrel is the detective layer that sits on top. Banks and MFS providers feed transaction data and STRs in; the BFIU sees a unified intelligence picture across every reporting institution; commercial bank CAMLCOs see the same picture limited to their own perimeter. The same product changes shape by persona: a BFIU analyst sees an alert-and-investigation workspace, a bank compliance officer sees their own posture overlaid with peer-network intelligence, and a BFIU director sees national threat trends, lagging-bank scorecards, and command-level reporting.

Kestrel is built as a standalone product. It can interoperate with goAML via an optional adapter, but it does not depend on goAML for any core workflow.

## Core capabilities

- **Universal entity search** — find any account, phone, wallet, NID, name, or business across every reporting institution from one search box. *(live)*
- **Entity dossier** — risk score, severity, reporting history, linked alerts, linked cases, connected entities, two-hop network graph, and timeline for any subject. *(live)*
- **Network analysis** — interactive directed graph with rendered amounts, beneficiary/wallet/device/phone relationships, suspicious-path counting. *(live)*
- **Cross-bank match clusters** — when the same identifier appears in STRs from multiple institutions it surfaces as a shared-intelligence cluster with an exposure total. *(live)*
- **Native STR workflow** — draft, edit, enrich, submit, review, and audit STRs directly inside Kestrel without exporting to another system. *(live)*
- **Alert queue with explainability** — every alert carries a list of `reasons` (rule code, score, evidence JSON, recommended action). Promotion to a case writes a full audit trail. *(live)*
- **Case management** — case ref generation, evidence linking, timeline, notes, alert linkage, exposure tracking. *(live)*
- **Persona-aware command view** — three different overview surfaces (analyst / bank CAMLCO / BFIU director) computed from the same intelligence engine. *(live)*
- **Compliance scorecard** — submission timeliness, alert conversion, peer-network coverage scored per bank-like institution. *(live)*
- **National threat dashboard** — channel-level threat map (RTGS, NPSB, BEFTN, MFS, Cash, Card), trend series, exposure aggregates. *(live)*
- **AI-assisted intelligence** — entity extraction, STR narrative drafting, alert explanation expansion, case summarization, typology suggestion, executive briefing generation. Backed by an internal provider abstraction (OpenAI / Anthropic / heuristic fallback) with redaction-by-default and a structured invocation audit. *(live, providers configured per environment)*
- **Pattern scanning** — bank-side workbench for queueing detection runs and reviewing flagged accounts. *(read paths live; the upload/parse/queue path is in active development — see `docs/production-plan.md` Phase 7)*
- **Synthetic regulator backfill** — a regulator-only admin action that loads a sanitized synthetic dataset derived from real Bangladesh bank statements into the live database for demos and evaluation. *(live)*

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
| Web app | Next.js 16.2.2 (App Router), React 19.2.4, TypeScript 5, Tailwind v4, `@xyflow/react`, recharts, zustand, zod | Vercel |
| API | FastAPI ≥0.115, SQLAlchemy 2 async, asyncpg, pydantic-settings, python-jose, networkx, httpx | Render web service |
| Worker | Celery 5.5 + Redis | Render worker service |
| Database | Postgres with RLS, pgcrypto, pg_trgm | Supabase |
| Auth | Supabase Auth (JWKS or HS256) | Supabase |
| File storage | `kestrel-uploads`, `kestrel-exports` buckets | Supabase Storage |
| Cache / queue | Redis | Render |
| AI providers | OpenAI + Anthropic via internal abstraction with heuristic fallback | Backend-only |
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
# Apply both SQL files to your Supabase project (SQL editor or supabase CLI):
#   supabase/migrations/001_schema.sql
#   supabase/migrations/002_rules_insert_policy.sql

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
- **Database → Supabase**. Apply `supabase/migrations/001_schema.sql` and `supabase/migrations/002_rules_insert_policy.sql` against the target project. Auth, storage buckets, and JWT signing keys are configured in the Supabase dashboard. Connection details live in environment variables on the engine.

CI on every PR and every push to `main` runs `.github/workflows/ci.yml`: web lint+build with Node 22, engine pytest + bytecode compile + seed manifest smoke test on Python 3.12.

The public landing page reads the engine's `/ready` endpoint live, so deployment drift (broken auth config, missing storage buckets, unreachable Redis, unconfigured AI providers) is visible without signing in.

## Project structure

```
kestrel/
├── web/                          Next.js 16 App Router frontend (Vercel)
│   ├── src/app/(public)/         Landing, pricing
│   ├── src/app/(auth)/           Sign in, register, forgot password
│   ├── src/app/(platform)/       Authenticated shell: overview, investigate,
│   │                             intelligence, alerts, cases, strs, scan,
│   │                             reports, admin
│   ├── src/app/api/              Next route handlers that proxy to the engine
│   ├── src/components/           Domain components + UI primitives
│   ├── src/lib/                  Supabase clients, engine proxy, normalizers
│   └── proxy.ts                  Supabase session middleware
│
├── engine/                       FastAPI intelligence engine (Render)
│   ├── app/main.py               Router registration
│   ├── app/auth.py               Supabase JWT validation (JWKS + HS256)
│   ├── app/config.py             Pydantic settings
│   ├── app/routers/              One router per domain
│   ├── app/services/             DB-backed business logic
│   ├── app/models/               SQLAlchemy models
│   ├── app/schemas/              Pydantic request/response models
│   ├── app/parsers/              CSV / XLSX / PDF statement parsers
│   ├── app/core/                 Graph builder + analyzer (detection engine
│   │                             core is scaffolded — see CLAUDE.md)
│   ├── app/ai/                   Internal AI provider abstraction, prompts,
│   │                             routing, redaction, audit, evaluations
│   ├── app/tasks/                Celery app + task modules
│   ├── seed/                     Synthetic data generators and loaders
│   ├── tests/                    pytest suites
│   └── render.yaml               Render service declarations
│
├── supabase/migrations/          001_schema.sql, 002_rules_insert_policy.sql
├── docs/production-plan.md       Phased roadmap and locked decisions
├── .github/workflows/            CI + Vercel + Render deployment
├── .env.example                  All environment variables
├── CLAUDE.md                     Project intelligence for Claude Code sessions
└── README.md                     This file
```

## Production roadmap

The phased plan is in [`docs/production-plan.md`](docs/production-plan.md). It is organized into ten phases from infrastructure baseline through production hardening. Phases 1, 3, 4, 5, 6, 8, and 9 have real database-backed implementations against the production schema. Phase 2 (AI platform) has a complete internal subsystem with providers, routing, prompts, redaction, audit, and a heuristic fallback. Phases 7 (real upload-driven scan pipeline) and 10 (production hardening, observability, AI evaluation) are the active areas of work.

For an unvarnished status report — what works, what is scaffolded, and the prioritized task list to reach the next demo milestone — read [`CLAUDE.md`](CLAUDE.md).

## License

No license file is currently included in this repository. All rights reserved by the project owners until a license is published.
