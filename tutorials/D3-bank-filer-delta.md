# Delta D3 — Bank Filer walkthrough

**Purpose**: What the **bank Filer** persona sees — the goAML-replacement free tier under BFIU procurement. This is the *minimum viable* AML platform: file STR / CTR / IER + receive inbound RFIs + export own-bank archives. Nothing else.

**Persona under examination**: `bank_filer` × any role × `filing_only` plan
**Live demo credentials**:
- **BRAC Bank Filer**: `filer@kestrel-brac.test` / `Kestrel!Filer!2026` · Tahmid Khan

**Reading time**: ~7 minutes
**Audience**: BFIU procurement (the people deciding whether Kestrel becomes Bangladesh's national AML infrastructure) + bank CTOs evaluating the free-tier option.

---

## TL;DR — what this persona is for

When BFIU procures Kestrel at the national level under their contract, **every commercial bank in Bangladesh gets a free Filer workspace**. The Filer surface is intentionally minimal:

- File STRs / CTRs / IERs / TBML reports in goAML XML.
- Import goAML XML produced by existing core-banking pipelines.
- Export own-bank goAML XML for archival.
- Receive inbound RFIs from BFIU + Circular 22 exchanges from peer banks.
- Nothing else.

A Filer workspace **costs the bank nothing** — it's bundled in the BFIU national contract. Banks who want the commercial-grade intelligence platform (cross-bank intel, real-time scoring, AI, KYC, sanctions) upgrade to `professional` (Tk 1.5 cr/year) or `enterprise` (Tk 4 cr/year) — that's a **separate commercial relationship** with Kestrel direct, parallel to the BFIU contract.

**This is what makes Kestrel a credible goAML replacement.** Banks continue to file the way they always have, on a familiar surface, for free. The intelligence upgrade is opt-in.

---

## 1 · The procurement framing — three revenue streams

This is the sentence that closes the BFIU procurement conversation:

> *"Under your BFIU contract, every bank files for free in goAML XML, exactly like today. They keep filing the way they file today. What we add for them — cross-bank intel, AI, scoring, KYC — is a separate commercial relationship between Kestrel and each bank. You get one unified intelligence layer; banks keep filing for free; commercial revenue comes from banks who want the upgraded toolkit. Three revenue streams, zero conflict."*

| Revenue stream | Customer | What they pay | What they get |
|---|---|---|---|
| **BFIU national contract** | Bangladesh Bank's BFIU | multi-year national contract (bespoke pricing) | The full regulator platform + every bank's Filer workspace bundled |
| **Bank professional / enterprise** | Each commercial bank | Tk 1.5 cr / yr (pro) or Tk 4 cr / yr (enterprise) | The CAMLCO commercial surface (cross-bank, real-time, AI, KYC, sanctions, agentic) |
| **Bank on-prem (enterprise)** | Tier-1 customer | Enterprise + deployment fee | Air-gapped on-prem deployment with sovereign AI |

Filer = stream 1's bank-side delivery. CAMLCO = stream 2. On-prem deployment = stream 3. **Three streams, no conflict** — banks pay nothing for filing; pay separately for the intelligence platform if they want it.

---

## 2 · Sidebar — extremely thin

The Filer sidebar shows **3 nav items**. Period.

| Tab | URL | Purpose |
|---|---|---|
| **Operations → STRs** | `/strs` | Draft + import + submit + supplement STR / CTR / TBML / Complaint / etc. (11 variants) |
| **Operations → Exchange** | `/iers` | Receive inbound RFIs from BFIU; respond. Send outbound Circular 22 to peer banks. |
| **Command → Export** | `/reports/export` | Generate own-bank XLSX / XML / PDF archives. |

That's it. No Overview. No Investigate. No Cross-bank. No Alerts. No Cases. No Customers. No Real-time. No Screening. No AI. No Admin. **Three tabs.**

### How the filtering happens

`web/src/components/shell/nav-config.ts` defines:

```ts
const FILER_ALLOWED_HREFS = new Set<string>([
  "/strs",
  "/iers",
  "/reports/export",
]);
```

And:

```ts
if (viewer.persona === "bank_filer" && !FILER_ALLOWED_HREFS.has(item.href)) {
  return false;
}
```

So nav items not in the allowlist are filtered out **before they render**.

---

## 3 · Middleware redirect — defense in depth

Even if a Filer tries to navigate directly to a non-allowed URL (e.g. by pasting `/intelligence/cross-bank` into the address bar), the Next.js middleware (`web/src/middleware.ts` → `web/src/lib/supabase/middleware.ts`) intercepts:

```ts
const FILER_ALLOWED_PREFIXES: ReadonlyArray<string> = [
  "/strs",
  "/iers",
  "/reports/export",
];

if (persona === "bank_filer" && !isFilerAllowed(request.nextUrl.pathname)) {
  return NextResponse.redirect("/strs");
}
```

Two layers:
1. **Nav doesn't show the link** (the user can't click).
2. **URL paste redirects** (the user can't sneak in via address bar).

This was the bug fix in PR #4 — the previous `web/proxy.ts` file was silently ignored by Next.js 16 on Vercel. The current `web/src/middleware.ts` with canonical `export async function middleware` works.

---

## 4 · Engine-side feature gating

Even if a Filer bypasses both web layers (e.g. directly calling the engine API with a curl), the **engine returns 402 PAYMENT REQUIRED** on every paid feature.

`engine/app/services/billing.py`:

```python
"filing_only": Plan(
    plan_id="filing_only",
    display_name="Filing only",
    price_bdt_yearly=0,
    seat_cap=5,
    monthly_transaction_cap=None,
    features=("core",),    # ← only "core" — nothing else
),
```

Routes that require paid features (`/transactions/score`, `/screening/entity`, `/customers POST`, etc.) call `require_feature("realtime")` / `require_feature("sanctions")` / `require_feature("kyc")` — Filer plan has none of these, so the call returns:

```http
HTTP/1.1 402 PAYMENT REQUIRED
{
  "error": "feature_required",
  "message": "Realtime scoring is not in your plan. Upgrade to Professional to enable.",
  "feature": "realtime",
  "current_plan": "filing_only",
  "required_plan": "professional"
}
```

Three layers of enforcement: **nav → middleware → API gate**. Even with a leaked JWT, the Filer cannot access paid surfaces.

---

## 5 · What the Filer DOES see — surface by surface

### 5.1 · `/strs` — the entire workspace

The Filer lands here on every session (middleware redirects every non-allowed URL to `/strs`). It IS their home.

**Identical surface** to what a CAMLCO sees on Tutorial 12:
- 11 report-type filter pills (STR / SAR / CTR / TBML / Complaint / IER / Internal / AM-STR / AM-SAR / Escalated / Addl. Info).
- Import goAML XML panel.
- Native draft form (9 fields).
- Lifecycle list with own-bank submissions.
- Export Excel link → `/api/str-reports/export`.

**Same `gen_str_ref()` reference scheme** — STRs prefix `STR-`, CTRs `CTR-`, TBML reports `TBML-`, etc. (Migration 005 CASE map.)

### 5.2 · `/iers` — inbound + Circular 22

Same surface as Tutorial 16. Filer can:
- **Receive an inbound IER** from BFIU — appears in their Exchange ledger.
- **Respond to inbound IER** — fill response narrative + media; submit.
- **Send an outbound IER under Circular 22** — request information from a peer bank.

The Filer **cannot** send outbound to a foreign FIU — that's BFIU's Egmont authority (MLPA § 24(4)). Filer's outbound exchange dropdown gates the foreign-FIU options.

### 5.3 · `/reports/export` — the archive surface

Same Export center as Tutorial 19 Part C. Filer-scoped output:
- **Bank's own STR archive** — XLSX dump for internal audit.
- **Bank's own goAML XML batch** — every STR ever filed, exportable for archival.
- **Submission proof bundle** — for Bangladesh Bank's MLPA inspection.

National briefing pack option is hidden (regulator-only). Compliance scorecard option is hidden (paid feature). Just XLSX/XML own-bank archives.

---

## 6 · What the Filer DOES NOT see

The hidden list is long. Quick reference:

| Surface | Why hidden |
|---|---|
| `/overview` | Not in FILER_ALLOWED_PREFIXES. Middleware redirects. |
| `/investigate/*` | Same. |
| `/intelligence/*` | Same. Cross-bank intel is the paid surface. |
| `/alerts` | Detection engine is "core" but the alert workspace is part of the commercial surface. Filer doesn't see the queue. |
| `/cases` | Investigation tooling is paid. |
| `/customers` | KYC is `require_feature("kyc")` — gated. |
| `/monitoring/realtime` | Realtime scoring is `require_feature("realtime")` — gated. |
| `/screen` | Sanctions screening is `require_feature("sanctions")` — gated. |
| `/intelligence/disseminations` | Banks don't disseminate to LE anyway; the surface is hidden. |
| `/admin/*` | All 8 admin tabs blocked. Filer has no rule tuning, no team management, no reference table access. |
| `/reports/national` · `/reports/compliance` · `/reports/trends` · `/reports/statistics` | All 4 strategic Command surfaces hidden. |

This is **why** the tier is called "Filing only." It's the goAML-shaped subset.

---

## 7 · What the Filer experience looks like

Imagine you're a junior compliance officer at BRAC Bank, your CAMLCO assigned you the Filer login. You sign in → land on `/strs`. You see:

- Header: `Tahmid Khan · bank filer` (your identity).
- Sidebar: 3 items only (STRs, Exchange, Export).
- Topbar: universal search box (returns own-bank entities only via RLS).
- Main: the STR lifecycle list with BRAC's submissions.

Your job:
- Click **"Open a native STR draft"** when your bank's monitoring system flags a customer.
- Fill the 9 fields.
- Click **Create draft** → review on detail page → click **Submit**.
- Status moves `draft → submitted`. BFIU now sees it.
- Monitor `/iers` once a week for inbound RFIs.
- Pull XLSX exports monthly for internal audit.

That's the daily flow. **Nothing else exists in your platform**, by design.

---

## 8 · Why "Filing only" is enough for procurement

When you walk BFIU procurement through Kestrel, the Filer demo is what they emotionally compare against goAML:

| Capability | goAML today | Kestrel Filer |
|---|---|---|
| File STR in XML | ✅ | ✅ |
| File CTR / TBML / Complaint / IER | ✅ | ✅ (11 variants) |
| Import existing pipeline XML | ✅ | ✅ |
| Export bank XLSX / XML | ✅ | ✅ |
| Receive inbound IER from BFIU | ✅ | ✅ |
| Submit Circular 22 to peer bank | ✅ | ✅ |
| Free of charge to the bank | ✅ | ✅ |
| Modern UI (Sovereign Ledger) | ❌ | ✅ |
| Same gen_str_ref + identical goAML XML | ✅ | ✅ |

**No regression on filing capability.** Plus a modern UI. Free to banks.

Then you say: *"…and if a bank wants more, they upgrade. We separately sell them cross-bank intelligence, AI explanations, real-time scoring, KYC, sanctions, agentic investigation. The free Filer tier is here forever; the upgrade is opt-in. Banks who file but don't want intelligence — like smaller co-ops or NBFIs — still get the modern UI for filing."*

**Procurement loves this.** It's lower friction than the goAML replacement they imagined.

---

## 9 · How many banks would land here

Bangladesh has ~64 scheduled banks + MFS + NBFIs. Realistic ratios under a BFIU procurement:

| Tier | Expected banks | Reason |
|---|---|---|
| **Filing only** (free) | ~40–50 | Smaller commercial banks, NBFIs, some MFS providers. They file what they have to file; intelligence platform isn't a priority. |
| **Professional** (Tk 1.5 cr/yr) | ~10–15 | Mid-large commercial banks (City, Sonali, BRAC, Dutch-Bangla, Islami). The ones who'll pay for the commercial surface. |
| **Enterprise** (Tk 4 cr/yr) | ~3–5 | Top-tier banks (probably HSBC BD, Standard Chartered BD, the largest state-owned, the largest private). On-prem-eligible. |

Filer is the **mass deployment**. Professional + Enterprise is the **commercial revenue**.

---

## 10 · The 5-seat cap explained

`filing_only` plan has `seat_cap=5`. That's per-bank.

5 seats is enough for:
- 1 Bank Filer admin (manages other filer seats).
- 1 Deputy Filer admin (succession).
- 2–3 filing officers (the people who actually file).

For most filing-only banks, 5 seats is sufficient. For larger banks with more filing volume, that's a signal — *"upgrade to professional to scale the team"* (15-seat cap).

---

## 11 · Filer ↔ CAMLCO relationship

In a bank that's on **professional** tier:
- The bank has both CAMLCO seats AND Filer-style filing officers.
- Filing officers are typically `bank_camlco × analyst` — they get the same `/strs` surface PLUS the commercial features the bank pays for.
- The dedicated `bank_filer` persona is for banks **only on filing_only tier** — banks that haven't upgraded.

So a `bank_filer` user is a **first-class persona for free-tier banks**, not a downgraded CAMLCO. Different bank entirely.

---

## 12 · Live demo flow — for BFIU procurement

When walking the BFIU through the Filer tier:

1. **Open `/login`** → log in as `filer@kestrel-brac.test`.
2. **Land on `/strs`** — show the lifecycle list with BRAC's submissions.
3. **Click "Open a native STR draft"** — show the 9-field form.
4. **Open one of the seeded STRs** → show the detail page, narrative editor, export XML.
5. **Try clicking outside the allowlist** — e.g. paste `/overview` into the URL → redirected back to `/strs`. Demonstrate the middleware enforcement.
6. **Navigate to `/iers`** — show the inbound RFI panel.
7. **Navigate to `/reports/export`** — show the bank's own archive options.
8. **Switch to CAMLCO** (Sonali) for comparison — same `/strs` page now has 25 more sidebar items + cross-bank intelligence + AI + KYC.
9. **Switch back to Filer** — emphasize the **free vs paid** delineation.

Total: ~10 minutes. The compare-and-contrast against the CAMLCO surface is the powerful moment — same `/strs`, different lens, different price.

---

## 13 · Cross-bank invisibility — the Tipping-Off proof for Filer

A `bank_filer` user has **zero visibility into other banks' filings**. Even more locked-down than the CAMLCO (who at least sees anonymised cross-bank patterns on `/intelligence/cross-bank`):

- RLS on every table filters by `auth_org_id() = org_id`.
- Cross-bank intelligence routes are middleware-blocked.
- The shared `entities` table is theoretically readable (`RLS shared`) but the Filer has no surface to navigate that data — `/intelligence/entities` is blocked.

A Filer **literally cannot tip off** another bank, because the system never shows them anything outside their own bank. FATF Recommendation 9 enforcement, in its most restrictive form.

---

## Banking 101 — Filer vocabulary

| Term | What it means |
|---|---|
| **Filing-only tier** | The `plan_id=filing_only` plan. Free under BFIU procurement. 3 nav items. |
| **goAML replacement** | The positioning of Kestrel against UNODC goAML. Filer is the surface that delivers this. |
| **Two-product split** | The Filer (free, BFIU-procured) + CAMLCO (paid, bank-direct) model. Separate revenue streams. |
| **5-seat cap** | The Filer plan's seat limit. Adequate for filing-only banks; upgrade for more. |
| **Middleware allowlist** | The three URL prefixes Filer can reach. Everything else 307-redirects to `/strs`. |
| **require_feature()** | The engine's feature gate. Returns 402 PAYMENT REQUIRED when the plan lacks the feature. |
| **Plan overrides** | Per-tenant feature enables that go beyond the plan's defaults. Cannot disable a plan-included feature. |
| **`bank_filer` persona** | One of the 4 personas. Distinct from `bank_camlco`. Drives nav + middleware behavior. |
| **MLPA § 25** | The statutory obligation for banks to file STRs. Filer surface delivers this obligation. |
| **gen_str_ref()** | Database function generating `STR-2026-00045`, `TBML-2026-00012`, etc. Same scheme for Filer and CAMLCO. |

---

## 14 · The complete persona sequence

| Persona | Tier | Surfaces |
|---|---|---|
| **bfiu_director** | regulator | All 30 (the Director walk) |
| **bfiu_analyst** | regulator | 30 minus the 8 Admin (national-scope read-only-for-most) |
| **bank_camlco** | professional / enterprise | 27 (gains Scan + Customers; loses National, Trends, Statistics, Schedules, Status) |
| **bank_filer** | filing_only | **3** (STRs, Exchange, Export) |

Read the deltas in this order: D1 (BFIU Analyst) → D2 (Bank CAMLCO) → D3 (Bank Filer) for a complete sweep of how the same platform serves four distinct user populations.

---

## What's next

The persona sequence is essentially complete after D3.

**D1 — BFIU Analyst delta** is small (~5 min) — same scope as Director minus admin write privileges. Can be added separately when you need it for an internal BFIU walkthrough.

For the full sequence + Director walk see [`tutorials/README.md`](README.md).
