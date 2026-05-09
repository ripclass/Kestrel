# Leave-behind — Bank

**Purpose**: one printed page, front and back, handed to the CAMLCO at the end of the demo. Goal: the document survives the meeting, gets walked into the bank's CFO's office on its own, and answers the four questions a bank's procurement team always asks before approving a pilot.

**Print**: A4, two-sided, monochrome, IBM Plex Sans for body / IBM Plex Mono for IDs and amounts. Black on white. No glossy paper.

---

## ┼ FRONT

# Kestrel
### Financial crime intelligence for Bangladesh's banks.

---

**The problem you can't see from inside one bank.**

Scam money moves across six banks in twelve minutes. Your CAMLCO sees only what passed through your bank. BFIU sees the XML files three weeks later. The cross-institution picture exists only in the head of whichever analyst happens to pull the right thread.

Ninety percent of suspicious activity in Bangladesh originates inside the banking system. *(BFIU Annual Report, FY 2022-23.)*

---

**What Kestrel adds, today, in production.**

**Cross-bank entity intelligence.** Every STR your bank submits is matched against every STR every other Kestrel bank has submitted. When the same NID, phone, account, or wallet appears at two or more institutions, Kestrel surfaces the cluster — anonymised on your side, full picture on BFIU's. Your CAMLCO sees *"this subject is also flagged at four peer institutions"* before the money moves again.

**Real-time transaction scoring.** A single HTTP call from your core banking system, sub-500ms decisioning, explainable reason array. Approve, review, hold, or reject — with the rule that fired and the evidence behind it. Bangladesh's twelve real rails: NPSB, BEFTN, RTGS, bKash, Nagad, Rocket, RTGS, cash, cheque, card, wire, LC, draft.

**AI-drafted STRs.** Your scanner finds the pattern. The AI writes the analyst-ready narrative — citing the rule, the cross-bank linkage, the evidence — in the four seconds it takes the page to load. Your analyst reads, judges, edits, submits. Ninety minutes of writing becomes eight minutes of reviewing.

**goAML pipeline preserved.** Your existing XML import and export round-trip cleanly. We don't ask you to throw anything away. Kestrel sits above the filing cabinet, not in place of it.

---

**Production state, today.**

| 27,481 | Sanctions records screened daily, OFAC + UN + UK FCDO, refreshed every 24h. |
| < 500ms | Real-time transaction scoring SLA. |
| 134 | Production API routes. STR / CTR / IER / case / screening / realtime / agentic. |
| 11 | Scheduled jobs running. Nightly scan, daily digest, KYC re-screen, audit retention. |
| < 10 min | From signup to populated demo workspace. Self-serve. |
| 99.5% / 99.9% | Uptime SLA, Professional and Enterprise tiers. Live status page. |

Hosted in Singapore (Supabase ap-southeast-1). On-premise option for tier-1 banks. BB Circular 26/2024 alignment built in.

---

## ┼ BACK

### Three commercial tiers, BDT-denominated.

| | **Starter** | **Professional** | **Enterprise** |
|---|---|---|---|
| **Price** | Tk 60 lakh / yr | Tk 1.5 crore / yr | Tk 4 crore / yr |
| **CAMLCO seats** | 5 | 15 | 50 |
| **Transactions / month** | 500k | unlimited | unlimited |
| **Pattern scanner + AI alerts + STR drafts** | ✓ | ✓ | ✓ |
| **Cross-bank intelligence (anonymised)** | ✓ | ✓ | ✓ |
| **goAML XML round-trip** | ✓ | ✓ | ✓ |
| **Real-time scoring API** | — | ✓ | ✓ |
| **Sanctions / PEP / adverse-media screening** | — | ✓ | ✓ |
| **KYC onboarding with inline screening** | — | ✓ | ✓ |
| **Agentic AI investigations** | — | — | ✓ |
| **On-premise deployment + sovereign LLM** | — | — | ✓ |
| **Dedicated 24/7 support, named CSM** | — | — | ✓ |

---

### Pilot terms.

**Thirty days. Fixed pilot fee. Converts to year-one subscription on contract.**

You sign up at `kestrelfin.com/signup/bank`. Your tenant is provisioned in ten minutes with anonymised demo data. Within a week you've imported your own goAML XML and your CAMLCO is working real signal. At day thirty, you decide: convert (pilot fee credits against year-one) or wind down (we delete the tenant and you walk away).

**First-mover banks pilot at half-price for six months in exchange for being a named reference.** This offer is open until the third paid pilot.

---

### What happens after this meeting.

If you want to evaluate further → click `kestrelfin.com/signup/bank` from your CAMLCO's email, the magic-link invite arrives in the next two minutes, the tenant is live ten minutes after that.

If you want a pilot agreement → reply to this email and we send the one-page pilot terms within twenty-four hours.

If you want a deeper architecture review for your CTO → `kestrelfin.com/docs/api`, `/docs/security`, `/docs/goaml`. No registration. No gating.

---

### Direct.

**Ripon Chowdhury** · Founder
intake@kestrelfin.com
Dhaka, Bangladesh
**Enso Intelligence Inc.**

`kestrelfin.com`

---

*Document version 2026-Q2. All BDT pricing is quoted in writing before any contract is signed. Implementation services priced separately.*
