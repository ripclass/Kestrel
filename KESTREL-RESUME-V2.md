# Kestrel — V2 build resume prompt

Drop this into the next session. Full state in `CLAUDE.md` (auto-loaded).

---

## Context (verified live 2026-05-05)

V2 of the world-class build is in motion. **Phases 1, 2, and 3 of `KESTREL-WORLD-CLASS-BUILD-V2.md` shipped to `main`** — ten commits over 2026-05-04 / 2026-05-05, all auto-deployed to Vercel + Render with no failures. Phases 4–6 still pending.

| Surface | Status |
|---|---|
| Engine | `https://kestrel-engine.onrender.com` — 107 routes, 193/193 pytest, `/ready` clean |
| Web | `https://kestrel-nine.vercel.app` — 41 platform pages + `/banks` (V2 P2.1) + `/signup/bank` (V2 P2.2) + `/monitoring/realtime` (V2 P3.4), Sovereign Ledger UI, last commit `67d038b` |
| AI | `anthropic/claude-sonnet-4.6` via OpenRouter on engine + worker + beat (no longer heuristic) |
| Render services | `kestrel-engine` (`srv-d7757oidbo4c73e98tlg`), `kestrel-worker` (`srv-d7760cuuk2gs73as3oeg`), `kestrel-beat` (`srv-d7sajha8qa3s73e1spv0`) — all running |
| Beat schedule | nightly scan (02:00 BDT), daily digest (06:30), weekly compliance (Mon 05:00), and **`demo_bank_seed_pending` every 10 min** (V2 P2.3) |
| Supabase | project `bmlyqlkzeuoglyvfythg`, ap-southeast-1, migrations 001 → 014 applied (013 was a P2.4 hot-fix; 014 is `realtime_scoring_log` from P3.1+P3.2) |

## What V2 Phase 1 shipped (don't redo)

| Commit | Task | Outcome |
|---|---|---|
| `d64049d` | **P1.1** cross-bank intelligence dashboard | 4 engine routes under `/intelligence/cross-bank/*`, persona-aware service in `engine/app/services/cross_bank.py` (8 new tests covering invariants), `web/src/app/(platform)/intelligence/cross-bank/page.tsx` + `cross-bank-dashboard.tsx` client component, sidebar nav entry. Live on prod. |
| `6bd2366` | **P1.2** multi-bank synthetic seed | `engine/seed/multi_bank_synthetic.py` (idempotent, deterministic UUIDs, sibling to the DBBL loader) + `multi_bank_to_sql.py` SQL emitter. **Applied to prod 2026-05-04: 24 entities + 6 matches + 17 cross-bank alerts.** Topology: 1 marquee 5-bank entity (Mohammad Karim, `+880 1711-555-001`), 2× 3-bank, 3× 2-bank, 18 single-bank. ⚠️ The 64 accounts + 105 transactions + 35 STRs are committed in the seed module but **not yet applied to prod** — see below. |
| `dfbfca3` | **P1.3** cross-bank intelligence whitepaper | `docs/cross-bank-intelligence.md` (2232 words / ~6 pages, every claim cites a code path) + `.html` (browser-viewable, Print → PDF works) + `docs/render_pdf.py` (renders both HTML and PDF when WeasyPrint deps load). |

## What V2 Phase 2 shipped (don't redo)

| Commit | Task | Outcome |
|---|---|---|
| `5932e9c` | **P2.1** Bank-direct landing | New public route `web/src/app/(public)/banks/page.tsx` composing 8 Sovereign-Ledger sections under `web/src/components/banks/banks-*.tsx` — hero with embedded `IntakeForm`, 4-stat ledger, 3-module features, dedicated cross-bank intelligence section linking to the P1.3 whitepaper, BB Circular 26/2024 callout, three BDT-denominated pricing tiers (Tk 60 lakh / 1.5 crore / 4 crore), 4-step operating loop, two-CTA footer. Static prerendered. Reuses `PublicHeader` + `PublicFooter` + `IntakeForm`. The BFIU-facing landing at `/` is untouched. |
| `98e21ae` | **P2.2** Bank-only self-serve signup | `web/src/app/(public)/signup/bank/page.tsx` (force-dynamic, `notFound()` when `ENABLE_BANK_DIRECT_SIGNUP=false`) + `web/src/components/banks/bank-signup-form.tsx` + server action `web/src/app/actions/bank-signup.ts` (validates input, generates a unique slug, inserts an `organizations` row with `org_type='bank'` + `settings.demo_seed_pending=true` + `settings.demo_narrative`, invites the user via `auth.admin.inviteUserByEmail` with `raw_user_meta_data` setting `org_id` + `persona='bank_camlco'` + `role='admin'`). Rolls back the org on invite failure. Magic link works because `handle_new_user` was already schema-qualified at migration-012 time. |
| `0b15a23` | **P2.3** Demo bank seed + Beat dispatch | `engine/seed/load_demo_bank.py` — idempotent per-tenant loader. Each tenant gets ~25 entities (4 cross-bank flagged + 21 single-bank), ~30 internal accounts, ~10k transactions over 180 days (40% NPSB / 25% BEFTN / 15% RTGS / 15% MFS / 5% cash+cheque), 12 alerts (3 critical / 5 high / 4 medium), 3 STRs at draft / flagged / submitted, 5 cases (2 standard / 1 proposal / 2 RFI), 4 cross-bank Match rows linking to BRAC / City / Islami / Sonali. Bulk transaction insert via `pg_insert(...).on_conflict_do_nothing()`. After successful apply, sets `settings.demo_seed_pending=false` + records `settings.demo_seed_counts`. Plus `engine/app/tasks/demo_seed_tasks.py` Celery wrapper + Beat schedule entry running every 10 min. CLI: `--org-id <uuid> --apply` for one tenant, `--apply-pending` for all flagged. |
| `857f415` | **P2.4** Persona-isolation verification + migration 013 hot-fix | `docs/multi-tenant-isolation-verified.md` — procurement-grade artifact, 8 sections with verbatim RLS policy citations, file:line citations of regulator-only mutation guards, cross-bank persona invariants from `cross_bank.py`, and live verification on prod (RLS simulation as Sonali CAMLCO showed 4/10 STRs visible / 3/49 alerts; cross-bank dashboard rendered peers as `PEER INSTITUTION N` with match keys redacted to `····XXXX`; `POST /api/reference-tables` as Sonali → `403 Insufficient role`). **Surfaced a production regression**: migration 012's `SET search_path = ''` lockdown broke `auth_org_id`, `is_regulator`, `gen_case_ref`, `gen_str_ref`, `gen_dissem_ref` because their bodies referenced unqualified relations/sequences. **Migration 013 (`qualify_security_definer_helpers`) is the hot-fix** — applied to prod via Supabase MCP. Without 013, every cases / STR / dissemination INSERT errored and direct-PostgREST RLS evaluation errored. Read paths were unaffected because the engine connects as `postgres` (BYPASSRLS); only trigger writes were broken. Regression window: 30 hours of zero new cases / STRs / disseminations between 2026-05-04 (012 applied) and 2026-05-05 (013 applied). |
| `166818e` | **P2.5** Resend wiring on briefing-intake form | `web/src/app/actions/access.ts` adds `sendBriefingNotification` after the `access_requests` insert. Best-effort: missing `RESEND_API_KEY` → log + early return; non-200 from Resend → log + return; the form-facing response stays `success: true`. Reply-to set to the requester's contact email. Plain-text + HTML bodies, both Sovereign-Ledger flavoured. Three new env vars: `RESEND_API_KEY` (auto-provisioned by Vercel Marketplace integration once installed), `BRIEFING_NOTIFY_EMAIL` (default `intake@enso-intelligence.com`), `BRIEFING_FROM_EMAIL` (default `Kestrel <onboarding@resend.dev>` until the sender domain is verified). |

**Pre-V2 audit baseline lives at `docs/production-audit-2026-04.md`** — engineering ground truth, 10 sections + post-audit follow-up log. Read that first if you need to verify any claim about current state.

## Outstanding small-pickups

⚠️ **V2 P1 leftover:** apply the remaining multi-bank-seed chunks (64 accounts + 105 transactions + 35 STRs) to prod when convenient. Not blocking — the cross-bank dashboard works without them — but they'd enrich the entity dossier when bank users click through to a flagged subject:

```bash
# Option A: from any env with DATABASE_URL set
python -m seed.multi_bank_synthetic --apply

# Option B: via the SQL emitter (no DB connection needed)
python -m seed.multi_bank_to_sql > /tmp/seed.sql
# then paste /tmp/seed.sql into Supabase SQL editor
```

⚠️ **V2 P2.5 leftover:** install the Vercel Marketplace Resend integration on the `kestrel` project so `RESEND_API_KEY` is auto-provisioned, then verify `enso-intelligence.com` as a Resend sending domain (DNS: SPF TXT + DKIM CNAMEs). Until installed, briefing-intake emails are no-op (form succeeds, DB row lands, no email goes out). After the domain is verified, optionally set `BRIEFING_FROM_EMAIL=Kestrel <noreply@enso-intelligence.com>` on Vercel. No redeploy needed — the next form submission picks up new env vars.

**First-signup checklist** (the first time someone hits `/signup/bank`):

- New `auth.users` row + `profiles` row with `persona='bank_camlco'` + `role='admin'` linked to the new `organizations` row
- New org has `settings.demo_seed_pending=true` and `settings.demo_narrative` populated
- Within ~10 min, Beat fires `demo_bank_seed_pending` → seeds the new tenant → flips flag false + records `settings.demo_seed_counts`
- New CAMLCO clicks magic link → lands on `/overview` → sees populated dashboard with cross-bank context

If anything looks wrong: query `audit_log` for the request_id, check `render logs --resources srv-d7sajha8qa3s73e1spv0` for Beat dispatch logs, verify `organizations.settings ->> 'demo_seed_pending'` flipped via Supabase MCP.

## What V2 Phase 3 shipped (don't redo)

| Commit | Task | Outcome |
|---|---|---|
| `1dc575a` | **P3.1+P3.2+P3.3** Real-time scoring endpoint + log schema + feedback endpoint | New router `engine/app/routers/realtime.py` mounted at `/transactions`. `POST /score` returns sub-500ms decisioning over the shared `entities` + `matches` tables. Decision bands: `<30 approve`, `<60 review`, `<80 hold`, `>=80 reject`. Reasons array fully explainable per contribution (`amount_*`, `channel_*`, `new_account_high_value`, `from/to_entity_flagged`, `from/to_cross_bank_flagged`). `POST /score/{id}/feedback` records `legitimate / fraud / unsure`. `GET /score/recent` for the live stream. Migration 014 (`realtime_scoring_log`) applied via Supabase MCP — RLS own-org-or-regulator on SELECT, own-org only on UPDATE, 4 indexes, decision CHECK constraint. 29 pure-helper tests added. |
| `67d038b` | **P3.4+P3.5** Monitoring dashboard + API integration docs | New page `/monitoring/realtime` with auto-refresh every 30s. Sovereign Ledger styled, persona-aware footer (bank own-org / regulator aggregate). Decision distribution strip, 4-stat tile row (calls / latency p50-p95-p99 / cross-bank flagged / reject rate), top scored last hour, recent stream. New engine route `GET /transactions/score/metrics` returning the dashboard payload. Two Next API proxies. Nav entry under Operations. `docs/api-integration.md` (~280 lines) covering every endpoint with cURL + Python examples, decision bands, reason codes, error envelope, retry semantics. Also fixed a pre-existing CI lint regression in `cross-bank-dashboard.tsx` (react-hooks/set-state-in-effect) that had been broken since V2 P1.1 — CI is now green. 5 percentile-helper tests added. |

**Total Phase 3 estimate spent: ~1 focused day** (vs the 5-6 day estimate). Came in under because the existing entity resolver + matches infrastructure carried most of the heavy lifting; the scoring path is mostly composition + audit logging.

## After Phase 3

| Phase | Estimate | Strategic unlock |
|---|---|---|
| **P4** Sanctions/PEP/adverse-media screening | 5–6 days | OFAC/EU/UN/UK ingestion (free public lists, daily cron), screening API, screening UI, ComplyAdvantage adapter as placeholder. Migration **015** for `watchlist_entries`. Real-time scoring integration so cross-rail screening happens inline (touches `engine/app/services/realtime_scoring.py` to add a `from/to_sanctions_hit` reason class). |
| **P5** KYC/CDD module | 5 days | Greenfield. New `customers` table (migration **016**). Customer onboarding service, 6 API endpoints, KYC UI, periodic re-screening Beat task. |
| **P6** Status page + pricing tiers + demo polish | 3–4 days | Public status surface driven by `/ready` history, pricing-tier enforcement (`engine/app/services/billing.py` + `organizations.plan_id` migration), weekly demo-data refresher Beat task, `/demo` public route with persona switcher. The realtime-scoring decision bands become tier-configurable here. |

> **Migration numbering:** 014 is now applied. **015** is the next available — make sure phases 4 / 5 / 6 keep contiguous numbering. Don't reuse 014.

## What to read first when you pick this up

1. `docs/production-audit-2026-04.md` — engineering ground-truth baseline. Don't skip — every claim about current state should be verified against this before adding new claims.
2. `CLAUDE.md` — auto-loaded. Has all the architecture, conventions, known issues, env vars. The V2 P2 surfaces are documented in §"Bank-direct surface (V2 P2)".
3. `KESTREL-WORLD-CLASS-BUILD-V2.md` — the canonical V2 build prompt. Phases 3–6 in full detail.
4. `docs/multi-tenant-isolation-verified.md` — V2 P2.4 verification artifact. Cite this doc when answering "is data isolated between bank tenants?" for a procurement audience.
5. `engine/app/services/cross_bank.py`, `engine/seed/load_demo_bank.py`, `web/src/app/actions/bank-signup.ts` — the V2 P1 + P2 reference patterns for persona-aware services, idempotent per-tenant seeds, and service-role provisioning actions.
6. `engine/app/services/realtime_scoring.py`, `engine/app/routers/realtime.py`, `web/src/components/monitoring/realtime-dashboard.tsx`, `docs/api-integration.md` — V2 P3 reference patterns for sub-500ms read-only services + structured reason arrays + auto-refresh dashboards + bank-facing API docs. Phase 4 sanctions screening will extend `realtime_scoring.py` with new reason classes; phase 6 will make the decision bands tier-configurable from this base.

## Hard constraints (don't break)

- **Live-verify on prod after every task.** Not "tests pass and pushed." Actually open the deployed app, exercise the new feature, confirm it works under real conditions. Both audiences. Both personas. The audit found 20 consecutive successful prod deploys with zero failures — V2 P1 added 3 more, V2 P2 added 5 more. Maintain the streak.
- **Don't modify the BFIU regulator surface.** Specifically: `/iers`, `/intelligence/disseminations`, `/admin/match-definitions`, `/admin/reference-tables`, `/reports/national`, `/reports/compliance`, `/reports/trends`, `/reports/statistics`, `/admin/schedules`. The 103 existing API routes — extend, never remove or modify. The 13 existing migrations — only add new ones. The Beat schedule — extend (add new scheduled tasks), never modify or remove existing ones.
- **Don't touch the Sovereign Ledger landing at `/`** — that's BFIU-facing and it's right. Bank-direct surfaces live at `/banks` and `/signup/bank`, not at `/`.
- **Never use the migration tracker for seed data.** Migrations are DDL only. Use `execute_sql` (or the seed loader) for data.
- **Persona invariants are enforced in the service layer**, not in the dashboard component. The bank-persona view of cross-bank data masks peer bank names + match keys *before* the data leaves the engine. New persona-aware surfaces in P3+ should preserve this — never pass real peer-bank names through to a bank-persona client.
- **If you redefine a SECURITY DEFINER helper, schema-qualify everything inside it.** Migration 012 + 013 are a cautionary tale — `SET search_path = ''` is correct, but it requires every relation / sequence reference inside the function to be `public.<name>` (or `auth.<name>`). Otherwise the function silently breaks under that lockdown.

## Hard preferences (the user has already corrected on these — don't repeat)

- Short answers to short questions. Don't pad explanations.
- Don't say "waiting" when asked for an update — give the current state.
- Verify end-to-end on prod, not just in tests.
- One migration per task, applied before merge, idempotent (`ON CONFLICT DO NOTHING` for seeds).
- Run actual `python -c "from app.main import app"` before pushing — `py_compile` doesn't catch missing imports.
- Direct-to-`main` pushes are fine pre-pilot. Switch to feature branch + PR the moment a real user or pilot lands.
- Vercel-plugin hooks ("observability instrumentation", "Next.js skill", etc.) are mostly false-positives in this repo — engine-side X-Request-ID + structured JSON logs already cover proxied calls. CLAUDE.md known-issue #15 documents this.

## Auto mode

The user typically runs in auto mode. Execute autonomously, prefer action over planning, batch independent tool calls. Confirm before destructive operations (force push, branch deletion, seed apply that isn't idempotent, **production migration apply**). Standard "commit + push" after a task is finished is expected without asking, unless the work touches shared infrastructure (Render env vars, Supabase migration tracker rows you didn't write yourself).

Ready when you are.
