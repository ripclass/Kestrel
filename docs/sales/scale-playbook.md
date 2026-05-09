# Kestrel — Scale Playbook (Post-Pilot)

> Founder-internal strategic doc. Not customer-facing. Lives alongside the sales-ops material in `docs/sales/` because the planning is sales-adjacent, but this file should never be linked from kestrelfin.com or shared externally without redaction.

**Working assumption when this document becomes relevant**: 2-3 paid pilots have signed, at least one has converted to production, the production-readiness gaps in `docs/sales/production-readiness.md` are closed, and the first 1-2 engineers have been hired. The platform is now serving real STR volume and real CAMLCOs daily.

The question this doc answers: *what happens next?*

---

## Phase map

| Phase | What it looks like | Time horizon |
|---|---|---|
| **Phase 1 — Pilot validation** *(today)* | Sales scripts ready, demo working, pilot agreement template lawyered, first 3 banks targeted via Kamal bhai introductions. Single founder. Hosted SaaS only. | Q3 2026 |
| **Phase 2 — Production readiness** | First pilot signed → pen test, SOC 2 Type 1, DR drill, insurance, first SRE hired. Subscription contract drafted. Pilot-to-production conversion of bank 1. | Q3-Q4 2026 |
| **Phase 3 — Reference machine** | Banks 1, 2, 3 in production. Bank 4, 5, 6 enter pilots via warm referrals from peer banks instead of cold WhatsApp intros. Sales motion shifts from outbound to inbound. Team is 4-6 people. | Q1 2027 - Q3 2027 |
| **Phase 4 — Marquee regulator deal** | BFIU national deployment goes live. On-prem inside BFIU's data centre with sovereign LLM running locally. Multi-year contract, 8-15 crore range. The deal is what unlocks Phase 5. | Q4 2027 - Q2 2028 |
| **Phase 5 — Geographic expansion** | First peer-FIU deal outside Bangladesh — Sri Lanka, Nepal, Maldives, or further afield. The pitch becomes *"BFIU runs this; here's the reference call you can have with their Director."* Different sales motion entirely. | Q2 2028 onward |
| **Phase 6 — Vertical or platform extension** | Adjacent products: real-time fraud detection, KYC-as-a-service API, insurance-claim fraud, telco compliance. Or platform-as-API: banks build their own UI on top of Kestrel's intelligence layer. Or a second product under Enso Intelligence Inc. that's not Kestrel. | 2029+ |

This is a 36-48 month plan. Pace varies — some banks convert pilot-to-production in 90 days, others stretch to 9 months; BFIU procurement is at least 12-18 months from first briefing to signed contract regardless of how the pilots go.

---

## Phase 3 in detail — the reference machine

Banks 1, 2, 3 are the operational hardening lap. Banks 4-10 are the commercial step-change because the sales motion completely changes.

**Outbound motion (pilots 1-3):**
- WhatsApp introduction from Kamal bhai
- Cold first call
- Founder-driven demo
- 30-45 days of negotiation (NDA → pilot terms → signature)
- 30-day pilot
- Conversion negotiation (subscription contract, DPA, lawyer review on both sides)
- Live in CAMLCO workflow

Total elapsed time per deal: 4-6 months. Founder time: ~30% per deal.

**Referral motion (pilots 4+):**
- Peer-bank CAMLCO mentions Kestrel to peer-bank CAMLCO at an industry event
- Inbound email asking for a demo
- 1-2 calls with founder (or eventually customer success lead)
- Pilot agreement signs in 2 weeks (counterparty has seen the template via the reference bank)
- 30-day pilot
- Conversion negotiation compressed (subscription template already lawyered for bank 1 + 2 + 3)
- Live in CAMLCO workflow

Total elapsed time per deal: 2-3 months. Founder time: ~10% per deal (because the reference bank does most of the convincing in industry conversations).

The 10% founder-time-per-deal is what makes scale possible. Phase 3 ends when the founder is no longer the bottleneck on commercial-tier banks — i.e. customer success has owned the last 3 conversion negotiations end-to-end.

**Hires during Phase 3** (in priority order, hired sequentially):
1. **SRE / DevOps** — covers on-call, DR, observability, scaling. Single point of failure if absent.
2. **Customer success lead** — owns pilots, conversions, weekly check-ins. Bangla + English fluency essential.
3. **AML domain back-end engineer** — knows AML, can extend the engine. Hardest hire; the intersection of finance and back-end Python is rare in Dhaka.
4. **Front-end engineer** — extends the platform UI as banks request features. Sovereign Ledger-fluent, Tailwind v4, brutalist sensibility.
5. **Sales / GTM lead** *(probably not yet)* — Phase 3 is too early for this hire. Founder + customer success lead can carry pilots 4-7 between them.

Team at end of Phase 3: ~5 people. Burn ~$40-60k/month at Bangladeshi salaries. Pilot + subscription revenue should comfortably cover this with 3-5 banks live.

---

## Phase 4 — BFIU deployment is the unlock

BFIU as a customer is not "another bank deal that pays more." It's a strategically different deal:

1. **Procurement timeline is years, not months.** First briefing to signed contract is 12-18 months minimum. The relationship-building happens during Phase 2 + 3 — Kestrel's commercial-bank deployments give BFIU the political coverage to fund a national deployment.

2. **Pricing is bespoke and large.** Multi-year contract, on-premise deployment, sovereign LLM, dedicated TAM, on-site implementation, training, custom rule authoring + national typology library. Realistic range: **8-15 crore for a 3-year contract** (back-of-envelope, depends entirely on scope and procurement vehicle).

3. **The deal funds development-bank attention.** ADB, World Bank, IMF technical-assistance arms fund regulator-grade RegTech deployments in emerging markets. Once BFIU is the customer, Kestrel becomes eligible for grant-funded geographic expansion to peer FIUs in South Asia and beyond.

4. **The political signal compounds.** A Bangladeshi-built RegTech platform that BFIU runs in production reframes Kestrel from *"another AML SaaS"* to *"the platform that secures Bangladesh's banking system."* Every subsequent bank pitch in Bangladesh becomes shorter; every peer-FIU pitch outside Bangladesh starts with that reference.

**Phase 4 hires:**
- **Implementation lead** for the on-premise deployment. Weeks of on-site work inside BFIU's data centre. Probably contracted from a Bangladeshi systems-integration partner; Kestrel co-leads.
- **Compliance / regulatory liaison** — BFIU is a regulator and behaves like one. Need someone whose full-time job is the relationship.
- **Senior security engineer** — production-grade, on-prem, sovereign LLM hosting requires real ops chops.

Team at end of Phase 4: ~10 people.

---

## Phase 5 — Geographic expansion

Once BFIU is live and in production for 6+ months, peer FIUs become reachable. The natural sequence:

1. **South Asia first.** Sri Lanka FIU, Nepal FIU, Bhutan, Maldives, possibly Pakistan if the political moment allows. Egmont Group membership creates the doorway. Cultural and regulatory similarity to Bangladesh keeps the platform's productisation cost low.

2. **Then Southeast Asia.** Philippines AMLC, Indonesia PPATK, Vietnam AMLD, Thailand AMLO. Larger markets, higher contract values, more vendor competition. Different LLM-localisation work — Bahasa, Vietnamese, Thai narrative drafting — which the V3 P4 fine-tuning pipeline accommodates.

3. **Then Africa.** Sub-Saharan emerging markets — Nigeria, Kenya, Ghana, Tanzania, Egypt — where AML infrastructure is being built mostly from scratch and Western vendors price themselves out of reach. This is where Kestrel's Bangladesh-built, BDT-pricing, on-prem-capable origin becomes a strategic moat.

**Funding question: Series A or grant-funded?**

Geographic expansion needs $5-10M of working capital to fund 18-24 months of pre-revenue motion in each new market. Three sources, in order of preference for retaining control:

| Source | Amount | Trade-off |
|---|---|---|
| **Pilot + subscription revenue** | Self-funded | Slowest. Caps expansion to one new market at a time. Best ownership outcome. |
| **Development-bank grant** (ADB / World Bank / Norad RegTech facilities) | $1-3M tranches per market | Mission-aligned, no equity dilution, but bureaucratic — 9-12 months to disburse. Best path if available. |
| **Strategic partnership** (Mastercard, Visa, regional bank network) | $2-5M for equity / partnership | Faster, opens doors, but ties Kestrel commercially to the partner. Mastercard via Kamal bhai is a real candidate to think about now. |
| **Series A from emerging-market focused VC** | $5-10M for 15-25% equity | Fastest, biggest, most dilutive. Right answer if 5+ markets in 24 months is the goal. |

The right call depends on year 1 traction. If 5 banks are paying production and BFIU is signed, raise from a strong Series A and execute fast. If only 2-3 banks are paying and BFIU is still in procurement, take the dev-bank grant route.

---

## Phase 6 — Vertical or platform expansion

Year 4-5 question: extend Kestrel into adjacent verticals, or extend Enso Intelligence Inc. with a second product?

**Option A: Adjacent verticals on Kestrel's engine**
- Real-time payment fraud (different rule set, same engine)
- KYC-as-a-service API (Kestrel's screening pool exposed as a B2B API for fintechs)
- Trade-based ML (TBML) standalone product
- Insurance claim fraud (different industry, same engine)

Pros: leverages the existing platform, low marginal cost.
Cons: dilutes the *"AML for banks and FIUs"* positioning that's the moat.

**Option B: Platform-as-API**
- Banks build their own UI on top of Kestrel's intelligence layer. Stripe-for-AML positioning.
- Existing engine surfaces 134 routes; expose them as a productised API.

Pros: 10x the addressable market. Different revenue mix.
Cons: completely different product motion. Loses the "complete AML platform" narrative.

**Option C: Second product under Enso Intelligence Inc.**
- Kestrel becomes "product 1." Product 2 is something else — different vertical, different geography, different layer.

Pros: protects Kestrel's positioning while diversifying revenue.
Cons: founder time split; building product 2 from scratch with Kestrel's playbook takes 18-24 months.

The right answer is undetermined until Phase 5 traction tells you which adjacent market is loudest in inbound. Don't pre-commit.

---

## Exit horizons (year 7-10)

Three credible paths, each with different optimisation:

| Path | Optimised for | Realistic price | What kills it |
|---|---|---|---|
| **Strategic acquisition by an AML / RegTech major** (NICE Actimize, Verafin, FIS, Fiserv, SAS) | Speed, certainty, founder liquidity | $100-300M if Kestrel is profitable + has 10+ FIU references | Acquirer absorbs the team, kills the brand. |
| **Cloud platform acquisition** (Microsoft, Google, AWS — they all have RegTech ambitions) | Strategic value to a hyperscaler entering financial-crime tooling | $200-500M if Kestrel has 2-3 national-FIU deployments | Cloud lock-in commitments may conflict with on-prem regulator deployments. |
| **PE buyout / strategic local-conglomerate acquisition** | Founders stay; Kestrel runs as a local platform inside the buyer's portfolio | $50-150M | PE multiples are softer than strategic; conglomerate buyers need deep AML conviction. |
| **IPO** | Maximum optionality, founder retains long-term control | Requires $50-100M+ ARR — probably 8-10 years out | Bangladesh capital markets aren't deep enough; Singapore SGX or US listing needed; takes 18 months and ~$5M of legal + compliance work. |
| **No exit, stay private and dividend** | Long-term family-business model | N/A — this is an outcome, not an exit | Forfeits the strategic-platform optionality of paths 1-2. |

Most likely outcome based on what regulator-grade RegTech precedents (Verafin, Quantexa, Symphony AyasdiAI) have done: a strategic acquisition by an AML major in years 7-10, in the $100-300M range, with founder + senior team carve-outs to stay through integration. Not the outsized-VC outcome, but a real one.

---

## What this doc is *not*

- It's not a fund-raising deck. The numbers above are back-of-envelope, not modelled.
- It's not a roadmap commitment. Phases shift based on what the first three pilots teach you.
- It's not customer-facing. Banks should not see this. The production-readiness doc (`docs/sales/production-readiness.md`) is the customer version.

It's a sketch of where the next 36-48 months can plausibly go *if pilots succeed*. Re-read it after pilot 1 signs. Re-read it after pilot 1 converts. Re-read it after pilot 3 signs. Each re-read should sharpen which path is real and which is fantasy.

---

*Document version 2026-Q2. Working draft. Updated as Phase 1 signal lands.*
