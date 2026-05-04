# Kestrel — V2 build resume prompt

Drop this into the next session. Full state in `CLAUDE.md` (auto-loaded).

---

## Context (verified live 2026-05-04)

V2 of the world-class build is in motion. **Phase 1 of `KESTREL-WORLD-CLASS-BUILD-V2.md` shipped to `main` 2026-05-04** — three commits, all auto-deployed to Vercel + Render with no failures. Phases 2–6 still pending.

| Surface | Status |
|---|---|
| Engine | `https://kestrel-engine.onrender.com` — 103 routes, 159/159 pytest, `/ready` clean |
| Web | `https://kestrel-nine.vercel.app` — 40 platform pages, Sovereign Ledger UI, last commit `dfbfca3` |
| AI | `anthropic/claude-sonnet-4.6` via OpenRouter on engine + worker + beat (no longer heuristic) |
| Render services | `kestrel-engine` (`srv-d7757oidbo4c73e98tlg`), `kestrel-worker` (`srv-d7760cuuk2gs73as3oeg`), `kestrel-beat` (`srv-d7sajha8qa3s73e1spv0`) — all running |
| Supabase | project `bmlyqlkzeuoglyvfythg`, ap-southeast-1, migrations 001 → 012 applied |

## What V2 Phase 1 shipped (don't redo)

| Commit | Task | Outcome |
|---|---|---|
| `d64049d` | **P1.1** cross-bank intelligence dashboard | 4 engine routes under `/intelligence/cross-bank/*`, persona-aware service in `engine/app/services/cross_bank.py` (8 new tests covering invariants), `web/src/app/(platform)/intelligence/cross-bank/page.tsx` + `cross-bank-dashboard.tsx` client component, sidebar nav entry. Live on prod. |
| `6bd2366` | **P1.2** multi-bank synthetic seed | `engine/seed/multi_bank_synthetic.py` (idempotent, deterministic UUIDs, sibling to the DBBL loader) + `multi_bank_to_sql.py` SQL emitter. **Applied to prod 2026-05-04: 24 entities + 6 matches + 17 cross-bank alerts.** Topology: 1 marquee 5-bank entity (Mohammad Karim, `+880 1711-555-001`), 2× 3-bank, 3× 2-bank, 18 single-bank. ⚠️ The 64 accounts + 105 transactions + 35 STRs are committed in the seed module but **not yet applied to prod** — see below. |
| `dfbfca3` | **P1.3** cross-bank intelligence whitepaper | `docs/cross-bank-intelligence.md` (2232 words / ~6 pages, every claim cites a code path) + `.html` (browser-viewable, Print → PDF works) + `docs/render_pdf.py` (renders both HTML and PDF when WeasyPrint deps load). |

**Pre-V2 audit baseline lives at `docs/production-audit-2026-04.md`** — engineering ground truth, 10 sections + post-audit follow-up log. Read that first if you need to verify any claim about current state.

## Outstanding small-pickup inside Phase 1

⚠️ Apply the remaining multi-bank-seed chunks to prod when convenient. Not blocking — the cross-bank dashboard works without them — but they'd enrich the entity dossier when bank users click through to a flagged subject:

```bash
# Option A: from any env with DATABASE_URL set
python -m seed.multi_bank_synthetic --apply

# Option B: via the SQL emitter (no DB connection needed)
python -m seed.multi_bank_to_sql > /tmp/seed.sql
# then paste /tmp/seed.sql into Supabase SQL editor
```

What lands on apply that isn't already on prod: **64 accounts + 105 transactions + 35 STRs**.

Also worth checking tomorrow morning ~03:00 Asia/Dhaka: did the Beat scheduler fire the nightly scan now that `kestrel-beat` is provisioned? Query:

```sql
SELECT action, created_at FROM public.audit_log
  WHERE action LIKE 'pipeline.scan.%' AND created_at > '2026-05-04'
  ORDER BY created_at DESC LIMIT 5;
```

Expect at least one `pipeline.scan.completed` row with timestamp 02:00–02:30 BDT next-day. If nothing appears, check `render logs --resources srv-d7sajha8qa3s73e1spv0` for the Beat scheduler error — most likely a missing env var.

## Next priority: Phase 2 — bank-direct surface

The single biggest go-to-market unlock. A bank can sign up, deploy, and use Kestrel **without BFIU being present as a tenant**. From the V2 prompt §"PHASE 2":

| Task | Estimate | What |
|---|---|---|
| **2.1** Bank-direct landing page | 1 day | New route `web/src/app/(public)/banks/page.tsx` (or subdomain `bank.kestrel-nine.vercel.app` if you wire that). Sovereign Ledger design system. Hero, BB Circular 26/2024 callout, three-column features (real screenshots from prod), cross-bank intelligence section linking to `docs/cross-bank-intelligence.html` (P1.3 deliverable), pricing tiers (Tk 60 lakh / 1.5 crore / 4 crore), request-demo CTA. |
| **2.2** Bank-only signup flow | 1 day | New route `web/src/app/(public)/signup/bank/page.tsx`. Form fields: bank name, full name, role, email, phone, demo-want narrative. On submit: create org with `org_type='bank'`, create user via Supabase Auth, set `persona='bank_camlco'`, send magic link. After login → trigger Task 2.3 demo seed for the new tenant. Feature flag: `ENABLE_BANK_DIRECT_SIGNUP` (env var, default `true`). |
| **2.3** Demo bank seed | 1 day | `engine/seed/load_demo_bank.py`. Per-tenant deterministic UUIDs from a per-tenant namespace. Generates 6 months of synthetic transactions (~10k records, realistic Bangladeshi channel mix), 12 alerts (3 critical / 5 high / 4 medium), 3 draft STRs at different lifecycle stages, 5 cases (2 standard / 1 proposal / 2 RFI), 4 entities pre-flagged with cross-bank context (link to the marquee 5-bank entity from V2 P1.2 so the new tenant sees `/intelligence/cross-bank` populated immediately). |
| **2.4** Persona-isolation verification | 0.5 day | Code-level isolation is correct per the audit (`requireViewer()` / `requireRole(...)` at every server-component top, RLS at the DB layer). This task is **verification only**: provision two test users in two different bank orgs, confirm A can't read B's STRs/alerts/transactions, confirm both can't access `/iers` or `/intelligence/disseminations` or `/admin/match-definitions` (regulator-only), confirm both CAN access `/intelligence/cross-bank` with the anonymised view. Document at `docs/multi-tenant-isolation-verified.md`. |
| **2.5** Request-demo form wiring | 0.5 day | The `access_requests` table is live (migration 010). The Sovereign Ledger landing form fields already match its schema (`institution_type`, `use_case`). Wire the POST handler that inserts via service-role + sends notification email to `ripon@enso-intelligence.com` via Resend (set `RESEND_API_KEY` first). Show "Thank you, we'll be in touch within 24 hours" confirmation. |

**Total Phase 2 estimate: 4–5 focused days.**

## After Phase 2

| Phase | Estimate | Strategic unlock |
|---|---|---|
| **P3** Real-time scoring API | 5–6 days | The single biggest enterprise capability gap. New endpoint `POST /api/v1/transactions/score` with sub-500ms target, reuses the existing 8 detection rules + entity resolver + matcher. New `realtime_scoring_log` table (migration 013). Feedback endpoint as foundation for ML loop. New monitoring dashboard. |
| **P4** Sanctions/PEP/adverse-media screening | 5–6 days | OFAC/EU/UN/UK ingestion (free public lists, daily cron), screening API, screening UI, ComplyAdvantage adapter as placeholder. Migration 014 for `watchlist_entries`. Real-time scoring integration so cross-rail screening happens inline. |
| **P5** KYC/CDD module | 5 days | Greenfield. New `customers` table (migration 015 — careful, P3 might use 013, P4 014, P5 015 — pick numbers contiguously when shipping). Customer onboarding service, 6 API endpoints, KYC UI, periodic re-screening Beat task. |
| **P6** Status page + pricing tiers + demo polish | 3–4 days | Public status surface driven by `/ready` history, pricing-tier enforcement (`engine/app/services/billing.py` + `organizations.plan_id` migration), weekly demo-data refresher Beat task, `/demo` public route with persona switcher. |

## What to read first when you pick this up

1. `docs/production-audit-2026-04.md` — engineering ground-truth baseline. Don't skip — every claim about current state should be verified against this before adding new claims.
2. `CLAUDE.md` — auto-loaded. Has all the architecture, conventions, known issues, env vars.
3. `KESTREL-WORLD-CLASS-BUILD-V2.md` — the canonical V2 build prompt. Phases 2–6 in full detail.
4. `engine/app/services/cross_bank.py` and `web/src/components/intel/cross-bank-dashboard.tsx` — the V2 P1.1 reference for how persona-aware services and Sovereign Ledger components compose. Phase 2's bank-direct surface should follow the same patterns.
5. `engine/seed/multi_bank_synthetic.py` — the V2 P1.2 reference for the per-tenant demo-seed pattern Phase 2 Task 2.3 will extend.

## Hard constraints (don't break)

- **Live-verify on prod after every task.** Not "tests pass and pushed." Actually open the deployed app, exercise the new feature, confirm it works under real conditions. Both audiences. Both personas. The audit found 20 consecutive successful prod deploys with zero failures — V2 P1.1, P1.2, P1.3 added 3 more. Maintain the streak.
- **Don't modify the BFIU regulator surface.** Specifically: `/iers`, `/intelligence/disseminations`, `/admin/match-definitions`, `/admin/reference-tables`, `/reports/national`, `/reports/compliance`, `/reports/trends`, `/reports/statistics`, `/admin/schedules`. The 99 (now 103) existing API routes — extend, never remove or modify. The 12 existing migrations — only add new ones. The Beat schedule — extend (add new scheduled tasks), never modify or remove existing ones.
- **Don't touch the Sovereign Ledger landing at `/`** — that's BFIU-facing and it's right. Phase 2's bank-direct landing lives at `/banks` (or a subdomain), not at `/`.
- **Never use the migration tracker for seed data.** Migrations are DDL only. Use `execute_sql` (or the seed loader) for data.
- **Persona invariants are enforced in the service layer**, not in the dashboard component. The bank-persona view of cross-bank data masks peer bank names + match keys *before* the data leaves the engine. Phase 2's bank-direct seed should preserve this — never pass real peer-bank names through to a bank-persona client.

## Hard preferences (the user has already corrected on these — don't repeat)

- Short answers to short questions. Don't pad explanations.
- Don't say "waiting" when asked for an update — give the current state.
- Verify end-to-end on prod, not just in tests.
- One migration per task, applied before merge, idempotent (`ON CONFLICT DO NOTHING` for seeds).
- Run actual `python -c "from app.main import app"` before pushing — `py_compile` doesn't catch missing imports.
- Vercel-plugin hooks ("observability instrumentation", "Next.js skill", etc.) are mostly false-positives in this repo — engine-side X-Request-ID + structured JSON logs already cover proxied calls. CLAUDE.md known-issue #15 documents this.

## Auto mode

The user typically runs in auto mode. Execute autonomously, prefer action over planning, batch independent tool calls. Confirm before destructive operations (force push, branch deletion, seed apply that isn't idempotent). Standard "commit + push" after a task is finished is expected without asking, unless the work touches shared infrastructure (Render env vars, Supabase migration tracker rows you didn't write yourself).

Ready when you are.
