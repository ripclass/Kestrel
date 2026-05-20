# Delta D1 — BFIU Analyst walkthrough

**Purpose**: What the **BFIU Analyst** persona sees *differently* from the Director walk (Tutorials 01–30). Designed for BFIU internal walkthroughs where the Joint Director / Section Chief is showing junior analysts the surfaces they'll use daily.

**Persona under examination**: `bfiu_analyst` × `analyst` (or `manager`) × `regulator` plan
**Live demo credentials**:
- **BFIU Analyst**: `analyst@kestrel-bfiu.test` / `Kestrel!Analyst!2026` · Sadia Rahman · Deputy Director, Intelligence Analysis

**Reading time**: ~6 minutes
**How to use this**: Read the Director walk first. This delta covers what's **different** for the investigator tier.

---

## TL;DR — who this persona is

The Director is the **command lens** (scorecards, dashboards, phone calls to CAMLCOs). The Analyst is the **investigator lens** — same regulator scope, same cross-bank visibility, but the surfaces they live in are different:

- **Director** lives in `/overview` + Compliance + Trends + Statistics. Strategic, decisional.
- **Analyst** lives in `/investigate` + Alerts + Cases + STRs + IERs + Cross-bank + TBML. Operational, evidentiary.

Both see the same data (`is_regulator()` RLS = full national pool). The difference is **role-gated mutations** and **strategic-Command tabs** that the analyst doesn't need.

This is the **bulk seat** in BFIU's procurement. Realistic mix:
- 1 Head of BFIU (Director × superadmin)
- 2–5 Joint Directors (Director × admin)
- 3–6 Section Chiefs (Analyst × manager)
- **10–60 Investigators (Analyst × analyst)** ← this delta
- 1–4 Audit / Viewer

So 60–80% of a BFIU deployment runs on this persona × role combination.

---

## 1 · Sidebar — what changes vs Director

The Analyst sidebar shows **21 nav items** (vs Director's 30). The diff is in Command + Admin.

### Items LOST vs Director

| Tab | Why Analyst can't see it |
|---|---|
| **Command → Compliance** | `personas: ["bfiu_director", "bank_camlco"]` — explicitly Director-side or bank-side. Analysts don't drive compliance calls; the Director does. |
| **Command → Trends** | `personas: ["bfiu_director"]` — Director-only strategic surface. |
| **Admin → Settings / Team / Rules / Match definitions / Reference tables / Schedules / API Keys** | All `roles: ["admin", "manager", "superadmin"]`. Analyst role (the bottom tier) doesn't qualify. |
| **Admin → Status** | `roles: ["admin", "superadmin"]` × `personas: ["bfiu_director", "bfiu_analyst"]` — fails the role gate. |

### Items KEPT vs Director

| Tab | Why Analyst sees it |
|---|---|
| **Command → National** | `personas: ["bfiu_director", "bfiu_analyst"]` — analyst included. Investigation context. |
| **Command → Statistics** | Same gate as National. Analyst uses for case-prep + report rolls. |
| **Command → Export** | All authed users. Analyst exports case-related XLSX / XML for handoff. |
| **Admin → AI outcomes** | `roles: ["admin", "manager", "superadmin", "analyst"]` — explicitly accepts analyst. Investigator-grade visibility into AI calls fired on their cases. |

### Items SAME for both

The 17 remaining items (Overview + Intelligence Tools 9 + Operations 7 — minus Scan and Customers which are bank-only) are visible to both Director and Analyst. **What they show is identical** because both are regulator-scope. RLS doesn't differentiate Director from Analyst.

### Sidebar summary

| Bucket | Director count | Analyst × analyst | Analyst × manager |
|---|---|---|---|
| Overview | 1 | 1 | 1 |
| Intelligence Tools | 9 | 9 | 9 |
| Operations | 7 | 7 | 7 |
| Command | 5 | 3 (National, Statistics, Export) | 3 (same) |
| Admin | 8 | 1 (AI outcomes) | 7 (loses Schedules, Status) |
| **Total** | **30** | **21** | **27** |

---

## 2 · Role × persona — the seat tiers

A BFIU Analyst persona ships with one of these roles:

| Role | Title | Sidebar | What they do |
|---|---|---|---|
| `analyst × superadmin` | (not realistic — Head of BFIU uses Director persona) | — | — |
| **Analyst × manager** | Section Chief / Deputy Director, Section | 27 nav items | Run a section of analysts; tune rules, manage team members, edit match definitions |
| **Analyst × analyst** | Investigator (the bulk seat) | 21 nav items | Triage alerts, investigate cases, draft STRs, respond to IERs |
| Analyst × viewer | Audit / external evaluator | 21 nav items, read-only | Read-only access for inspections |

The seeded test user (`analyst@kestrel-bfiu.test`) is `analyst × analyst` — i.e. an Investigator. The smallest, most-numerous tier.

---

## 3 · `/overview` — same lens, slightly different framing

URL: `/overview`.

The Analyst lands on `/overview` and sees the **same CommandView dashboard the Director sees**:
- Live wire · Alerts.
- Cross-bank wire.
- National command summary.
- 3 stat tiles.
- Channel signal strip.
- National threat heatmap.
- Bank compliance posture.

The hero copy may reframe slightly per persona but the **data is identical**. Both regulator personas see the national rollup because both have `is_regulator()` = true.

### Where the difference shows up

- The Analyst doesn't typically *act* on the "Attention needed" bank — that's a Director call. They observe it.
- The Analyst uses the Live wire alerts list more — those are the alerts they'll work through today.

---

## 4 · `/investigate` — the Analyst's primary surface

This is where the Analyst spends most of their day. Tutorial 02 applies identically.

### Analyst daily flow on `/investigate`

1. **Receive a lead** — internal note, foreign-FIU IER, press story, RFI from a bank.
2. **Paste the identifier** into the omnisearch or topbar search.
3. **Land on entity dossier** — read header, AI explanation, two-hop graph, reporting history.
4. **Click "Investigate this entity (AI)"** — run the agent if the case is complex.
5. **Promote to STR draft or open case** — depending on whether action needed.

A skilled Analyst clears 15–25 entity dossiers per day. The dossier is their canvas.

---

## 5 · `/alerts` — the triage queue

URL: `/alerts`. Tutorial 13 applies.

### What the Analyst does here

- **Triage critical alerts daily** — read AI explanation + rule trace.
- **Disposition each one**: true positive → create case · false positive → mark + note · escalate → BFIU Joint Director queue.
- **Convert promising alerts into cases** via the "Create case" action.

### Distinct from CAMLCO experience

A bank CAMLCO sees own-bank alerts. The Analyst sees **the full national alert pool** — every bank's alerts are visible to them. They can prioritise cross-bank patterns over single-bank noise.

This is the surface where the Analyst spots correlations CAMLCOs can't see (because the CAMLCOs are bank-bounded).

---

## 6 · `/cases` — Analyst's investigation workbench

URL: `/cases`. Tutorial 14 applies.

### What the Analyst does

- **Assigned cases** — the Analyst is the `assigned_to` user on the case rows they own.
- **Investigate** — add notes, link STRs, attach diagrams.
- **Generate case PDF** — for handoff to LE.
- **Escalate** — to Joint Director when dissemination is needed.

The Analyst typically owns 5–20 active cases. The case is their **work-in-progress folder**.

### What the Analyst CAN'T do

- **Disseminate to LE directly** — the dissemination action requires admin/manager role. Analyst escalates to Section Chief who handles the dissemination submission.

---

## 7 · `/strs` — Analyst review surface

URL: `/strs`. Tutorial 12 applies.

### What the Analyst does

- **Review submitted STRs** — when banks submit, the Analyst reads, validates, marks confirmed / rejected.
- **Draft internal STRs** — using report type `Internal` for BFIU-side intelligence packets.
- **Enrich** — add context, cite typologies, link to cases.
- **Supplement** — request additional info via `Addl. Info` report type.

The Analyst is the **first set of eyes** on every submitted STR before BFIU forwards anything to LE.

---

## 8 · `/iers` — Foreign FIU + Circular 22 exchange handler

URL: `/iers`. Tutorial 16 applies.

### Analyst-specific work

- **Inbound foreign FIU IER** — when FinCEN / FINTRAC / AUSTRAC ask about a BD subject, the Analyst gathers the response (queries the system, drafts narrative).
- **Inbound bank-to-BFIU IER** — a bank asks BFIU for context on a peer customer; Analyst responds under Circular 22.
- **Outbound Analyst-initiated IER** — when an investigation needs context from a foreign FIU.

The Analyst's responses go through the Section Chief or Joint Director for approval before transmission (the Egmont channel is on the Director side).

---

## 9 · `/intelligence/cross-bank` — Analyst's pattern detector

URL: `/intelligence/cross-bank`. Tutorial 08 applies.

### What the Analyst does here

- **Daily 30d window scan** — anything new in the cross-bank cluster list?
- **Drill into a cluster** — click the entity row → dossier → AI investigation.
- **Build a case** — when a cluster warrants formal investigation.

### Director vs Analyst difference

- The Director uses this for **situational awareness** — scan, note, move on.
- The Analyst uses it for **actionable investigation** — click into specific clusters, build cases.

Same surface, different lens of use.

---

## 10 · `/intelligence/tbml` — TBML case discovery

URL: `/intelligence/tbml`. Tutorial 11 applies.

### Analyst-specific work

The Analyst is the human behind every TBML investigation. The dashboard surfaces:
- **Multi-invoicing clusters** — investigate as a single coordinated case.
- **Country-pair heatmap** — pick the highest-risk corridor pair (Iran, HK, SG, AE) and walk through the trade transactions.
- **Recent TBML alerts** — open the alert detail, read the rule trace + avenue citation, decide action.

This is **the surface that closes BFIU's TBML procurement question** — and the Analyst is the operator who delivers the value of this surface daily.

---

## 11 · `/intelligence/typologies` + `/intelligence/saved-queries` + `/intelligence/disseminations`

All three are accessible. Analyst use:

- **Typologies** — reference catalogue when writing STR narratives. Cite the BFIU avenue + indicators.
- **Saved queries** — store personal investigation patterns. Share with the team via the share toggle.
- **Disseminations** — read-only for the most part. The Analyst sees the dissemination ledger to understand what's been routed where; mutations happen at admin/manager level.

---

## 12 · Operations surfaces — Analyst use

| Surface | Analyst behavior |
|---|---|
| **`/strs`** | Read submitted; enrich; respond. Primary surface. |
| **`/alerts`** | Daily triage queue. |
| **`/cases`** | Investigation workbench. |
| **`/iers`** | Foreign FIU + Circular 22 response work. |
| **`/monitoring/realtime`** | Read-only — see system-wide realtime traffic. Analyst doesn't manage the integration; they observe. |
| **`/screen`** | Identical to Director — manual lookup when an investigation needs sanctions check. |
| **(no `/scan`)** | Bank-only surface. Analyst doesn't see it. |
| **(no `/customers`)** | Bank-only surface. Analyst doesn't see it. |

---

## 13 · Command bucket — 3 items instead of 5

The Analyst's Command bucket:

### `/reports/national`

The National Threat Dashboard. Same widgets as `/overview` — but framed as a *reporting* surface. The Analyst opens this when preparing for a Joint Director meeting (need to take a screenshot of the dashboard into the meeting deck).

### `/reports/statistics`

Operational statistics. The Analyst uses this for **prep work** — quarterly review of typology trends, channel volumes, case-outcome distributions. Drives the BFIU monthly brief.

### `/reports/export`

Export center. The Analyst generates briefing packs for handoff (to LE, internal Joint Directors, external evaluators). Same 3-option dropdown.

### Items LOST vs Director

- **Compliance** — the readiness scorecard. Not an Analyst function.
- **Trends** — strategic time series. Not an Analyst function.

These two are the surfaces the Director uses for **regulatory pressure conversations**. Analysts don't make those calls.

---

## 14 · Admin bucket — just AI outcomes (for `analyst` role)

For `bfiu_analyst × analyst`, the Admin bucket collapses to **1 item**: AI outcomes.

### Why AI outcomes is accessible to analysts

The Analyst is the **person who corrects AI output**. When they edit an AI-drafted STR narrative or dismiss an AI alert explanation, they generate the training-data correction. This page (Tutorial 29) is where the Analyst sees:
- The volume of AI calls fired on their work.
- Their personal correction rate.
- The recent stream of invocations they triggered.

This is also **part of the V3 P4 corpus-building** — the more analyst corrections accumulate here, the better the sovereign-AI fine-tune will be.

### For `bfiu_analyst × manager` (Section Chief)

The Section Chief gains 7 Admin tabs (loses Schedules + Status only). Section Chiefs:
- **Edit rules** — tune the detection-engine for the section's risk patterns.
- **Author match definitions** — add bespoke patterns based on emerging typologies.
- **Manage team** — onboard new investigators, promote senior analysts.
- **Edit reference tables** — BFIU is the regulator org so reference-table writes are allowed at this role tier.
- **Review API keys** — see active integrations.

The Section Chief is the **operational floor manager** of BFIU's investigation work.

---

## 15 · What stays identical between Director and Analyst

A deliberately complete list, because the equality is the point:

- **Cross-bank intelligence (`/intelligence/cross-bank`)** — full national view, no anonymisation. Both regulator personas see everything.
- **Matches ledger (`/intelligence/matches`)** — full national list.
- **Entity dossier (`/investigate/entity/[id]`)** — full reporting history, full graph, full AI agent.
- **Alerts (`/alerts`)** — full national queue.
- **Cases (`/cases`)** — full national case list.
- **STRs (`/strs`)** — every bank's submitted STR is readable.
- **Disseminations (`/intelligence/disseminations`)** — full outbound ledger.
- **IERs (`/iers`)** — full inbound + outbound ledger.

Both personas see the same data. The differences are at the **action button** level (who can mutate what) and the **strategic Command surface** level (who needs the dashboards).

---

## 16 · How the Analyst's day looks

Realistic Monday flow for Sadia Rahman (Deputy Director, Intelligence Analysis):

| Time | Surface | Action |
|---|---|---|
| **09:00** | `/overview` | Coffee + scan the wire. See if anything is unusually shaped. |
| **09:15** | `/alerts` | Triage critical alerts. Today: 11 new criticals over the weekend. Triage 6, escalate 3, dismiss 2. |
| **10:00** | `/cases` | Open her 5 active cases. Review notes from Friday. |
| **10:30** | `/intelligence/cross-bank` | Spot-check for new clusters in the 7-day window. One new cluster — open it. |
| **11:00** | `/investigate/entity/[uuid]` | Investigate the new cluster's marquee entity. Run the AI agent. |
| **11:30** | `/iers` | Respond to a FINTRAC inbound IER on a BD national. Gather the data, draft response. |
| **13:00** | (lunch) |  |
| **14:00** | `/cases` | Continue investigation on her highest-priority case. Add notes, link STR, attach diagram. |
| **15:30** | `/strs` | Review 3 newly-submitted STRs from BRAC. Confirm 2, request supplement on 1. |
| **16:30** | `/reports/export` | Generate a briefing pack for the Joint Director's morning meeting tomorrow. |
| **17:00** | `/admin/ai-outcomes` | Quick check on her AI correction rate this week. |
| **17:30** | (end of day) |  |

Total active cases: 5–8. Total alerts triaged: 15–20 / day. Total STRs reviewed: 3–5 / day. **This is the load that one Analyst seat carries**.

---

## 17 · Investigator viewer-mode (audit + external evaluators)

`bfiu_analyst × viewer` is the read-only seat for audit committees + external evaluators (e.g. FATF Mutual Evaluation team).

What the viewer can do:
- **See all 21 nav items** identical to investigator.
- **Read every record across all banks** (full regulator scope via RLS).
- **Cannot mutate** — every action button (Mark TP / FP / Submit STR / Disseminate / etc.) is disabled.
- **Export** — viewers can generate XLSX/PDF exports for their own audit reports.

This is **the seat tier FATF inspectors get** when they're in BFIU's office for the next Mutual Evaluation cycle. They walk the same surfaces investigators use; they read the same evidence; they cannot accidentally affect the data.

---

## 18 · Differences in cross-bank visibility

A clarification because this gets asked: **bfiu_analyst sees the full unanonymised cross-bank data, same as the Director.**

`engine/app/services/cross_bank.py::_label_orgs_for_user` reads:
```python
if user.org_type == "regulator":
    return orgs  # full bank names
# else (bank persona):
#   return anonymised "Peer institution N"
```

The check is on **org_type**, not persona within regulator. Director and Analyst both have `org_type='regulator'` → both see full data.

The same applies to `_anonymize_match_key` — regulator returns the identifier unchanged.

---

## 19 · Demo flow — for internal BFIU walkthrough

When walking BFIU through what their Analysts will see day-to-day:

1. **Log in as Sadia** (`analyst@kestrel-bfiu.test`) — show her identity in the topbar.
2. **Sidebar tour** — 21 items, 3 short of Director, but **all the investigation surfaces** (`/investigate`, `/alerts`, `/cases`, `/strs`, `/iers`) are present.
3. **Show `/overview`** — same dashboard, framed for investigation context.
4. **Show `/alerts`** — the daily queue. Walk one alert's workspace including AI explanation.
5. **Show `/cases`** — the workbench. Open a case detail; show the timeline + notes + linked alerts.
6. **Show `/investigate`** — search for an entity; open the dossier; show two-hop graph.
7. **Show `/intelligence/tbml`** — point at the multi-invoicing clusters; explain Analyst's investigation path.
8. **Show `/admin/ai-outcomes`** — *"this is where you'll see your AI invocations + correction history."*
9. **Try clicking `/admin/team`** — middleware blocks → redirect or 403. *"Section Chiefs handle team; you don't."*
10. **End with `/reports/export`** — *"when your case is ready for handoff, you generate the PDF here."*

Total: ~12 minutes. The investigator's daily reality, made explicit.

---

## 20 · Section Chief vs Investigator — show the role difference

If walking a senior staff member who would get `bfiu_analyst × manager`, do a second pass showing:
- `/admin/team` — visible to Section Chief, can promote investigators.
- `/admin/rules` — visible, can tune the detection engine's weights.
- `/admin/match-definitions` — visible, can author bespoke patterns from emerging cases.
- `/admin/reference-tables` — visible, can add new bank shortcodes as BFIU licences new entities.

The 7-item Admin bucket at manager-role level is **the management surface** distinct from the 1-item analyst-role view.

---

## Banking 101 — Analyst seat vocabulary

| Term | What it means |
|---|---|
| **Analyst persona** | `bfiu_analyst`. The investigator-tier regulator persona. Same data scope as Director, different action-button availability. |
| **Investigator (analyst × analyst)** | The bulk seat — 60–80% of a BFIU deployment. Triages alerts, investigates cases, drafts STRs. |
| **Section Chief (analyst × manager)** | The operational floor manager. Adds 7 Admin tabs vs investigator. |
| **Viewer (analyst × viewer)** | Read-only — audit committees, external evaluators, FATF inspectors. |
| **org_type='regulator'** | The check that grants full national visibility. Director and Analyst both pass. |
| **Section** | A BFIU organisational unit. Each Section Chief manages 3–10 investigators. |
| **Joint Director** | The seat tier above Section Chief — typically `bfiu_director × admin`. Strategic + tactical. |
| **Mutual Evaluation Report (MER)** | FATF's seven-year peer review. Inspectors land here as viewer-role users. |
| **AI correction** | An analyst's edit / dismissal of AI output. Feeds the V3 P4 training corpus. |

---

## 21 · The complete persona matrix

| Persona × role | Sidebar | Function | Mutations |
|---|---|---|---|
| `bfiu_director × superadmin` | 30 | BFIU Head | Platform + national |
| `bfiu_director × admin` | 30 | Joint Director | National + team |
| `bfiu_analyst × manager` | 27 | Section Chief | Section management + admin tabs |
| **`bfiu_analyst × analyst`** | **21** | **Investigator** | **Alerts / cases / STRs / IERs** |
| `bfiu_analyst × viewer` | 21 | Audit / inspector | Read-only |
| `bank_camlco × admin` | 27 | CAMLCO + Deputy | Bank operations + bank admin |
| `bank_camlco × manager` | 27 | AML Unit Head | Operations + tuning |
| `bank_camlco × analyst` | ~24 | Bank AML analyst | Daily ops |
| `bank_camlco × viewer` | ~24 | Internal audit | Read-only |
| `bank_filer × any` | **3** | Filer | STR / IER / Export only |

Five operational persona × role combinations cover essentially every real seat in a national deployment.

---

## What's complete

This is **D1 of the three persona delta documents**. Together with:
- ✅ D1 — BFIU Analyst delta (this document)
- ✅ D2 — Bank CAMLCO delta (Sonali + City demos)
- ✅ D3 — Bank Filer delta (BFIU procurement)
- ✅ Tutorials 01–30 — Director walk

The full Kestrel platform documentation is now complete from a persona perspective. Every user a bank or BFIU might deploy has a tutorial they can read.

For the full sequence + Director walk see [`tutorials/README.md`](README.md).
