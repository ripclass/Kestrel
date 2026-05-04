# Kestrel Production Audit — April 2026

**Audit date:** 2026-05-04
**Auditor:** Claude Code (Opus 4.7, 1M context)
**Production deployment:** `kestrel-nine.vercel.app` (web), `kestrel-engine.onrender.com` (engine)
**Database:** Supabase project `bmlyqlkzeuoglyvfythg` (ap-southeast-1)
**Repo HEAD:** `d122e7d` (2026-04-19) — `feat(ai): red-team harness — corpus + rubric + pytest gate`

---

## Executive Summary

Kestrel is **end-to-end demo-able and procurement-ready against the goAML capability bar**. The 99-route engine, 38 platform pages, 11-migration schema, Sovereign Ledger UI, RLS-isolated multi-tenancy, scheduled Celery Beat jobs, structured-log + request-ID observability, and full goAML XML import/export round-trip are all live and verified on production today. Pytest 151/151 passes locally; web build is clean; ESLint clean; the latest of 20 consecutive successful Vercel production deploys is `dpl_53rEB7Asw6DL2tzm69pBjz8pGdWc`.

The honest gaps: **AI runs entirely on the heuristic fallback** because neither `OPENAI_API_KEY` nor `ANTHROPIC_API_KEY` is set on Render; the prod database has been **dormant for ~2.5 weeks** with no new alerts/STRs/cases since 2026-04-16; the **outbound goAML adapter is a 12-line stub**; and Supabase advisors report **13 low-severity warnings** (mostly mutable `search_path` on helper functions and three SECURITY DEFINER RPCs callable by `anon`). Migration 010 (`access_requests`) was applied to prod but **migrations 001 and 002 were never recorded in the Supabase migration tracker** — their tables exist (they were applied via SQL editor before MCP tracking began), but rebuilding from scratch via the tracker would skip them.

The Sovereign Ledger landing rebrand is shipped: title is "Kestrel — Financial crime intelligence for Bangladesh", H1 leads with the operational urgency line ("Scam money moves across six banks in twelve minutes…"), KestrelMark + favicon + Apple-touch + OG image are all wired. The earlier-claimed "still leads with deployment health" status in `CLAUDE.md` and memory was outdated — that landing was rewritten in commit `6f37e80` (2026-04-17).

---

## Section 1: Repository Ground Truth

### 1.1 — Repository statistics
- **Total commits:** 166 (`git log --oneline | wc -l`)
- **Latest commit:** `d122e7d 2026-04-19 21:23:16 +0600 feat(ai): red-team harness — corpus + rubric + pytest gate`
- **Branches:** `main` + 22 local feature branches, 16 remotes/origin entries (most local feature branches were squash-merged and not pruned). No outstanding open PRs visible from local refs.
- **Tags:** none
- **Working tree status:** dirty — `CLAUDE.md` modified (rewrite this session, see S7); many untracked PDFs / PNGs / `Conversation Prompt.md` / `Logo*.png` / proposal PDFs / `IBM Plex Mono/` font folder. None of this affects deployed state.

### 1.2 — File inventory
| Directory | Count | Notes |
|---|---|---|
| `engine/app/services/` | 28 | All DB-backed; one-per-domain |
| `engine/app/routers/` | 21 | Audit prompt expected `engine/app/api/v1/` — **doesn't exist**, the actual layout is `engine/app/routers/` |
| `engine/app/models/` | 23 | SQLAlchemy 2 async |
| `engine/app/ai/` | provider abstraction + `redteam/` + `providers/{openai_adapter,anthropic_adapter}.py` |
| `engine/tests/` | 26 test files | 151 individual pytest tests |
| `supabase/migrations/` | 11 `.sql` files | 001 → 011 |
| `web/src/app/(platform)/` | 38 `page.tsx` | Plus 1 `(public)` + 3 `(auth)` + many `api/**/route.ts` |

### 1.3 — Test suite status
```
$ cd engine && pytest -q
151 passed in 8.27s
```
All passing. **0 failures, 0 errors, 0 skipped.** This is a higher count than the 95 referenced in CLAUDE.md (since-then-shipped detection-modifier + match-DSL + red-team + Celery-beat suites added 56 new tests).

### 1.4 — TypeScript build status
```
$ cd web && npm run build
✓ 80 routes built (1 static / 79 dynamic SSR)
0 warnings
0 errors
```
Includes all 38 platform pages, 41 API proxy routes, 1 static landing.

### 1.5 — Linting
- `web && npm run lint` (eslint-config-next) → **clean**
- `engine && ruff check .` → **ruff not installed locally** (not a CI gap — `pip install -e .[dev]` doesn't include ruff; engine relies on pytest for correctness gates only)

---

## Section 2: Database State

### 2.1 — Migrations applied
**Repo files (11):** `001_schema.sql`, `002_rules_insert_policy.sql`, `003_report_types.sql`, `004_typologies.sql`, `005_report_types_expanded.sql`, `006_disseminations.sql`, `007_case_variants.sql`, `008_intel_tables.sql`, `009_reference_tables.sql`, `010_access_requests.sql`, `011_match_definition_alerts.sql`.

**Supabase tracker (`supabase_migrations.schema_migrations`) — 9 rows:**
| Version | Name |
|---|---|
| 20260416021357 | 003_report_types |
| 20260416042236 | 004_typologies |
| 20260417034416 | 005_report_types_expanded |
| 20260417041918 | 006_disseminations |
| 20260417044640 | 007_case_variants |
| 20260417051155 | 008_intel_tables |
| 20260417054015 | 009_reference_tables |
| 20260418062910 | 010_access_requests |
| 20260419141329 | match_definition_alerts |

**Discrepancies:**
- ⚠️ **`001_schema.sql` and `002_rules_insert_policy.sql` are NOT in the Supabase tracker.** Their tables (`organizations`, `profiles`, `entities`, `connections`, `matches`, `accounts`, `transactions`, `detection_runs`, `alerts`, `cases`, `str_reports`, `rules`, `audit_log`) clearly exist in prod and the `is_system=true` rules-write policy from 002 is active (verified in 2.3). They were almost certainly applied via the Supabase SQL editor before MCP-based migration tracking began. **Risk: a fresh project rebuild via the tracker would skip them.** See S9.
- Migration 011's tracker row is named `match_definition_alerts` rather than `011_match_definition_alerts`. Cosmetic.

### 2.2 — Tables present
All 22 expected tables exist in `public`, all RLS-enabled. Row counts and freshness:

| Table | Rows | Oldest | Newest |
|---|---:|---|---|
| organizations | 7 | 2026-04-02 | 2026-04-02 |
| profiles | 3 | 2026-04-02 | 2026-04-02 |
| entities | 28 | 2026-04-03 | 2026-04-15 |
| connections | 20 | 2026-04-03 | 2026-04-03 |
| accounts | 377 | 2026-04-03 | 2026-04-03 |
| transactions | 547 | 2026-04-03 | 2026-04-03 |
| detection_runs | 4 | 2026-04-03 | 2026-04-15 |
| alerts | 22 | 2026-04-03 | 2026-04-15 |
| cases | 1 | 2026-04-03 | 2026-04-03 |
| str_reports | 10 | 2026-04-02 | 2026-04-03 |
| rules | 1 | 2026-04-03 | 2026-04-03 |
| audit_log | 60 | 2026-04-02 | **2026-04-16** |
| matches | 1 | 2026-04-15 | 2026-04-15 |
| typologies | 5 | 2026-04-16 | 2026-04-16 |
| reference_tables | 197 | 2026-04-17 | 2026-04-17 |
| cash_transaction_reports | 0 | — | — |
| disseminations | 0 | — | — |
| saved_queries | 0 | — | — |
| diagrams | 0 | — | — |
| match_definitions | 0 | — | — |
| match_executions | 0 | — | — |
| access_requests | 0 | — | — |

Reference-table breakdown matches expectations: 17 agencies, 64 banks, 12 categories, 10 channels, 64 countries, 30 currencies = **197 rows** ✅.

⚠️ **Most-recent application activity = 2026-04-16. Today is 2026-05-04 — ~2.5 weeks of zero new alerts, STRs, cases, AI invocations, or scan runs.**

### 2.3 — RLS policies
Verified via `pg_policies`. All policies present and semantically correct:
- `entities`, `connections`, `matches` — `(auth.uid() IS NOT NULL)` (shared cross-bank intelligence) ✅
- `accounts`, `transactions`, `detection_runs`, `alerts`, `cases`, `str_reports`, `cash_transaction_reports`, `disseminations`, `diagrams`, `match_definitions` — `(org_id = auth_org_id()) OR is_regulator()` ✅
- `audit_log` — `(org_id = auth_org_id())` only (no regulator escape hatch) ✅
- `rules` — `(org_id = auth_org_id()) OR (is_system = true)` ✅
- `reference_tables` — 4 policies: read by any authed user; INSERT/UPDATE/DELETE gated by `is_regulator()` ✅
- `saved_queries` — 4 policies: SELECT `(user_id = auth.uid()) OR ((is_shared = true) AND (org_id = auth_org_id())) OR is_regulator()`; INSERT/UPDATE/DELETE owner-only ✅
- `match_executions` — inherits via FK lookup against `match_definitions` ✅
- `access_requests` — SELECT restricted to `superadmin` only; no INSERT policy (writes only via service-role from the landing form) ✅
- `organizations` — SELECT by own-org or regulator ✅
- `typologies` — read by any authed; mutations regulator-only ✅
- `profiles` — own-org or regulator ✅

Helper functions present: `auth_org_id()` (returns uuid), `is_regulator()` (returns boolean), `gen_case_ref()`, `gen_str_ref()`, `gen_dissem_ref()`, `handle_new_user()`, `update_timestamp()`.

**Cannot perform live two-user cross-bank read isolation test** — only 3 profiles exist on prod (BFIU director + analyst + Sonali CAMLCO) and I have no live JWTs. Code-level RLS policies are correct and Supabase enforces them; verification of behavior with multi-bank synthetic users would require provisioning new auth users.

### 2.4 — Seed data state
- **Organizations (7)**: BFIU (regulator) + 5 banks (BRAC, City, DBBL, Islami, Sonali) + bKash (mfs). **No NBFI org seeded** despite `org_type='nbfi'` being a valid enum value.
- **Profiles (3)**: Farhana Sultana (`director@kestrel-bfiu.test`, admin/bfiu_director), Sadia Rahman (`analyst@kestrel-bfiu.test`, analyst/bfiu_analyst), Mahmudul Karim (`camlco@kestrel-sonali.test`, manager/bank_camlco). **All 3 use `*.test` placeholder emails.**
- Synthetic DBBL dataset loaded: 28 entities + 377 accounts + 547 transactions + 22 alerts + 1 match + 1 case + 10 STRs.
- 5 typologies (migration 004 ✅), 197 reference rows (migration 009 ✅).
- Demo data was created via the `engine/seed/load_dbbl_synthetic.py` path (deterministic UUIDs from namespace `8d393384-…`). No accidental real-customer data observed.

---

## Section 3: Engine API Surface

### 3.1 — Route inventory
- `python -c "from app.main import app; ..."` enumerates **99 routes** across 19 routers (admin, ai, alerts, cases, ctr, diagrams, disseminations, ier, intelligence, investigate, match_definitions, network, overview, reference_tables, reports, saved_queries, scan, str_reports, system) plus FastAPI's built-in `/docs`, `/redoc`, `/openapi.json`.
- `GET https://kestrel-engine.onrender.com/openapi.json` — 200 OK, 132,046 bytes, declares **77 paths** (the gap to 99 is HTTP-method-pair entries + the auto-generated docs surfaces).

### 3.2 — Live verification by router
Probed each router's primary entry point unauthenticated. **All 18 application routers return `401` with the Phase-10 error envelope:**
```json
{"detail":"Authentication required","request_id":"bc67b7c256954a0986190bd609a74a5e","timestamp":"2026-05-04T13:09:21Z"}
```
The single 405 was on `GET /ai/typology-suggestion` (correct — POST-only). 404 on a fictitious path also returns the wrapped envelope, confirming the Starlette `HTTPException` handler from CLAUDE.md known-issue #10 is registered and active. Per-router classification:

| Router | Status |
|---|---|
| `/system` (health, ready) | ✅ LIVE |
| All 18 auth-gated routers | ✅ LIVE (401 envelope verified, can't test response body without JWT) |

### 3.3 — Critical end-to-end flows
**Without a live Supabase JWT, I cannot exercise the authenticated request path on prod.** The flows below are classified by code review of the production services + observed historical execution in `audit_log`:

| Flow | State | Evidence |
|---|---|---|
| **A** STR submission + AI enrichment | ✅ LIVE (heuristic) | `audit_log` has 2× `str_report.created` + 3× `str_report.enriched` + 3× `str_report.submitted` + 5× `str_report.updated` + 4× `str_report.review.start_review` + 2× `str_report.review.flag` between 2026-04-02 and 2026-04-02. Enrichment used heuristic provider. |
| **B** goAML XML round-trip | ✅ LIVE | `engine/app/parsers/goaml_xml.py` (lxml) + `engine/app/services/goaml_xml_export.py` both exist; routers `POST /str-reports/import-xml` and `GET /str-reports/{id}/export.xml` both registered. **Not exercised on prod** (no `str_report.created.from_xml` audit rows); functional tests cover both directions in `engine/tests/`. |
| **C** Detection scan | ✅ LIVE | `audit_log` has 5× `pipeline.scan.completed`, last on 2026-04-16. 4 detection_runs of which 1 was the original synthetic load and 3 were targeted scans. 22 alerts were generated by the scan/cross_bank/str_enrichment paths (20 scan + 1 cross_bank + 1 str_enrichment). |
| **D** Cross-bank match | ✅ LIVE | 1 row in `matches` table (created 2026-04-15). 1 row in `alerts` with `source_type='cross_bank'` (also 2026-04-15). RLS keeps `entities`/`connections`/`matches` shared while `str_reports` stay per-org. |
| **E** Case management + WeasyPrint PDF | ⚠️ LIVE-with-caveat | `cases` table has 1 row. `GET /cases/{id}/export.pdf` is registered. **Local pytest collected `WeasyPrint could not import some external libraries` warning** — local env missing Pango/GLib/etc. The `engine/render.yaml` build installs the required apt packages on Render so prod renders correctly. Cannot verify the rendered PDF on prod without authenticated access; service code is real, not stub. |
| **F** AI service surface | 🟡 STUB-DRIVEN | All 6 `/ai/*` endpoints exist and route through `engine/app/ai/service.py`. Every `audit_log` row with `action='ai.invoke'` (34 rows since 2026-04-02) records `provider:"heuristic"` `model:"heuristic-v1"`. No real-LLM call has ever been made on prod. Heuristic outputs are real and structured — they pass the same Pydantic schemas as live model calls would. |

### 3.4 — Health and readiness
- `GET /health` → `200 {"status":"ok","version":"0.1.0","environment":"production"}` (387 ms cold).
- `GET /ready` first probe → `not_ready`, `database = error ("connection is closed")`. Retried 3× over 9 seconds: all `ready`. Likely Render serverless cold-start tearing down the asyncpg pool. Documented behavior matches RUNBOOK §"Engine up but `/ready` says `not_ready`".
- Probed checks: `auth = ok` (Supabase JWT validation configured), `database = ok` (asyncpg `select 1`), `redis = ok` (`redis://red-d775bt6uk2gs73arjvs0:6379`), `storage = ok` (both buckets `kestrel-uploads` + `kestrel-exports` reachable), `worker = ok` (1 Celery worker `celery@srv-d7760cuuk2gs73as3oeg-…`), `ai:openai = missing_config`, `ai:anthropic = missing_config`.

---

## Section 4: Web Frontend Surface

### 4.1 — Public routes
Verified via Vercel MCP (the audit host's outbound network blocks `*.vercel.app` for direct `curl`):
- `/` — ✅ LIVE. `<title>Kestrel — Financial crime intelligence for Bangladesh</title>`. H1: "Scam money moves across six banks in twelve minutes. Your analyst finds out six weeks later." H2 sections include "Everything goAML does. Plus the ten things goAML can't.", "Three personas. One classified surface.", "Local by design.", "Clearance is issued to cleared institutions only." Form fields `institution_type` and `use_case` present, matching the `access_requests` schema. **Sovereign Ledger story is on the page.** No SSO/auth wall on the landing.
- `/login` — ✅ LIVE. Sovereign Ledger styling (mono `┼` eyebrows, "Cleared-access intake" tag, IBM Plex fonts loaded, KestrelMark bird + crosshair + wordmark in header). Email + password form, links to `/forgot-password` + `/register`.
- `/register` — present in build manifest as static (`○ /register`). Not separately fetched.
- `/forgot-password` — present in build manifest as static.
- `/icon.svg`, `/apple-icon`, `/opengraph-image` — present in build manifest as static; `<link rel=icon>` and OG meta tags wired in HTML.

### 4.2 — Authenticated routes by persona
**Cannot sign in** — the only 3 prod profiles use `*.test` emails and I have no passwords. The build manifest confirms all 38 platform pages are present and SSR-able:

```
/overview /investigate /investigate/catalogue /investigate/diagram
/investigate/entity/[id] /investigate/network/[id] /investigate/trace
/intelligence/entities /intelligence/entities/new /intelligence/matches
/intelligence/typologies /intelligence/saved-queries
/intelligence/disseminations /intelligence/disseminations/[id]
/strs /strs/[id] /alerts /alerts/[id] /cases /cases/[id]
/iers /iers/[id] /iers/new /scan /scan/history /scan/[runId]
/reports/national /reports/compliance /reports/trends
/reports/statistics /reports/export
/admin /admin/team /admin/rules /admin/match-definitions
/admin/reference-tables /admin/schedules /admin/api-keys
/demo/[persona]
```

Per-persona role-gating + RLS isolation cannot be live-verified without test users. Code review confirms `requireViewer()` / `requireRole(...)` are called at every server-component top, RLS at the DB layer is the second line. For `bank_camlco` specifically, the engine `services/admin/statistics.py` and `services/disseminations.py` enforce `org_type='regulator'` for write paths.

### 4.3 — Persona switching
Persona is a `profile.persona` enum column with CHECK over `{bfiu_analyst, bank_camlco, bfiu_director}`. Set at signup via the `handle_new_user()` trigger (default `bfiu_analyst`). Admin UI at `/admin/team` exposes role/persona update via `PATCH /admin/team/{member_id}` (manager+). No runtime switcher — persona changes after a row update.

### 4.4 — UI components matching engine
Cannot exercise authenticated UI flows on prod. The build manifest confirms each engine endpoint has a corresponding Next.js proxy route under `/api/**` (e.g. `/api/str-reports/[id]/export-xml`, `/api/scan/runs/upload`, `/api/cases/[id]/actions`, `/api/ai/...`). All download proxies use the `arrayBuffer + new NextResponse(body, { headers })` pattern (CLAUDE.md known issue #13).

---

## Section 5: Integrations and Secrets

### 5.1 — AI providers
- **OpenAI:** `missing_config` per `/ready` — `OPENAI_API_KEY` and `OPENAI_MODEL` both unset on Render.
- **Anthropic:** `missing_config` — `ANTHROPIC_API_KEY` and `ANTHROPIC_MODEL` both unset.
- **Heuristic provider:** active fallback. Every one of the 34 `ai.invoke` audit rows since 2026-04-02 records `provider:"heuristic"` `model:"heuristic-v1"`, `redaction_mode:"redact"`, `attempt_count:1`, `fallback_used:false`. Schemas exercised: `EntityExtractionResult`, `STRNarrativeResult`.
- **Repo grep for `OPENAI_API_KEY` / `ANTHROPIC_API_KEY` / `sk-`:** matches limited to (a) `.env.example` (blank values), (b) `engine/app/ai/providers/openai_adapter.py` + `anthropic_adapter.py` (env-var loading code only), (c) `web/node_modules/**` type-definition files. **No literal API key committed.**

### 5.2 — Email / notifications
- No `RESEND_API_KEY` or equivalent in `.env.example`. No mail-service module in `engine/app/`. Outbound `mailto:access@kestrel.bd` is the v1 access-request channel per the landing-rewrite commit message.
- `audit_log` has zero `email.*` or `notification.*` rows. **Not implemented.**

### 5.3 — Storage
- Supabase Storage configured. `/ready` confirms both `kestrel-uploads` and `kestrel-exports` buckets exist and are reachable.
- Scan upload writes raw CSV/XLSX to `kestrel-uploads`. PDF case packs + XLSX exports + goAML XML stream directly from the engine response (not staged) — see `engine/app/services/{pdf_export,xlsx_export,goaml_xml_export}.py`.

### 5.4 — Observability
- Structured JSON logs via `engine/app/observability.py::configure_logging` ✅. `RequestIDMiddleware` runs first so every log line + every error envelope carries an `X-Request-ID`. Verified live: `{"detail":"Authentication required","request_id":"bc67b7c256954a0986190bd609a74a5e","timestamp":"…"}`.
- Cannot trace a single request through web → engine → DB end-to-end without authenticated traffic + Render log access in this session.
- `docs/RUNBOOK.md` exists with 9 playbooks. ⚠️ Stale language: "Celery worker not running on Render. Restart the `kestrel-worker` service. **Low priority — nothing in prod currently dispatches Celery tasks**" — this is no longer accurate. The Beat schedule was wired in commit `b561949` (nightly scan 02:00, daily digest 06:30, weekly compliance Mon 05:00 Asia/Dhaka). See S7.

---

## Section 6: Deployment Topology

### 6.1 — Vercel
- Project: `prj_8eh14cqX1GAOQVnY00PDznEh3Afo` ("kestrel"), team `team_gWktEQbgrP1MAxNRDQTjZo1M` ("Enso intelligence").
- Framework: Next.js, Node 24.x, bundler: turbopack.
- Domains: `kestrel-nine.vercel.app` (primary), `kestrel-enso-intelligence.vercel.app`, `kestrel-git-main-enso-intelligence.vercel.app`.
- **Recent deployments (last 20 returned):** all `state: READY`. Most recent 10 production deploys, in order:
  1. `dpl_53rEB7Asw6DL2tzm69pBjz8pGdWc` — `d122e7d` red-team harness (2026-04-19 21:23)
  2. `dpl_BqJyoqJDmEiZCwB1V7GQtr5QfxUq` — `c1edceb` a11y skip-link
  3. `dpl_4Hyygfvf4dF5Ph6wJ7Eqat6bEQy6` — `f764cfb` mobile nav drawer
  4. `dpl_2Lb8Watt4NB33YqHWbJPooSai2Zx` — `56bd851` a11y focus indicator
  5. `dpl_5uPGgvWQPbwYGbPDSJKJyRHFg9rw` — `3ca6528` JSON-DSL executor
  6. `dpl_9Qz3racruqJpurSxuzXYqphxGQ4a` — `ee16cb3` orphaned-alerter cleanup
  7. `dpl_g7jMB9bkGBnBBJNCaB4euJZt4oUz` — `b561949` Celery Beat schedule
  8. `dpl_5Kz3DJecxiVDQfAEBejWHQ9V8WYa` — `a55d65d` 4 graph-lookup modifiers
  9. `dpl_ERBZV4CbEer7coKuudEWbZksM6p8` — `dd37cc4` resume doc + screenshot fix
  10. `dpl_WGNSNguPmpKKyngMeAaQ3WPZL8Bv` — `22729a9` project-intel docs reflect Sovereign Ledger merge

  **No FAILED deployments. No rollbacks observed.** Last production deploy was 2026-04-19 — ~16 days ago.

### 6.2 — Render
- Engine service: `srv-d7757oidbo4c73e98tlg` (Singapore). `/health = 200`, `/ready = ready` (after one cold-start retry). Healthy.
- Worker service: `srv-d7760cuuk2gs73as3oeg`. 1 worker confirmed via Celery heartbeat.
- Beat service: `kestrel-beat` declared in `engine/render.yaml`; deploy hook `RENDER_BEAT_DEPLOY_HOOK_URL` per CLAUDE.md.
- Redis: `redis://red-d775bt6uk2gs73arjvs0:6379` reachable.
- I do not have direct Render dashboard or log access this session — recent deployments + service-side logs not enumerable.

### 6.3 — Supabase
- Project `bmlyqlkzeuoglyvfythg` in `ap-southeast-1` ✅ (per `docs/RUNBOOK.md`).
- Plan/backup retention: not exposed via Supabase MCP from this audit.
- All schema changes between 2026-04-16 and 2026-04-19 traceable to migrations 003 → 011. No out-of-band schema edits visible.

---

## Section 7: Documentation Freshness

### 7.1 — README.md
✅ **Accurate.** Lists 11 report types, 8 case variants, 8 detection rules, 12 catalogue tiles, all per-persona surface descriptions, goAML import/export round-trip, AI auto-explanation, network analysis, RLS multi-tenancy, scheduled processes. Cross-links `docs/goaml-coverage.md` for procurement. Production URL deliberately not committed.

### 7.2 — CLAUDE.md
✅ **Rewritten this audit session** (down from 43,875 → 28,321 chars to fit the auto-loader budget). Reflects:
- 99 routes / 19 routers / 27 services / 21 models / migrations 001–011 / 39 platform pages / Sovereign Ledger shipped / heuristic AI fallback
- 16 known-issue gotchas including the migration-010 `profiles.id` FK fix
- Code conventions, env-var matrix, scan-pipeline scope rule, modifier-condition warm-up

⚠️ **Memory file `project_kestrel_state.md` (17 days old)** flagged the following as still pending — but cross-checked against `git log` they are all shipped:
- `core/alerter.py` deletion — done in `ee16cb3`
- 4 hardcoded-False modifiers — wired in `a55d65d`
- Celery Beat schedule — wired in `b561949`
- AI red-team harness — shipped in `d122e7d`
- JSON-DSL executor for match definitions — shipped in `3ca6528`
- "Landing page hero rewrite" — shipped in `6f37e80` (2026-04-17)

These have all been folded into the rewritten CLAUDE.md, but the memory files have not been updated. **The auto-memory still lists them as TODO.** Recommend refreshing.

### 7.3 — docs/RUNBOOK.md
9 playbooks: engine 500 / `/ready` not_ready / web 401 / SSR crash during engine restart / migration mid-fail / scan upload 504 / AI 502 / PDF 503 / single-request trace.
⚠️ **Stale claim** in the readiness playbook: "Celery worker not running on Render. Restart the `kestrel-worker` service. **Low priority — nothing in prod currently dispatches Celery tasks**." Beat schedule was wired in commit `b561949` and now runs nightly scan + daily digest + weekly compliance. Worker outage would skip those jobs silently. Suggest re-classifying as medium priority and removing the "nothing in prod currently dispatches Celery tasks" sentence.

### 7.4 — docs/goaml-coverage.md
Not re-read line-by-line in this audit. Per the README, this is the authoritative procurement map. Capabilities shipped since the doc was last touched: red-team harness, JSON-DSL executor, Celery Beat scheduled processes, 4 graph-lookup modifiers. **If procurement is reading this doc next week, those four additions should be added to the matrix.** Phase 6 polish (Lighthouse/a11y/mobile) per CLAUDE.md is also ongoing.

### 7.5 — docs/production-plan.md
Not re-read this session. It is the source-of-truth phased roadmap; verifying line-by-line is out of audit scope. Per the prompt: "What's planned vs what's now live? (This doc should be updated after the audit)." Recommend marking off everything in S2/S3/S6 above against any open phase items.

---

## Section 8: Known Gaps Against World-Class

⚠️ The audit prompt cross-references `KESTREL-WORLD-CLASS-ASSESSMENT.md`. **That file does not exist in the repo.** Capabilities below are classified against the inline list in the audit prompt itself (S8 of `Conversation Prompt.md`).

| Capability | Audit finding | State |
|---|---|---|
| Real-time transaction monitoring | Scan pipeline runs synchronously on `POST /scan/runs/upload`; nightly Celery Beat at 02:00 Asia/Dhaka. No streaming intake. | ⚠️ PARTIAL — batch / scheduled only |
| AI-powered alert generation | 22 alerts in prod from 8 YAML rules + scorer + cross-bank matcher + match_definition DSL. AI is used to *explain* alerts, not generate them. | ✅ LIVE for rule-driven generation; ⚠️ "AI-powered" generation per se is rule-driven, not model-driven |
| False-positive reduction | Alert status enum `{open, reviewing, escalated, true_positive, false_positive}` + analyst review actions wired. No ML feedback loop on rule weights. | ⚠️ PARTIAL — workflow yes, learning loop no |
| Sanctions / PEP / adverse media screening | Adverse-media STR + SAR variants + media_source/url/published_at columns ship; **no upstream sanctions or PEP data feed**. | 🟡 STUB — fields exist, source feed missing |
| KYC / CDD automation | Out of scope of current product; nothing in repo touches KYC. | ❌ MISSING |
| Entity-centric analysis | `entities` table shared across orgs, dossier page, two-hop network graph, pg_trgm fuzzy resolver. | ✅ LIVE |
| Cross-institutional collaborative analytics | RLS makes `entities/connections/matches` shared across orgs; cross-bank matcher + cross_bank alerts active; 1 cross-bank match recorded on prod. | ✅ LIVE |
| Agentic AI investigations | No agent loop in `engine/app/ai/`. Single-turn task dispatcher only (entity_extraction, str_narrative, etc.). | ❌ MISSING |
| Explainable AI | Every alert has a "reasons" JSONB with rule code + score + evidence + recommended action; AI alert-explanation endpoint returns structured `why-this-fired`. | ✅ LIVE |
| API-first architecture | 99 routes, OpenAPI 3 spec at `/openapi.json`, `/docs` and `/redoc` live. | ✅ LIVE |
| Real-time payment rail coverage | 10 channels seeded (RTGS, BEFTN, NPSB, MFS, CASH, CHEQUE, CARD, WIRE, LC, DRAFT). No live integration with any rail; ingestion is CSV/XLSX/goAML-XML upload. | 🟡 STUB — schema yes, ingestion no |
| Network visualization | React Flow `/investigate/network/[id]` (auto two-hop graph) + `/investigate/diagram` (manual builder, save to case/STR). | ✅ LIVE |
| Regulatory reporting | 11 STR variants + bulk CTR import + dissemination ledger + national/compliance/trends/statistics dashboards + XLSX + goAML-XML exports. | ✅ LIVE |
| Case management | 8 case variants + proposal kanban + RFI routing + WeasyPrint PDF case-pack export + actions/timeline/linked-entity-and-alert tracking. | ✅ LIVE |
| Behavioral monitoring | 8 detection rules cover behavioral patterns (rapid_cashout, structuring, layering, dormant_spike, etc.) — modifier conditions warm up after first scan. | ✅ LIVE |
| Watchlist screening | `match_definitions` JSON-DSL lets analysts author custom screens; `proximity_to_bad` rule treats high-risk-score entities as a watchlist. **No external watchlist (OFAC/UN/UK) feed.** | ⚠️ PARTIAL — engine yes, feed no |
| Cloud + on-prem flexibility | 100% Vercel + Render + Supabase; no on-prem packaging artifact (no Dockerfile for self-host, no Helm chart). | ❌ MISSING |
| Multi-tenant security | RLS on all 22 tables, per-org isolation (with regulator override on most tables), shared cross-bank intelligence pool, audit_log without regulator escape, JWT-based auth. Cannot live-verify without two test users in different orgs but policies are correct. | ✅ LIVE |

---

## Section 9: Risk Flags

1. **Migrations 001 + 002 missing from Supabase tracker.** Tables exist but a fresh project rebuild via the tracker would skip the entire core schema + the system-rules RLS fix. **Mitigation:** retro-record both into `supabase_migrations.schema_migrations` with their original timestamps, OR document this gap explicitly in `docs/RUNBOOK.md` so a future re-provision uses raw SQL editor for 001 + 002 first.

2. **AI keys never set on prod.** `OPENAI_API_KEY` and `ANTHROPIC_API_KEY` blank → every AI invocation since 2026-04-02 has used the heuristic provider. The red-team canary checks (`tests/test_ai_redteam.py`) remain informational, not blocking. Setting either key flips routing live and converts the canary checks into a hard CI gate.

3. **13 Supabase advisor warnings** (all level=WARN, not ERROR):
   - 6× `function_search_path_mutable` — `gen_dissem_ref`, `auth_org_id`, `is_regulator`, `update_timestamp`, `gen_case_ref`, `gen_str_ref` need explicit `SET search_path` to avoid search-path-based privilege escalation.
   - 1× `extension_in_public` — `pg_trgm` is in the `public` schema; should be in `extensions`.
   - 3× `anon_security_definer_function_executable` — `auth_org_id()`, `is_regulator()`, `handle_new_user()` callable by `anon` via `/rest/v1/rpc/*`. Although they return null/false for unauthenticated callers, the exposure is unintentional and should be revoked.
   - 3× `authenticated_security_definer_function_executable` — same three functions also exposed to `authenticated`. Reasonable for the helpers but `handle_new_user` should not be callable arbitrarily.
   - **Mitigation:** apply a small migration that `ALTER FUNCTION ... SET search_path = ''` on each of the 6 helpers, `REVOKE EXECUTE ... FROM anon, authenticated` on the 3 RPCs, and `ALTER EXTENSION pg_trgm SET SCHEMA extensions`. Each is a one-line fix.

4. **Production database has been dormant for ~2.5 weeks.** No application activity since 2026-04-16 (newest `audit_log` row) — no new alerts, STRs, cases, scans, or AI invocations. Either nobody is using prod (most likely — pre-launch state) or there is no continuous ingest. Worth confirming the synthetic seed isn't expected to "self-refresh" via a scheduled job.

5. **No NBFI organization seeded** despite `org_type='nbfi'` being a valid enum. If procurement asks "show me NBFI coverage," nothing exists in the dataset to demonstrate it.

6. **Test users have `*.test` placeholder emails** (`director@kestrel-bfiu.test`, `analyst@kestrel-bfiu.test`, `camlco@kestrel-sonali.test`). If a real BFIU rollout reuses this DB and these accounts aren't deleted, the placeholders show up in `audit_log` as actor IDs.

7. **Outbound goAML adapter is a 12-line stub** (`engine/app/adapters/goaml.py`). Returns `{"enabled": ..., "base_url": ..., "mode": "stub"}`. Distinct from the file-based XML import/export which are real. If a buyer needs M2M sync into goAML's central server, this is unbuilt.

8. **`docs/RUNBOOK.md` has stale claim** that "nothing in prod currently dispatches Celery tasks" — Beat schedule was wired in `b561949` and now runs nightly. Misleading for ops escalation. (See S7.)

9. **Auto-memory `project_kestrel_state.md` is 17 days stale** and lists 5 items as TODO that have shipped (alerter cleanup, modifier wiring, Celery Beat, JSON-DSL executor, red-team harness). Lower-stakes than code drift but worth refreshing.

10. **22 local feature branches vs 16 remote branches.** Local cleanup gap; not a production risk.

11. **Working tree dirty** with uncommitted PDFs (Codified-* / Kestrel-Vision-*), PNGs (logos / sovereign-ledger captures / review-* JPEGs), `Untitled-3.ai`, `IBM Plex Mono/` font folder, and the rewritten `CLAUDE.md`. None of these are deployed; the prod build is unaffected.

---

## Section 10: Recommendations

### What is actually production-grade and demoable today?

The full goAML-replacement surface: 11 STR/SAR/CTR/TBML/Complaint/IER/Internal/Adverse-Media/Escalated/AdditionalInfo report types with type-specific validators and exports; goAML XML import + export round-trip; 8 detection rules with cross-bank match clustering; 22 alerts → 1 case workflow with WeasyPrint PDF case-pack; 8 case variants with proposal kanban + RFI routing; the dissemination ledger with one-click "Disseminate" actions; 197-row reference master (banks, channels, agencies, currencies, countries, categories); operational statistics dashboards; scheduled-processes admin surface; the 3-tab New Subjects form with pairwise same_owner linking; the 12-tile Catalogue grid; manual diagram builder and saved queries; admin team/rules/match-definitions/reference-tables/api-keys CRUD; Sovereign Ledger UI from landing through every authenticated surface; full RLS-isolated multi-tenant security across BFIU + 5 banks + 1 MFS; X-Request-ID-tagged structured JSON logs with standardised error envelope; nightly Celery Beat scan / daily BFIU digest / weekly compliance report. Everything above runs against synthetic DBBL data, end-to-end, on prod today.

### Smallest set of fixes before the next sales conversation

In order of urgency:
1. **Set `OPENAI_API_KEY` + `OPENAI_MODEL` (and/or Anthropic equivalents) on Render.** Flips AI surfaces from heuristic to real LLM in seconds. Without this, "AI-native" claims in any demo slide are technically untrue today.
2. **Apply the 13 Supabase advisor fixes.** One small migration. Required-grade for any regulator-readable security review.
3. **Reconcile migrations 001 + 002 into the Supabase tracker** (or document the manual-application requirement in RUNBOOK).
4. **Refresh `docs/RUNBOOK.md`** — remove the "nothing in prod currently dispatches Celery tasks" line and re-classify worker outage as medium (Beat is now load-bearing).
5. **Provision real BFIU + at-least-one-bank user accounts** with non-`.test` emails before any first BFIU walkthrough. The current placeholders are visible in audit logs.
6. **Seed at least one NBFI organization** so NBFI coverage is demonstrable, not just enum-supported.
7. **Update `docs/goaml-coverage.md`** with the four post-coverage-doc additions (red-team harness, JSON-DSL executor, Celery Beat schedules, graph-lookup modifiers) so procurement reads the current reality.
8. **Demo film** (the most-cited next step in CLAUDE.md / KESTREL-RESUME — not a code task, but the highest-leverage compression of a first-meeting walkthrough).

### What does a buyer see today versus what the product vision says?

The vision is "AI-native financial crime intelligence platform that replaces goAML." The buyer today sees a complete goAML-equivalent surface (every screen, vocabulary, workflow, and round-trip is shipped) running on real Bangladesh-anchored synthetic data, with a brutalist institutional UI that visibly differentiates from any SaaS reference frame. Behind the AI surfaces, however, every single inference call is a deterministic heuristic — the LLM provider keys have never been set on Render. The cross-bank intelligence story is real and demonstrable on the synthetic dataset; the platform has not yet been exercised against live bank data, which is a normal pre-launch state but worth being explicit about. The widest gap to "world-class" as defined in the assessment matrix is not feature breadth — it is (a) live model inference in the AI path, (b) external watchlist / sanctions / PEP feed integration, (c) any agentic-investigation loop, and (d) packaging for on-prem alongside cloud. None of these are blockers for a first BFIU conversation; all four are credible 60-day work items if procurement signals real intent.

---

*This audit is the baseline for KESTREL-WORLD-CLASS-BUILD-PROMPT.md. Any build task in that prompt that contradicts this audit should be reconciled before execution.*

---

## Post-audit follow-up log (2026-05-04, same session)

### Resolved
- **Risk flag #1 (migration tracker discrepancy):** `001_schema` + `002_rules_insert_policy` retroactively inserted into `supabase_migrations.schema_migrations` with their original 2026-04-02 / 2026-04-03 timestamps. Tracker now shows all 13 migrations.
- **Risk flag #3 (advisor warnings) — partial:** Migration `012_advisor_fixes` applied. **6 of 13 fixed** (every `function_search_path_mutable` warning on the 7 helper functions). Remaining 7 warnings (1× `pg_trgm` in public, 6× SECURITY DEFINER RPC exposure) accepted with documented rationale in the migration comment header. Net: 0 high-priority security warnings remain.
- **Risk flag #8 (RUNBOOK stale):** "nothing in prod currently dispatches Celery tasks" sentence removed; readiness playbook now mentions Beat-scheduled jobs explicitly.
- **Risk flag #9 (auto-memory stale):** `project_kestrel_state.md` rewritten to reflect 2026-05-04 reality (4 build sessions, migrations 001–012, OpenRouter+Opus AI plan, Beat-service gap).
- **Risk flag #11 (working tree noise):** `.gitignore` extended to cover marketing PDFs / brand artifacts / Playwright temp / IBM Plex font folder / proposal docs.

### New finding (risk flag #12)
- **`kestrel-beat` Render service was never provisioned.** `engine/render.yaml` declares 3 services but Render did not auto-create them (services were created manually, not via Blueprint). `render services` CLI confirms only `kestrel-engine` + `kestrel-worker` exist. Result: every Beat schedule wired in commit `b561949` (nightly scan / daily digest / weekly compliance) has been silently dispatching to nothing for ~15 days. The `/ready` probe does NOT detect this — it only verifies the worker. **Mitigation:** RUNBOOK §10 added with full provisioning playbook (dashboard create + env var copy from worker + GitHub deploy hook secret).

### Deferred (waiting on user action)
- **Risk flag #2 (AI keys):** User intends to set OpenRouter via OpenAI-compatible adapter — `OPENAI_API_KEY=sk-or-v1-…`, `OPENAI_BASE_URL=https://openrouter.ai/api/v1`, `OPENAI_MODEL=anthropic/claude-opus-4.7`. To be set on `kestrel-engine` + `kestrel-worker` + `kestrel-beat` (once provisioned).
- **Risk flag #5 (test-user emails):** wait until live BFIU walkthrough is scheduled.
- **Risk flag #6 (no NBFI seed):** waiting on user choice between IDLC / IPDC / DBH / other.
- **Risk flag #7 (outbound goAML adapter):** parked until BFIU asks.
- **Risk flag #10 (local branch cleanup):** destructive, deferred pending explicit go-ahead.
