# Delta D2 — Bank CAMLCO walkthrough

**Purpose**: What the **bank CAMLCO** persona sees *differently* from the Director walk (Tutorials 01–30). Designed as a side-by-side reference for bank-side procurement reviews + live demos.

**Persona under examination**: `bank_camlco` × `manager` × `professional` plan
**Live demo credentials**:
- **Sonali Bank**: `camlco@kestrel-sonali.test` / `Kestrel!Sonali!2026` · Mahmudul Karim
- **City Bank**: `camlco@kestrel-city.test` / `Kestrel!City!2026` · Nashid Karim

**Reading time**: ~12 minutes
**How to use this**: Read the Director walk first (or skim the README) so you know what *exists*. This document covers what's **different** for bank-side users.

---

## TL;DR for bank-side procurement

A bank CAMLCO on Kestrel sees:

- **Their own bank's data** — own STRs, own alerts, own cases, own customers, own AI calls.
- **The cross-bank intelligence layer** — with peer bank names hidden ("Peer institution N") and match keys redacted to last 4 chars (`····5001`).
- **Bank-specific surfaces** the Director doesn't have — `Scan` and `Customers` only appear for bank persona.
- **Read-only access** to system-level tabs the Director writes to (Reference tables, Rules, Match definitions visible but enforcement-gated at the API).

Bank CAMLCO **does NOT see**:
- Other banks' STRs, alerts, cases, customers — RLS-blocked.
- The National command view (BFIU lens).
- The Trends + Statistics dashboards (regulator-only by procurement design).
- The Admin Schedules + Status tabs (BFIU operates the platform; bank doesn't see those).
- Full identifiers of cross-bank-flagged subjects belonging to other banks.

This is enforced by **four layers**: Next.js middleware → engine route auth deps → service-layer org-type guards → Postgres RLS. Documented procurement-grade in `docs/multi-tenant-isolation-verified.md`.

---

## 1 · Sidebar — what changes

The single biggest visible difference. The nav-config (`web/src/components/shell/nav-config.ts`) gates per-item with `personas` and `roles`. Here's the diff for `bank_camlco × manager`:

### Items GAINED vs Director

| Tab | Why CAMLCO sees it |
|---|---|
| **Operations → Scan** | Bank uploads CSV/XLSX transaction batches to seed alerts. Director doesn't — regulator doesn't ingest transactions. |
| **Operations → Customers** | KYC / CDD onboarding. Director persona never onboards customers (V2 P5 spec — *"regulator doesn't onboard customers"*). |

### Items LOST vs Director

| Tab | Why CAMLCO doesn't see it |
|---|---|
| **Command → National** | BFIU command lens — `personas: ["bfiu_director", "bfiu_analyst"]` only. |
| **Command → Trends** | National time-series — `personas: ["bfiu_director"]` only. Strategic data. |
| **Command → Statistics** | Operational statistics across reporting orgs — `personas: ["bfiu_director", "bfiu_analyst"]`. |
| **Admin → Schedules** | Beat-task admin — `roles: ["admin", "superadmin"]`. Manager role doesn't qualify. |
| **Admin → Status** | Public-status incident posting — `["admin", "superadmin"]` × `["bfiu_director", "bfiu_analyst"]`. Two gates; bank fails both. |

### Items SAME for both

The 21 remaining items are visible to both Director and CAMLCO, but **what they show is filtered by RLS** — same nav, different data.

### Sidebar summary

| Bucket | Director count | CAMLCO count |
|---|---|---|
| Overview | 1 | 1 |
| Intelligence Tools | 9 | 9 |
| Operations | 7 | 9 (+ Scan, + Customers) |
| Command | 5 | 2 (Compliance, Export — loses National, Trends, Statistics) |
| Admin | 8 | 6 (loses Schedules, Status) |
| **Total** | **30** | **27** |

---

## 2 · Overview — Bank command view

URL: `/overview` (same as Director).

The dashboard switches from "National command view" to **"BankView"** — same sections (live wire, command summary, stat tiles, channel strip, threat heatmap, bank compliance posture) but **all data is own-bank scoped**.

### Key visible deltas

- **Hero copy** changes to position the bank's lens.
- **Live wire · Alerts** column shows own-bank alerts only.
- **Cross-bank wire** column shows clusters the bank's org participates in, with the identifier redacted to last 4 chars (`····5001`).
- **National command summary** → reframed as "Own portfolio summary."
- **Stat tiles**: own-bank cluster count, own peer-lag self-assessment, own evaluation packs.
- **Bank compliance posture** card shows **own bank** in detail + neutral peer ranges. Other banks' detailed scores hidden.

The Director's "Attention needed: bKash Limited 42" tile does NOT appear for CAMLCO — that's a regulator-level call.

---

## 3 · Investigate / Catalogue / Entities / New subject

URLs unchanged.

### What's the same

- Universal search returns the same shared-pool results (the `entities`, `connections`, `matches` tables are explicitly RLS-shared so banks can see the cross-bank intelligence pool).
- The Catalogue 12-tile grid is identical.
- The entity dossier (Tutorial 02 Part B) renders the same sections.

### What's different

- **Entity dossier — Reporting history table**: own-bank rows by name; other banks' rows show as *"Peer institution N"*. The bank can act on their own filings; cannot read peer narratives.
- **Two-hop graph**: same data, but when a connected node belongs to another bank, the node label is anonymised.
- **New subject form**: subjects created here attribute to the CAMLCO's org. RLS ensures other banks cannot read until cross-bank matching links them via the shared `entities` row.

---

## 4 · Cross-bank intelligence — the anonymisation surface

URL: `/intelligence/cross-bank` (same as Director).

**This is the surface where the persona-aware enforcement is most visible.** Show this to bank-side procurement and they immediately see the FATF Recommendation 9 (Tipping-Off) compliance.

### Director vs CAMLCO side-by-side

| Section | Director sees | CAMLCO sees |
|---|---|---|
| **Header eyebrow** | `┼ Filters · Regulator view` | `┼ Filters · Bank view` |
| **Stats tiles** | National counts across all 6 banks | Own-bank participation + system aggregate context |
| **Heatmap** | Each bank named (BRAC, City, DBBL, Sonali, Islami) | Own bank by name; peers as *"Peer institution 1, 2, 3, 4, 5"* |
| **Recent matches** | Full identifier (`+8801711555001`) | Redacted (`····5001`) |
| **Top entities** | Full identifier | Redacted (`····5001`) |

### How the redaction works in code

`engine/app/services/cross_bank.py`:

- `_label_orgs_for_user(user, org_names)` — for bank persona, replaces each non-own-bank name with `Peer institution N` (deterministic per render).
- `_anonymize_match_key(user, key)` — for bank persona, returns `····` + last 4 chars; for regulator, returns the key unchanged.

These run in the **service layer**, not the JavaScript. The bank persona literally never receives the unredacted data over the wire. Open DevTools and inspect the network response — same redaction in the JSON.

### Tested by

`engine/tests/test_cross_bank.py` — 8 pure-helper tests covering persona invariants. CI enforces.

---

## 5 · Matches

URL: `/intelligence/matches`.

Same dataset as Cross-bank dashboard's "Recent matches" panel. CAMLCO sees:
- Match clusters their org participates in.
- Anonymised peer-bank names + redacted identifier.
- Same row-click → entity dossier path.

If a cluster doesn't touch the CAMLCO's bank, **the row doesn't appear in their list**. RLS-bounded.

---

## 6 · Alerts

URL: `/alerts`.

**Strictly own-bank**. RLS policy on `alerts` is `auth_org_id() = org_id OR is_regulator()`. Bank persona is not regulator → sees only their own rows.

### Per-alert workspace deltas

- AI explanation still generates (the AI sees the cross-bank context but doesn't surface peer specifics in the natural-language output).
- Rule trace shows own-bank evidence.
- Network graph mini-preview anonymises peer-side nodes.
- Disposition actions (Tutorial 13 § B.1 — 6 buttons) all work identically.

The CAMLCO can dispose, escalate, promote-to-case exactly like the Director, but only on own-bank alerts.

---

## 7 · STRs

URL: `/strs`.

Own-bank scoped. RLS on `str_reports`. CAMLCO sees:
- Own bank's drafts, submitted, confirmed, closed STRs.
- The 11 report-type filter pills (same 11 variants).
- Native-draft form (same 9 fields).
- goAML XML import (own-bank scoped).
- Excel export — own bank only.

This is the surface a bank CAMLCO **spends most of their day on**.

### Key bank-side note

The submit action moves an STR from `draft → submitted`. After that, BFIU sees it (regulator RLS lets them read all `submitted+` STRs). The bank cannot un-submit; they can supplement via the `Addl. Info` variant.

---

## 8 · Cases

URL: `/cases`.

Own-bank scoped. CAMLCO sees:
- Own bank's cases across all 8 variants (Standard / Proposal / RFI / Operation / Project / Escalated / Complaint / Adverse Media).
- The variant pill filter.
- Per-case workspace identical in shape; data scoped.

### Proposals — the bank ↔ BFIU coordination surface

When a bank submits a case with `variant=proposal`, BFIU sees it on their proposals kanban. The bank sees their submitted proposals + BFIU's decisions when returned. **This is where bank-regulator coordination on cross-bank patterns happens** — and Sonali / City CAMLCOs will care about this for their commercial-tier pitch.

### Case PDF export

CAMLCO can generate own-bank case PDFs. The PDF includes own-bank evidence + cross-bank cluster reference (with anonymised peer names) for evidentiary use.

---

## 9 · Disseminations

URL: `/intelligence/disseminations`.

### Critical difference for banks

A bank **cannot disseminate to law enforcement** — that's BFIU's statutory authority under MLPA § 24(3). The form is visible but submitting an LE dissemination as bank persona fails the server-side `is_regulator()` check.

### What CAMLCO CAN do here

- **Receive inbound disseminations from BFIU** — when BFIU disseminates findings back to the bank.
- **Submit Circular 22 bank-to-bank exchanges** — checking the "Circular 22" toggle on the form. This is legal: MLPA § 23(1)(d) enables it.

### Surface behavior

The CAMLCO's view of the dissemination ledger is filtered to:
- Inbound disseminations addressed to their bank.
- Their own Circular 22 outbound exchanges.

LE-bound disseminations sent by BFIU to other banks are **not visible**.

---

## 10 · Exchange (IERs)

URL: `/iers`.

Bidirectional bank-side use:
- **Outbound** — bank requests information from another bank under Circular 22 + MLPA § 23(1)(d). Or from BFIU directly.
- **Inbound** — bank receives an IER from BFIU or a peer bank; responds.

The form's "Counterparty FIU" field becomes "Counterparty bank" in bank-persona use. Egmont reference field is blank for domestic exchanges.

**Most useful surface** for inter-bank coordination on shared customers. Particularly important for the Sonali/City demos — show them how they request information about a shared customer from another bank within Kestrel, with full audit trail.

---

## 11 · Scan (bank-only)

URL: `/scan` — **only visible to bank persona** per nav-config (`personas: ["bank_camlco"]`).

### What it does

The bank uploads CSV/XLSX transaction batches → Kestrel runs the detection engine inline → alerts get generated → CAMLCO triages on `/alerts`.

### When it's used

- **Initial onboarding** — first historical batch upload.
- **Periodic enrichment** — when the bank's API integration isn't real-time yet.
- **Manual ad-hoc** — investigating a specific suspicious pattern.

Director doesn't see this because BFIU doesn't ingest transactions — they consume what banks scan and report on.

---

## 12 · Real-time

URL: `/monitoring/realtime`.

Same hero + same 4-stat structure. **Bank persona view is scoped to own-bank traffic** — the "system aggregate" view is regulator-only.

When the bank's core-banking integration starts calling `POST /transactions/score`, this dashboard fills with that bank's traffic. Empty today; full once Sonali / City wire their core systems to Kestrel.

### CAMLCO's primary use

Daily 09:00 BDT pass:
- Yesterday's call volume + p99 latency.
- Reject rate — should be < 1%.
- Recent stream — scan for unexpected REJECTs.
- Latency creep — alert ops if p99 starts climbing toward 500 ms.

---

## 13 · Screening

URL: `/screen`.

Identical surface for Director and CAMLCO. The watchlist pool is global (RLS = `SELECT for any authed`), so both personas see the same 22+ entries.

### CAMLCO daily flow

- KYC ad-hoc check — pre-onboarding.
- Counterparty review — before large outbound payments.
- Adverse-media flag — after a press story names a customer.

### What's hidden

Nothing on this surface. Watchlist is shared infrastructure.

---

## 14 · Customers (KYC) — bank-only

URL: `/customers` — **only visible to bank persona** per nav-config.

### What it shows

Own-bank customers + the KYC status + last-rescreen timestamp. The 13 Sonali customers seeded on prod will be visible when the CAMLCO logs in.

### What CAMLCO does here

- **Onboard new customer** — primary surface for KYC daily ops.
- **Process review queue** — filter `REVIEW`, work through each pending decision.
- **Handle re-screen alerts** — Beat task fires; CAMLCO investigates next morning.

### What the Director DOES see here (read-only)

When the Director navigates directly to `/customers`, the nav doesn't show the link but the page loads if URL is entered. The Director sees customers across **all banks** (system-wide read), but **cannot onboard** (the "Onboard customer" button is hidden).

---

## 15 · Reports — Compliance + Export

The two Command tabs CAMLCO retains.

### Compliance

URL: `/reports/compliance`. CAMLCO sees:
- **Own bank's row in full** — Timeliness × Conversion × Coverage + composite score.
- **Anonymised peer ranges** — *"Peer institution 1: 78"* etc., so the bank can see where they rank without seeing other specific banks.
- **Own bank's trend** (when populated) — quarter-over-quarter movement.

This is **the page that motivates a CAMLCO's daily work** — their score is their accountability.

### Export

URL: `/reports/export`. CAMLCO can generate:
- Own-bank STR XLSX archives.
- Own-bank goAML XML batch export.
- Per-bank compliance scorecard for the bank's internal audit.

National briefing pack option is hidden — that's BFIU only.

---

## 16 · Admin — what CAMLCO can touch

The 6 admin tabs CAMLCO retains:

### Settings (Settings/Org)

Org profile, plan tier visibility, demo mode flag (when applicable). Read-only on most fields; mutable on `designation` + display preferences.

### Team

**This is where the CAMLCO manages their bank's staff** — adding new analysts, promoting case officers, etc. Same Team page (Tutorial 23) but scoped to own org. RLS on `profiles` blocks cross-org reads.

CAMLCO with `role=manager` can edit other staff's roles but **cannot escalate to superadmin** (server-enforced).

### Rules

Bank-side tuning of the 17 system rules. CAMLCO can:
- Override weights for their bank's risk profile.
- Toggle rules off for known-irrelevant patterns.
- Add description overrides explaining bank-specific tuning.

System (YAML) defaults remain. The CAMLCO's overlay sits on top.

### Match definitions

Custom JSON DSL rules **scoped to the bank**. When the bank executes a definition, it runs against their own entity universe (RLS-bounded). Definitions are private to the bank — BFIU doesn't see another bank's bespoke rules.

### Reference tables

**Read-only**. The CAMLCO sees the 7 tables (banks, channels, categories, countries, currencies, agencies, branches) and reads them for STR drafting + dropdowns. **Cannot mutate** — `is_regulator()` policy gates writes.

Exception: **Branches tab is per-bank writable**. The bank lists its own physical/digital branches here.

### AI outcomes

Own-bank AI invocations only. CAMLCO sees the 4 stats + by-task correction rate + recent stream for their bank.

### API Keys

The page that will (V2) let the CAMLCO issue scoped API keys for their bank's core-banking integration. Today, read-only view of the 3 declared system integrations.

---

## 17 · Admin tabs CAMLCO does NOT see

Quick reference:

| Tab | Why CAMLCO blocked |
|---|---|
| **Schedules** | `roles: ["admin", "superadmin"]`. Manager doesn't qualify. (Even Sonali's admin user would see it.) |
| **Status** | Two gates — `["admin", "superadmin"]` AND `["bfiu_director", "bfiu_analyst"]`. Bank persona fails the second. |

The bank doesn't manage Kestrel's infrastructure (Beat tasks + status incidents) — that's BFIU territory. Bank consumes the public `/status` page for outage visibility.

---

## 18 · Director-only surfaces CAMLCO entirely lacks

The Command bucket is the most-visibly thinned for bank persona:

- `/reports/national` — National threat dashboard. **Blocked.**
- `/reports/trends` — Country-wide time series. **Blocked.**
- `/reports/statistics` — goAML-shape stat panels. **Blocked.**

These three are **regulator-strategic surfaces** — letting a bank see national alert volume trends could let them game the system or extract competitive intel about other banks. Procurement-grade locked down.

---

## 19 · What this means for the demo

When you're walking Sonali / City CAMLCO through Kestrel, the high-value moments are:

1. **Show `/overview`** — they see their bank's name in the hero, own-bank alerts in the wire, own-bank stats. Immediate "this is **our** workspace" recognition.

2. **Show `/intelligence/cross-bank`** — open the page, point to *"Peer institution 1, Peer institution 2..."* and *"····5001"* redacted identifiers. Say: *"This is FATF Recommendation 9 enforcement. We see the cross-bank pattern but never see another bank's specific customer. We comply with tipping-off rules by design."*

3. **Show `/customers`** — the bank-only KYC surface. Demonstrate onboarding flow + re-screen → "this is what your AML team uses daily."

4. **Show `/scan`** — the upload path. *"You batch-upload transactions here; Kestrel runs detection inline; alerts surface on /alerts."*

5. **Show `/admin/rules`** — bank-side tuning surface. *"You can adjust the rule weights for your bank's risk profile. The system defaults are BFIU's; your overlays are private to you."*

6. **Show `/admin/team`** — *"Your bank's CAMLCO + Deputy CAMLCO + analysts all live here. We add seats; we revoke seats; activity audited."*

7. **End with `/reports/compliance`** — *"This is the page that drives BFIU's monthly call to your CAMLCO. You can see your own score in detail + ranked anonymised against peers. Your daily work moves this number."*

Total demo: ~12 minutes for these 7 surfaces. Leave the AI / TBML / Disseminations for follow-up sessions.

---

## 20 · Sonali vs City — what's identical

Both Sonali (`org_id 9c222222-…`) and City (`org_id 9c666666-…`) are on `plan_id=professional`. Their **surfaces are identical**; the **data is different**:

- Sonali CAMLCO sees Sonali's 4 cases, 3 STRs, 3-cluster cross-bank participation, 13 KYC customers.
- City CAMLCO sees City's 4 cases, 3 STRs, 3-cluster cross-bank participation, (0 KYC customers — not seeded).
- Both see the marquee 5-bank cluster `····5001` because both participate in it.

If during the City demo you pivot to Sonali's tenant by accident (or vice versa), the cross-bank wire shows **the other bank as "Peer institution N"** — perfect live evidence of the anonymisation working.

---

## 21 · Multi-tenant isolation — the procurement document

When bank-side IT or audit asks *"how do we know our data isn't visible to other banks?"* — point them to:

**`docs/multi-tenant-isolation-verified.md`** — 8 sections covering:
1. The 4-layer isolation architecture (middleware → route auth → service guard → RLS).
2. Verbatim RLS policy citations.
3. File:line citations of regulator-only mutation guards.
4. Cross-bank persona invariants.
5. Frontend route gates.
6. **Live verification on prod 2026-05-05** — RLS simulation as Sonali CAMLCO showing 4/10 STRs visible, 3/49 alerts visible, peer banks rendered as `PEER INSTITUTION N`, match keys redacted to `····XXXX`, `POST /api/reference-tables` returning `403 Insufficient role` with captured request_id.

This is **what passes the bank's IT review**. The document is checked into the repo as procurement evidence.

---

## 22 · Filing-only filer is a separate persona

Don't confuse `bank_camlco` (this delta) with `bank_filer`. The Filer is the **goAML-replacement free tier under BFIU procurement** — locked to just `/strs`, `/iers`, `/reports/export`. That's the D3 delta (separate document).

When BFIU procures Kestrel at the national level, every bank gets a free **Filer** workspace; the bank separately upgrades to **Professional** (the CAMLCO surface) for the commercial-grade tooling.

---

## Banking 101 — multi-persona vocabulary

| Term | What it means |
|---|---|
| **Bank persona** | One of: `bank_camlco`, `bank_filer`. Drives UI layout + nav visibility. |
| **Anonymisation** | Server-side replacement of other-bank specifics with neutral labels (`Peer institution N`) + redaction of identifiers (`····5001`). |
| **FATF R.9** | Recommendation 9 — Tipping-Off. Banks cannot be informed of other banks' specific filings. Kestrel enforces. |
| **RLS bounded** | A query returns only rows the calling user can see per the Postgres Row-Level Security policy. The database enforces, not the application. |
| **`is_regulator()`** | SECURITY DEFINER helper returning true if caller's org is `org_type='regulator'`. Gates many WRITE policies. |
| **Plan tier** | `filing_only` / `starter` / `professional` / `enterprise`. Tier determines which features unlock — bank CAMLCO defaults to `professional`. |
| **Manager role** | The CAMLCO's typical role. Action buttons enabled; cannot mutate platform-admin surfaces. |
| **Circular 22** | BFIU Circular 22/2019. The bank-to-bank info exchange enabling clause under MLPA § 23(1)(d). |
| **Multi-tenant isolation** | The cross-org-cannot-read-other-org property. Documented in `docs/multi-tenant-isolation-verified.md`. |

---

## What's next

**D1 — BFIU Analyst delta** (national-scope, no admin) and **D3 — Bank Filer delta** (filing-only locked tier) round out the persona sequence. Both are short additions to this CAMLCO delta.

For the full sequence + Director walk see [`tutorials/README.md`](README.md).
