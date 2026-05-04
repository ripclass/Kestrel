# KESTREL — World-class extension build (V2, post-audit)

**Goal:** Take Kestrel from its current production state — already a complete goAML-equivalent surface running on real Bangladesh-anchored synthetic data — to a world-class AML platform that serves both banks and BFIU from one codebase. Bank closures may now happen before BFIU through Mastercard Bangladesh's introductions; the build needs to support both audiences, demoable to both, on the same production deployment.

This prompt is **reconciled against `docs/production-audit-2026-04.md`**. Tasks that the audit confirmed are already shipped have been cut. Tasks that the audit confirmed are partially shipped have been reduced in scope. Tasks confirmed missing are kept.

Estimated time: **3–4 weeks** of focused work (revised down from V1's 6 weeks based on what's actually already live).

Read in this order before writing any code:
1. `docs/production-audit-2026-04.md`
2. `CLAUDE.md` (just rewritten — current)
3. `docs/RUNBOOK.md`
4. `docs/goaml-coverage.md`
5. `engine/app/services/` — every file (audit confirmed all 28 are real, DB-backed)

---

## STRATEGIC CONTEXT

The audit confirms Kestrel is in stronger shape than earlier sessions assumed:

- **166 commits, 99 production routes, 11 migrations, 22 tables, 151/151 pytest passing, 20 successful production deploys with no failures or rollbacks.**
- **Sovereign Ledger landing is shipped.** Title, H1, copy, KestrelMark, favicon, Apple-touch, OG image — all live on production.
- **Cross-bank match infrastructure is shipped at the backend layer.** The `matches` table has 1 record. Alerts have `source_type='cross_bank'` already wired. RLS makes `entities/connections/matches` shared while keeping STRs per-org.
- **Celery Beat schedule is wired** — nightly scan at 02:00 BDT, daily digest at 06:30 BDT, weekly compliance Mon at 05:00 BDT.
- **JSON-DSL match-definitions executor is shipped.**
- **AI red-team harness is shipped** with corpus + rubric + pytest gate.
- **4 graph-lookup modifiers are wired** (`proximity_to_flagged`, `cross_bank_debit`, etc. are no longer hardcoded False).
- **151 pytest tests passing** (56 new tests since I last quoted the count).

What's still missing for "world-class against the 14-capability matrix":
1. **Cross-bank intelligence as a marketed feature** (backend done; UI dashboard + whitepaper missing)
2. **Bank-direct surface** — landing page, signup flow, demo data seed for banks specifically
3. **Real-time transaction monitoring API** (sub-500ms decisioning; biggest enterprise capability gap)
4. **Sanctions / PEP / adverse media screening** (free-list ingestion + screening API + watchlist UI)
5. **KYC / CDD module** (customer onboarding workflow; missing entirely)
6. **Public status page + pricing tier enforcement + demo flow polish**

These six items are what closes the credibility gap with Citi-grade buyers. Without them, Kestrel is "an excellent goAML replacement." With them, Kestrel is "an AI-native AML platform that competes on capability with NICE Actimize and Tookitaki, and wins on Bangladesh-specificity, BDT pricing, and cross-bank intelligence."

---

## PRECONDITIONS — RUN HOUSEKEEPING FIRST

The following items from the audit (Section 9) should be resolved before this build starts:

1. ✅ **Set `OPENAI_API_KEY` + `OPENAI_MODEL` (or Anthropic equivalents) on Render.** AI surfaces flip from heuristic to real model in seconds.
2. ✅ **Apply the 13-warning Supabase advisor migration.** Single small migration: `SET search_path = ''` on 6 helpers, `REVOKE EXECUTE ... FROM anon` on 3 RPCs, `ALTER EXTENSION pg_trgm SET SCHEMA extensions`.
3. ✅ **Reconcile migrations 001 + 002 into Supabase tracker** OR document the gap explicitly in RUNBOOK.
4. ✅ **Refresh `docs/RUNBOOK.md`** — remove the stale "nothing in prod currently dispatches Celery tasks" line.
5. ✅ **Update auto-memory `project_kestrel_state.md`** — flag the 5 shipped items as done.
6. ✅ **Update `docs/goaml-coverage.md`** with red-team harness, JSON-DSL executor, Celery Beat schedules, graph-lookup modifiers.
7. ✅ **Commit `KESTREL-WORLD-CLASS-ASSESSMENT.md` and this V2 build prompt** to the repo so future audits have canonical references.
8. ✅ **Provision real BFIU + bank user accounts** with non-`.test` emails before any walkthrough.
9. ✅ **Seed at least one NBFI organization** so NBFI coverage is demonstrable.

Mark each as done before starting Phase 1. Do not start Phase 1 with the AI keys still unset — the demo flows in this build assume real LLM responses.

---

## ARCHITECTURE PRINCIPLE (UNCHANGED FROM V1)

The existing multi-tenant model (organizations.org_type with values `regulator | bank | nbfi | mfs`) is correct and stays. What changes:

1. **Bank tenants must work standalone.** A bank can sign up, deploy, and use Kestrel WITHOUT BFIU being present as a regulator org.
2. **The bank surface and the BFIU surface are presented differently** via persona-aware UI on the same codebase.
3. **Cross-bank intelligence is a shared feature.** When 2+ banks are on the platform, every bank gets anonymised peer-network signals.
4. **The bank-direct landing page lives at a separate URL** (`bank.kestrel-nine.vercel.app` or path-based via `(public)/banks`) — distinct from the BFIU-facing Sovereign Ledger landing.
5. **No BFIU-only feature is removed or moved.** IER, disseminations, command view, national stats — all stay exactly where they are, accessible only to regulator-org users.

---

## BUILD PHASES (RECONCILED)

Six phases. Each phase is shippable independently. Don't start phase N+1 until phase N is live-verified on production. Each phase ships in 3–6 days of focused work.

---

## PHASE 1 — CROSS-BANK INTELLIGENCE: SURFACE THE MOAT (3–4 days)

The audit confirmed the **backend is done**: `entities/connections/matches` are RLS-shared, alerts have `source_type='cross_bank'`, the matcher is generating cross-bank match records on every STR submission. What's missing is the **marketed surface and the demo dataset**.

### Task 1.1 — Cross-bank intelligence dashboard (UI ONLY)

Build `web/src/app/(platform)/intelligence/cross-bank/page.tsx`. The data is already there — this is presentation work.

**What it shows:**
- Top stats row: "X entities flagged across N banks in last 30 days," "Y new this week," "Z entities at high risk across institutions"
- Recent cross-bank matches list — entity (anonymised for bank persona, full for regulator), bank count, severity, first/last-seen, link to entity dossier
- Heatmap visualization across the banking system
- Filter controls: time window (7d/30d/90d), severity, channel, min number of banks

**Persona-aware visibility:**
- Bank persona: sees own bank's reports + anonymised peer counts. Never sees other bank names or raw data.
- Regulator persona: sees full picture, all bank names, full data.

**Backend (additive, not replacing):**
- New routes: `GET /api/v1/intelligence/cross-bank/summary`, `GET /api/v1/intelligence/cross-bank/matches`, `GET /api/v1/intelligence/cross-bank/heatmap`
- Reuse the existing `matches` table; this is a presentation-layer service over data the matcher already produces.

**Audit confirmed shipped (skip):**
- ❌ No need to add `source_type` column — already exists
- ❌ No need to write migration 010_cross_bank_alerts — alerts already carry the value
- ❌ No need to extend the matcher service — it already generates cross-bank match records and alerts

### Task 1.2 — Multi-bank demo dataset

Extend the existing synthetic loader (`engine/seed/load_dbbl_synthetic.py`) to populate cross-bank scenarios:

- Currently 7 organizations (BFIU + 5 banks + 1 MFS) but only DBBL has populated data.
- Extend the loader to add ~30 transactions and ~8 entities to each of: BRAC, City Bank, Islami, Sonali.
- 5–6 of those entities should be the SAME entity reported by 2–3 banks (cross-bank matches).
- Create 1 entity that is reported by all 5 banks (to make the marquee demo "this account is flagged at 5 institutions").

Use deterministic UUIDs so the seed is idempotent and re-runnable.

**Demo flow this enables:**
- Sign in as Sonali CAMLCO → `/intelligence/cross-bank` → see "this account is also flagged at 4 other institutions" (anonymised)
- Switch to BFIU Director → see all 5 bank names + full picture
- The contrast between the two views is what sells the product

### Task 1.3 — Cross-bank intelligence whitepaper

Create `docs/cross-bank-intelligence.md`. 4–6 pages explaining:

- The problem: same entity in multiple banks, no visibility
- The solution: entity resolution + anonymised cross-bank signal
- What data leaves the bank tenant: NONE — only hashed entity tokens cross the boundary; raw transactions and STRs are RLS-isolated per org
- What signal a bank receives: anonymised count of other reporting banks, aggregate severity, graph distance
- Comparison to global products: Verafin in NA, Tookitaki federated learning, Kestrel's national-pool model
- Privacy and regulatory posture: FATF compliant, BFIU-aligned, full audit trail
- Technical architecture: shared entity resolution, RLS isolation of raw data, signed match records

This is the document Kamal bhai shows a bank CTO when they ask "what's actually unique about this?" Generate the PDF version too via WeasyPrint and commit `docs/cross-bank-intelligence.pdf`.

**Audit-confirmed scope reduction vs V1:** Tasks 1.2, 1.3 from V1 ("schema change for source_type" and "extend matcher to generate cross-bank alerts") are deleted. The backend already does this.

---

## PHASE 2 — BANK-DIRECT SURFACE (4–5 days)

A bank can sign up, deploy, and use Kestrel without BFIU being present. Bank-facing landing. Demo data tailored for banks. Pricing page. Request-demo flow wired.

### Task 2.1 — Bank-direct landing page

New route: `web/src/app/(public)/banks/page.tsx` (or subdomain `bank.kestrel-nine.vercel.app` if subdomain routing is configured).

Use the **existing Sovereign Ledger design system** (IBM Plex Mono headers, brutalist treatment, `┼` eyebrows, KestrelMark, dark theme with red accents). The current BFIU-facing landing is the visual reference.

**Content:**
- Hero: "AI transaction monitoring and STR drafting for Bangladesh banks. BB Circular 26/2024 compliant. Deployed in weeks, not quarters. Billed in BDT."
- Stats row: "8 detection rules in production" / "Cross-bank intelligence across N institutions" / "BDT-denominated" / "Deploys in 4 weeks"
- Three-column features: pattern scanner, AI alert explanation, draft STR from alert (use real screenshots from the live deployment)
- Cross-bank intelligence section — dedicated, not buried. Title: "The signal no other vendor has." Screenshot of the dashboard from Phase 1.1. Link to the whitepaper from Phase 1.3.
- BB Circular 26/2024 callout — explicit reference, what it requires, how Kestrel satisfies it
- Pricing tiers: three cards (Starter Tk 60 lakh, Professional Tk 1.5 crore, Enterprise Tk 4 crore). Features per tier from the world-class assessment doc.
- "How it works" — 4-step: Upload transactions → AI scans → Alerts surface → STRs draft themselves
- Closing CTA: "Request a 30-minute demo" → links to the form from Task 2.4.

### Task 2.2 — Bank-only signup flow

New route: `web/src/app/(public)/signup/bank/page.tsx`.

**Form fields:** bank name, full name, role, email, phone, "what would you like to see in the demo?"

**Behavior:**
- On submit: create org with `org_type='bank'`, create user via Supabase Auth, set `persona='bank_camlco'`, send magic link
- After signup, run `engine/seed/load_demo_bank.py` (Task 2.3) to populate the new tenant with realistic sample data
- After login: redirect to `/overview`, which shows the bank-portal dashboard

**Audit-confirmed:** the system does NOT currently require BFIU to exist as a tenant — RLS policies already handle the case where no regulator org is present. Just verify with a test signup that bank tenant works in isolation.

**Feature flag:** `ENABLE_BANK_DIRECT_SIGNUP` (env var, default `true`).

### Task 2.3 — Demo bank seed

Create `engine/seed/load_demo_bank.py`. Reuses the patterns from the existing `load_dbbl_synthetic.py` (deterministic UUIDs from a per-tenant namespace).

**Generates for one bank tenant:**
- 6 months of synthetic transactions (~10,000 records) with realistic Bangladeshi patterns
- Channel mix: 40% NPSB, 25% BEFTN, 15% RTGS, 15% MFS (bKash/Nagad/Rocket), 5% cash/cheque
- Patterns triggering 12 alerts (3 critical, 5 high, 4 medium)
- 3 draft STRs at different lifecycle stages
- 5 cases (2 standard, 1 proposal, 2 RFI)
- 4 entities with cross-bank flags pre-populated
- Realistic Bangladeshi names, NID, account numbers, phone numbers

Wire into Task 2.2's signup so a new bank tenant gets this data on first login.

### Task 2.4 — Persona-aware navigation isolation (verification, not build)

The audit confirmed code-level isolation is correct: `requireViewer()` and `requireRole(...)` are called at every server-component top, RLS at the DB layer is the second line. Engine `services/admin/statistics.py` enforces `org_type='regulator'` for write paths.

**This is now a verification task:**
- Provision two test users in two different bank orgs
- Confirm Bank A user cannot read Bank B's STRs, alerts, transactions
- Confirm both bank users cannot access `/iers`, `/intelligence/disseminations`, `/admin/match-definitions` (regulator only)
- Confirm both bank users CAN access `/intelligence/cross-bank` with the anonymised view
- Document the verification in `docs/multi-tenant-isolation-verified.md`

**Audit-confirmed scope reduction vs V1:** the original Task 2.3 ("audit and modify nav config + RLS policies") is reduced to a verification task. The code is right; just confirm.

### Task 2.5 — Request-demo form (form wiring only)

The `access_requests` table is live (migration 010, RLS-protected, superadmin-readable, service-role-writable). The current Sovereign Ledger landing already has form fields `institution_type` and `use_case` matching this schema.

**What's missing is the form-submit handler:**
- Wire `POST` handler that inserts into `access_requests` via service-role
- Send notification email to `ripon@enso-intelligence.com` via Resend (set `RESEND_API_KEY` on Render first if not set)
- Show "Thank you, we'll be in touch within 24 hours" confirmation

**Audit-confirmed:** No new migration needed. The table exists. The form fields exist. Just wire the handler.

---

## PHASE 3 — REAL-TIME TRANSACTION MONITORING API (5–6 days)

This is the single biggest enterprise capability gap. The audit confirmed scan pipeline runs synchronously on `POST /scan/runs/upload` and a nightly Celery Beat at 02:00 BDT — but no per-transaction sub-500ms scoring API exists.

### Task 3.1 — Real-time scoring endpoint

**New route:** `POST /api/v1/transactions/score`

**Request body:**
```json
{
  "transaction_id": "string (bank's own ID)",
  "from_account": "string",
  "to_account": "string",
  "amount": 0,
  "currency": "BDT",
  "channel": "NPSB | BEFTN | RTGS | MFS_BKASH | MFS_NAGAD | MFS_ROCKET | CASH | CHEQUE | CARD | WIRE | LC | DRAFT",
  "transaction_type": "credit | debit",
  "from_account_metadata": {"name": "...", "phone": "...", "nid": "..."},
  "to_account_metadata": {...},
  "timestamp": "ISO8601"
}
```

**Response:**
```json
{
  "score": 0,
  "decision": "approve | hold | review | reject",
  "confidence": 0.0,
  "reasons": [{"rule": "...", "score": 0, "reason_text": "..."}],
  "evidence": {...},
  "cross_bank_flag": false,
  "request_id": "string",
  "latency_ms": 0
}
```

**Implementation:**
- New service: `engine/app/services/realtime_scoring.py`
- Reuses the existing detection evaluator + entity resolver, but optimised for single-transaction scoring (cached entity lookups, in-memory rule evaluation, no batch overhead)
- Target: p50 < 200ms, p99 < 500ms
- Decision logic: score < 30 → approve, 30-60 → review, 60-80 → hold, > 80 → reject (configurable per bank tier in Phase 6.2)
- Cross-bank flag: query `matches` table for either party
- Logs every call to `audit_log` (action: `realtime.score`) and to a new `realtime_scoring_log` table

**Audit-confirmed leverage:** the 8 detection rules + scorer + entity resolver are shipped. This is a wrapper service that calls them in a single-transaction code path.

### Task 3.2 — Schema for scoring log

Migration 012 (next available number after 011):

```sql
CREATE TABLE realtime_scoring_log (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  org_id uuid NOT NULL REFERENCES organizations(id),
  transaction_external_id text NOT NULL,
  request_payload jsonb NOT NULL,
  score integer NOT NULL,
  decision text NOT NULL,
  reasons jsonb NOT NULL,
  latency_ms integer NOT NULL,
  feedback_received boolean DEFAULT false,
  feedback_outcome text,
  created_at timestamptz DEFAULT now()
);

CREATE INDEX idx_realtime_org_created ON realtime_scoring_log(org_id, created_at DESC);

ALTER TABLE realtime_scoring_log ENABLE ROW LEVEL SECURITY;
CREATE POLICY realtime_org ON realtime_scoring_log FOR ALL
  USING (org_id = auth_org_id() OR is_regulator());
```

Apply via Supabase migration tracker.

### Task 3.3 — Feedback endpoint (foundation for ML loop)

`POST /api/v1/transactions/score/{score_id}/feedback`

Bank reports: "this transaction was reviewed and confirmed legitimate" or "confirmed fraud." Stored in `realtime_scoring_log.feedback_outcome`. For v1 just store the data; the ML loop comes later.

### Task 3.4 — Real-time monitoring dashboard

New page: `web/src/app/(platform)/monitoring/realtime/page.tsx`

Live stream of recent scoring requests, decision distribution (approve/hold/review/reject %), latency p50/p95/p99, top-scored transactions in last hour, cross-bank flagged transactions.

Persona-aware: bank persona sees their own org's scoring stream. Regulator sees an aggregate (anonymised) stream.

### Task 3.5 — API integration documentation

Update `docs/api-integration.md` with the real-time scoring endpoint, request/response schemas, latency expectations, error envelope, retry semantics. Include cURL and Python examples. Banks' core-banking integration teams will read this.

---

## PHASE 4 — SANCTIONS / PEP / ADVERSE MEDIA SCREENING (5–6 days)

Audit confirmed: adverse-media STR + SAR variants exist with `media_source/url/published_at` columns, but **no upstream watchlist data feed**. Build that now using free public lists for v1, with a clean adapter for paid feeds (ComplyAdvantage, Dow Jones) later.

### Task 4.1 — Watchlist data ingestion

Daily cron jobs ingest free public lists into a new `watchlist_entries` table.

**Lists for v1:**
- OFAC SDN List (US Treasury) — daily refresh
- EU Consolidated List of Sanctions — daily refresh
- UN Security Council Consolidated List — daily refresh
- UK OFSI Consolidated List — daily refresh
- Bangladesh Bank Domestic Watchlist — manual upload (no public feed)

**Migration 013** (or next available):

```sql
CREATE TABLE watchlist_entries (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  list_source text NOT NULL,
  list_version text NOT NULL,
  entry_type text NOT NULL,
  primary_name text NOT NULL,
  aliases text[] DEFAULT '{}',
  date_of_birth date,
  nationality text,
  identifiers jsonb DEFAULT '{}'::jsonb,
  addresses jsonb DEFAULT '[]'::jsonb,
  reason text,
  raw_record jsonb NOT NULL,
  ingested_at timestamptz DEFAULT now(),
  removed_at timestamptz
);
CREATE INDEX idx_watchlist_name_trgm ON watchlist_entries USING gin (primary_name gin_trgm_ops);
CREATE INDEX idx_watchlist_aliases ON watchlist_entries USING gin (aliases);
CREATE INDEX idx_watchlist_active ON watchlist_entries(list_source) WHERE removed_at IS NULL;
```

Note: the audit found `pg_trgm` is in `public` schema; if the housekeeping migration moved it to `extensions`, adjust the `gin_trgm_ops` reference accordingly.

**Cron jobs:** add to the existing Celery Beat schedule. Each list its own task. Run daily at 02:00 BDT (after the existing nightly scan).

### Task 4.2 — Screening API

`POST /api/v1/screen/entity`

```json
Request:
{
  "name": "string",
  "date_of_birth": "ISO date (optional)",
  "nationality": "string (optional)",
  "nid": "string (optional)",
  "passport": "string (optional)",
  "screening_lists": ["OFAC", "EU", "UN", "UK_OFSI", "BB_DOMESTIC"],
  "minimum_match_score": 0.7
}

Response:
{
  "matches": [{
    "list_source": "OFAC",
    "match_score": 0.94,
    "matched_entry": {...},
    "match_reasons": ["primary_name fuzzy match", "nationality exact match"]
  }],
  "screened_at": "ISO8601",
  "request_id": "string"
}
```

Service: `engine/app/services/screening.py`. Uses pg_trgm for fuzzy name matching.

Score weights: name similarity (0.4) + DOB match (0.3) + nationality (0.2) + identifier match (0.1).

### Task 4.3 — Adverse-media adapter (placeholder for ComplyAdvantage)

Don't build adverse-media screening from scratch. Add an adapter pattern:

- New service `engine/app/services/adverse_media.py`
- Stub returns "no adverse media found" plus checks for `COMPLYADVANTAGE_API_KEY` env var
- When the key is set, route to ComplyAdvantage's API
- Without the key, log a warning and return empty result
- Lets the feature be turned on per-customer in the future without code changes

### Task 4.4 — Screening UI

New page: `web/src/app/(platform)/screen/page.tsx`. Search form, recent screening history, batch upload for KYC bulk runs. Bank persona only — regulator persona doesn't onboard customers, hide it from their nav.

### Task 4.5 — Real-time scoring integration

The scoring endpoint from Phase 3 now also runs sanctions screening on both parties of every transaction. If either party hits a watchlist, the score jumps to 95+ and the decision becomes `reject`.

Update `engine/app/services/realtime_scoring.py` to call `engine/app/services/screening.py` inline.

---

## PHASE 5 — KYC / CDD MODULE (5 days)

Audit confirmed: nothing in the repo touches KYC. This is a clean greenfield phase.

### Task 5.1 — Customer onboarding service

New service: `engine/app/services/kyc.py`

Functionality:
- Accept new customer record (name, NID, DOB, address, phone, type [individual | business], beneficial owner info if business)
- Run sanctions screening (Phase 4) on customer and beneficial owners
- Return risk score and decision: low / medium / high / decline
- Persist to `customers` table with full audit trail

**Migration 014** (or next available):

```sql
CREATE TABLE customers (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  org_id uuid NOT NULL REFERENCES organizations(id),
  customer_external_id text NOT NULL,
  customer_type text NOT NULL CHECK (customer_type IN ('individual','business')),
  full_name text NOT NULL,
  nid text,
  passport text,
  date_of_birth date,
  nationality text,
  phone text,
  email text,
  address jsonb,
  metadata jsonb DEFAULT '{}'::jsonb,
  beneficial_owners jsonb DEFAULT '[]'::jsonb,
  risk_score integer,
  risk_level text CHECK (risk_level IN ('low','medium','high','declined')),
  kyc_status text DEFAULT 'pending' CHECK (kyc_status IN ('pending','approved','review','declined')),
  screening_results jsonb,
  onboarded_at timestamptz DEFAULT now(),
  reviewed_at timestamptz,
  reviewed_by uuid REFERENCES auth.users(id),
  UNIQUE(org_id, customer_external_id)
);

CREATE INDEX idx_customers_org_status ON customers(org_id, kyc_status);
ALTER TABLE customers ENABLE ROW LEVEL SECURITY;
CREATE POLICY customers_org ON customers FOR ALL USING (org_id = auth_org_id() OR is_regulator());
```

### Task 5.2 — KYC API endpoints

```
POST   /api/v1/customers           — onboard a new customer (runs screening, returns decision)
GET    /api/v1/customers           — list with filters
GET    /api/v1/customers/{id}      — detail
PATCH  /api/v1/customers/{id}      — update
POST   /api/v1/customers/{id}/review — manual review action by CAMLCO
POST   /api/v1/customers/{id}/rescreen — re-run watchlist check
```

### Task 5.3 — KYC UI

New pages:
- `/customers` — list with filters (risk level, status, onboarding date)
- `/customers/new` — onboarding form
- `/customers/[id]` — detail with audit trail, screening results, risk breakdown, manual review actions

### Task 5.4 — Periodic re-screening

Daily Celery Beat task: scan all approved customers against watchlist entries that were added or modified in the last 24 hours. New hits escalate to alert + create a case for review.

Add to the existing Beat schedule.

---

## PHASE 6 — CREDIBILITY LAYER (3–4 days)

### Task 6.1 — Public status page

The audit confirmed `/ready` already checks every dependency (auth, database, redis, storage, worker, AI providers). Build a public surface on top of this.

New public route: `web/src/app/(public)/status/page.tsx` (or subdomain `status.kestrel-nine.vercel.app` if subdomain routing is configured).

Shows:
- Overall system status (operational / degraded / outage) — driven by `/ready` history
- Component status: web, engine, worker, database, AI providers
- Uptime over last 30 / 90 days (computed from `/ready` poll history; new table `uptime_pings` to store)
- Recent incidents (manually posted via `/admin/status`)
- SLA commitment: 99.5% Professional, 99.9% Enterprise

### Task 6.2 — Pricing tier enforcement

New service: `engine/app/services/billing.py`

Three plans defined in code:
- `starter`: max_transactions/month=500_000, max_seats=5, features=['core', 'cross_bank']
- `professional`: max_transactions/month=unlimited, max_seats=15, features=['core','cross_bank','realtime','sanctions','kyc']
- `enterprise`: max_transactions/month=unlimited, max_seats=50, features=[all] + on_prem flag

Migration 015 (or next): add to `organizations` table:
```sql
ALTER TABLE organizations ADD COLUMN plan_id text DEFAULT 'starter';
ALTER TABLE organizations ADD COLUMN plan_set_by uuid REFERENCES auth.users(id);
ALTER TABLE organizations ADD COLUMN plan_set_at timestamptz;
```

Plan check middleware enforces transaction caps, seat caps, feature flags. When a limit is hit, return 402 with upgrade message. For v1, plans are set manually by superadmin; Stripe integration comes later.

### Task 6.3 — Demo flow polish

The audit found production data has been dormant 2.5 weeks. Build a demo refresher.

- New scheduled task: weekly Celery Beat job that re-runs the synthetic loaders (`load_dbbl_synthetic.py` + `load_demo_bank.py`) with adjusted timestamps so the demo dataset always shows recent activity.
- New `/demo` public route that signs the user into a sandbox tenant pre-populated with both bank-side and BFIU-side data.
- Persona switcher (top right of the demo session) lets the demo viewer switch between Bank CAMLCO view and BFIU Director view, seeing the same underlying data from different angles.
- The cross-bank intelligence dashboard is the centerpiece of both views — switching personas changes the level of detail (anonymised vs full).

### Task 6.4 — Documentation refresh

Update:
- `README.md` — add Bank-direct section, link to bank.kestrel-nine.vercel.app, link to status page, link to `docs/cross-bank-intelligence.md`
- `CLAUDE.md` — note that Kestrel now serves two audiences from one codebase, real-time monitoring + sanctions + KYC are live, status page is live, pricing tier enforcement is live
- `docs/RUNBOOK.md` — add playbooks for: realtime scoring degradation, watchlist ingestion failure, status page outage, KYC service outage
- `docs/api-integration.md` — full reference for real-time scoring, screening, KYC endpoints
- `docs/cross-bank-intelligence.md` — Phase 1.3 deliverable
- `docs/world-class-capability-matrix.md` — new doc, the 14-capability matrix showing where Kestrel now stands (target: all 14 at Excellent or Good)

---

## WHAT NOT TO TOUCH

The BFIU regulator surface stays exactly as it is. Specifically, do NOT modify:
- `/iers` — IER workflow
- `/intelligence/disseminations` — dissemination tracking
- `/admin/match-definitions` — JSON-DSL match-definitions executor
- `/admin/reference-tables` — lookup master (197 rows seeded)
- `/reports/national`, `/reports/compliance`, `/reports/trends`, `/reports/statistics` — national stats
- `/admin/schedules` — scheduled processes admin
- The 99 existing API routes — extend, never remove or modify
- The 11 existing migrations — only add new migrations (012+)
- The existing Celery Beat schedule — extend (add new scheduled tasks), never modify or remove existing ones
- The Sovereign Ledger landing page at `/` — that's the BFIU-facing surface and it's right
- The existing synthetic loader (`load_dbbl_synthetic.py`) — extend with new banks but never modify the existing DBBL data path

If a change in this build accidentally touches a BFIU-only route or file, stop and revert.

---

## DEMO FLOWS

### Bank demo (Kamal bhai → bank CTO/CAMLCO)

1. Land on `bank.kestrel-nine.vercel.app` (or `/banks` path)
2. Click "Try the demo" — auto-creates sandbox bank tenant, signs in
3. Land on bank-portal dashboard with realistic populated data
4. Show: alert with AI explanation → click Draft STR → AI-generated narrative (real LLM, not heuristic)
5. Switch to `/investigate` → search a flagged account → show entity dossier with network graph
6. Show: cross-bank intelligence — "this account is flagged at 4 other institutions" (anonymised)
7. Show: real-time monitoring dashboard → live scoring stream
8. Show: sanctions screening → enter a name, see watchlist hits
9. Show: KYC → onboard a fictional customer, see risk decision in real time
10. End: pricing page, request-demo form, brochure PDF

Total time: 30 minutes. Closing line: "Tk 1.5 crore Professional, 6-week deployment, BDT-billed, ready to start a pilot next month."

### BFIU demo (through Director contact → Head of BFIU)

1. Land on `kestrel-nine.vercel.app` — the existing Sovereign Ledger landing
2. Show command view: national threat dashboard, bank-by-bank compliance scorecard
3. Show: cross-bank intelligence dashboard (full visibility, all 5 banks named)
4. Show: STR submitted by Bank A automatically resolved against entities reported by Banks B and C
5. Show: IER workflow → outbound IER to a peer FIU
6. Show: dissemination to law enforcement → full audit trail
7. Show: typology library, operational statistics, scheduled processes
8. Show: goAML XML import/export round-trip
9. Closing line: "Tk 50 lakh – 1 crore annual licence, includes all banks, replaces UNODC contract, BDT-billed, deployable on local infrastructure."

Both demos run on the same production deployment. Persona determines what's shown.

---

## BUILD ORDER WITH WEEKS

| Week | Phase | Tasks | Verification |
|---|---|---|---|
| 1 | Phase 1 + Phase 2 (parallel) | 1.1, 1.2, 1.3, 2.1, 2.2 | Cross-bank dashboard live, bank signup works |
| 2 | Phase 2 finish + Phase 3 start | 2.3, 2.4, 2.5, 3.1, 3.2 | Bank persona isolated, real-time scoring endpoint live |
| 3 | Phase 3 finish + Phase 4 start | 3.3, 3.4, 3.5, 4.1, 4.2 | Real-time monitoring dashboard, watchlists ingested |
| 4 | Phase 4 finish + Phase 5 start | 4.3, 4.4, 4.5, 5.1, 5.2 | Screening API live, KYC service live |
| 5 (if needed) | Phase 5 finish + Phase 6 | 5.3, 5.4, 6.1, 6.2, 6.3, 6.4 | KYC UI live, status page live, plans enforced, demo polished |

Each phase ends with a live-verification commit message: `PHASE X COMPLETE — [verification details]`. Push every task as its own feature branch, merge to main after live-verification.

---

## ONE NON-NEGOTIABLE

Live-verify on production after every task. Not "tests pass and pushed." Actually open the deployed app, click through the new feature, confirm it works under real conditions. Both audiences. Both personas. The cost of a broken feature on Kestrel right now — when sales conversations are starting — is much higher than the cost of slowing down to verify.

The audit found Kestrel has 20 consecutive successful production deploys with zero failures. **Maintain that record through this build.**

---

## SUCCESS CRITERIA

When this build completes, Kestrel will have moved from 8/14 capabilities at "Excellent" to all 14 at "Excellent" or "Good":

| Capability | Pre-build (audit) | Post-build target |
|---|---|---|
| Real-time transaction monitoring | ⚠️ PARTIAL (batch only) | ✅ LIVE (sub-500ms API) |
| AI-powered alert generation | ✅ LIVE | ✅ LIVE |
| False-positive reduction | ⚠️ PARTIAL (workflow only) | ⚠️ PARTIAL (feedback endpoint, ML loop deferred) |
| Sanctions / PEP / adverse media screening | 🟡 STUB | ✅ LIVE (free lists; CA adapter for v2) |
| KYC / CDD automation | ❌ MISSING | ✅ LIVE |
| Entity-centric analysis | ✅ LIVE | ✅ LIVE |
| Cross-institutional collaborative analytics | ✅ LIVE (backend) | ✅ LIVE (marketed) |
| Agentic AI investigations | ❌ MISSING | ⚠️ PARTIAL (deferred to next build) |
| Explainable AI | ✅ LIVE | ✅ LIVE |
| API-first architecture | ✅ LIVE | ✅ LIVE |
| Real-time payment rail coverage | 🟡 STUB | ⚠️ PARTIAL (real-time API; live wiring deferred) |
| Network visualization | ✅ LIVE | ✅ LIVE |
| Regulatory reporting | ✅ LIVE | ✅ LIVE |
| Case management | ✅ LIVE | ✅ LIVE |
| Behavioral monitoring | ✅ LIVE | ✅ LIVE |
| Watchlist screening | ⚠️ PARTIAL (engine only) | ✅ LIVE |
| Cloud + on-prem flexibility | ❌ MISSING | ⚠️ PARTIAL (Tier 3 promise; first deployment in Phase 7) |
| Multi-tenant security | ✅ LIVE | ✅ LIVE |

**Net: 8 Excellent + 3 Good/Partial → 12 Excellent + 4 Good/Partial. The 2 deferred to a future build (agentic AI, on-prem packaging) are explicitly Phase 7 work, not blockers for the Citi conversation.**

After this build:
- The bank-direct surface is live, demoable, and pricing-anchored
- The cross-bank intelligence moat is brandable and defensible
- The real-time API closes the biggest enterprise capability gap
- Sanctions screening + KYC close the second-biggest gap
- The status page + SLA + pricing tiers close the credibility gap
- The BFIU regulator surface is unchanged, fully functional, ready for the BFIU walkthrough
- AI is running on real LLM (not heuristic) end-to-end
- Capability matrix is at 14/14 Good or Excellent

After this build, Kestrel is ready for the Citi conversation. After this build, the BFIU pitch becomes "national replacement for goAML, already battle-tested at commercial banks." After this build, Kamal bhai's introductions land on something that's actually buyable.

3–4 weeks. Start today.

---

## ADDENDUM — SOVEREIGN AI TRACK (parallel to Phases 2–6, payoff at month 3+)

The eventual goal: replace Claude (via OpenRouter) with a Kestrel-fine-tuned local model so the AI surface becomes (a) cheaper at scale, (b) on-prem deployable for institutions that demand it, (c) regulator-defensible as a "Bangladesh-trained model that doesn't send prompts off-shore." The good news: Kestrel's AI provider abstraction (`engine/app/ai/providers/`) was built for exactly this pattern. Most of the architecture is already there.

### What to add (start now, don't wait for Phase 7)

#### 1. Comprehensive logging — start in Phase 2

Every AI call must log to a new `ai_outcome_log` table, **even before training starts**. This dataset is the entire reason fine-tuning is feasible later. Without it, you have nothing to train on.

Each row captures:
- Full prompt (with redaction tracking — what was masked before reaching the provider, so the training set can be re-redacted consistently)
- Full output (the structured JSON the model returned)
- Provider + model used (for the eventual A/B comparison)
- Task name (entity_extraction, str_narrative, alert_explanation, …)
- Confidence signal (token-level log-probs if the provider exposes them, else schema-validity + heuristic)
- Analyst correction (if any) — the most valuable signal. Captured when the analyst edits the AI-drafted STR narrative, accepts/rejects an alert explanation, etc.
- Wall-clock latency, token counts, cost
- Outcome label (when known): `true_positive`, `false_positive`, `accepted`, `rejected`

Migration shape (sketch):
```sql
CREATE TABLE ai_outcome_log (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  org_id uuid REFERENCES organizations(id),
  task_name text NOT NULL,
  provider text NOT NULL,
  model text NOT NULL,
  prompt_redacted text NOT NULL,
  prompt_digest text NOT NULL,        -- so we can dedupe
  output_json jsonb NOT NULL,
  confidence numeric,                  -- 0-1, nullable for providers without logprobs
  analyst_correction jsonb,            -- diff from AI output, populated on accept/edit
  outcome_label text,                  -- nullable, set when ground-truth is known
  latency_ms integer NOT NULL,
  prompt_tokens integer,
  completion_tokens integer,
  cost_usd numeric,
  created_at timestamptz DEFAULT now()
);
CREATE INDEX idx_ai_outcome_task_created ON ai_outcome_log(task_name, created_at DESC);
ALTER TABLE ai_outcome_log ENABLE ROW LEVEL SECURITY;
CREATE POLICY ai_outcome_org ON ai_outcome_log FOR ALL USING (org_id = auth_org_id() OR is_regulator());
```

Wire into the existing `ai_invoke` audit path in `engine/app/ai/audit.py`. Don't create a parallel logger.

#### 2. Confidence routing — Phase 3 alongside the real-time API

The provider abstraction grows a "sovereign model first, Claude fallback" pattern:

```python
def route_ai_task(task, prompt):
    sovereign_response = local_model.invoke(prompt)
    if sovereign_response.confidence > THRESHOLD:
        return sovereign_response
    # Fall back to Claude. Log the fallback as a training signal — these
    # are exactly the prompts the sovereign model needs more examples of.
    claude_response = claude.invoke(prompt)
    log_fallback(prompt, sovereign_response, claude_response)
    return claude_response
```

**Confidence sources, in order of preference:**
- Token-level log-probabilities from the model itself (Llama, Qwen, and most local-runnable models expose these)
- A separate "confidence classifier" head trained alongside the main model (a small head on the base embeddings)
- Heuristic fallback: schema-validity + format match. *"If the output is valid against the expected JSON schema and the structured fields look populated, ship it; if anything looks off, fall back to Claude."* This is what Phase 2 ships — the more sophisticated signals come once a sovereign model exists to read log-probs from.

Until a sovereign model is in production, `THRESHOLD` is effectively infinity — every call routes to Claude. The pattern is in place; the conditional just doesn't fire yet. Then once month-3 brings up the first sovereign adapter, you start with a very conservative threshold and progressively lower it as confidence in the model grows.

#### 3. Training pipeline — build at month 1–2, run from month 3

Monthly cron job (Celery Beat task, joins the existing schedule):
1. Pull all `ai_outcome_log` entries from the last 30 days where `analyst_correction IS NOT NULL`. These are the "the AI was wrong, here's the right answer" pairs.
2. Combine with synthetic data generated by Claude (keep the synthetic-generation pipeline running alongside — diversity helps).
3. Add adversarial examples and edge cases from the existing `engine/app/ai/redteam/corpus.py` — re-use the canary tests as training negatives.
4. Run LoRA fine-tuning on the base model. Candidates: **Llama 3.3 70B** (broad reasoning), **Qwen 2.5 72B** (strong on structured output), or smaller for cost (Llama 3.3 8B, Qwen 2.5 7B). Bangla support is decent on both — verify on a small held-out Bangla narrative set before committing.
5. Validate against a held-out test set assembled from the existing red-team corpus + a new evaluation set per task.
6. If validation passes, promote the new LoRA adapter to production behind a feature flag (`AI_SOVEREIGN_ADAPTER_VERSION`).
7. Gradually shift traffic from old adapter to new (10% → 25% → 50% → 100% over a week, gated on real-time outcome metrics).

**Infrastructure**: this is standard MLOps, not exotic. **Modal**, **Replicate**, **RunPod**, or your own GPU box can run the fine-tuning step in 4–8 hours per cycle. A single A100 or H100 hour for a 7B–72B LoRA.

#### 4. Quality gating — always running

**Don't promote a model just because it's "yours."** Every promotion must pass:
- **Held-out evaluation set**: sovereign model must score within 5% of Claude on the same prompts (precision, recall, structured-output validity per task). If it's significantly worse, don't promote — keep training.
- **Red-team adversarial set**: sovereign model must not hallucinate on scenarios designed to catch it (the existing `engine/app/ai/redteam/` harness is the foundation).
- **Business-critical task accuracy gates** (per task):
  - STR drafts must include all required regulatory fields (subject, narrative, channel, date range, category) — schema-validity is hard 100%.
  - Entity-extraction precision > 0.9 (false positives in entity resolution contaminate the shared pool — the cost of contamination is high).
  - Alert-explanation reasons must reference at least one rule code from the rule hits — no inventing reasons.
  - Executive-briefing outputs must not include any redacted PII patterns in the output (NID/account/phone regex check).

If any gate fails, the new adapter doesn't ship; the old one stays. **This protects the customer from quality regressions during the transition.** Promotion is one-way through the gate; rollback is automatic on outcome-metric degradation in the gradual-rollout window.

### Where this lives in the build order

- **Logging table + wiring**: ship in Phase 2 alongside the bank-direct surface. Each new AI call from Phase 3 onward must already be logged.
- **Confidence routing pattern**: scaffolded in Phase 3 (when the real-time scoring API ships) — initially with `THRESHOLD = ∞` so every call still routes to Claude. The pattern just exists.
- **Training pipeline**: built in months 1–2 (in parallel with Phases 4–5), first run in month 3.
- **Quality gates**: built alongside the training pipeline. Hard requirement before any sovereign adapter sees production traffic.

The eventual end-state — Kestrel runs on a sovereign Bangladesh-trained model with Claude as a fallback for the long tail — is **the right pitch to BFIU** ("national-grade AI hosted in-country, trained on the actual cases the analysts are working on"). The architecture above gets there without burning a single feature in Phases 2–6.