# Leave-behind — Regulator (BFIU + peer FIUs)

**Purpose**: one printed page, front and back, handed to the BFIU Director or Joint Director at the end of the demo. Goal: the document survives the meeting, gets walked into BFIU procurement on its own, and frames the conversation as *national-infrastructure procurement*, not as SaaS purchase.

**Print**: A4, two-sided, monochrome, IBM Plex Sans for body / IBM Plex Mono for IDs. Black on white. No glossy paper. Heavier stock if available — regulator leave-behinds end up in folders, they need to feel substantive in the hand.

---

## ┼ FRONT

# Kestrel
### Financial crime intelligence for Bangladesh's regulator.

---

**Why goAML can't do what BFIU now needs.**

goAML, the UNODC system Bangladesh uses for STR filing, was designed in 2006 as a filing cabinet. Banks submit reports into it; analysts read them out. It does not perform cross-bank entity resolution. It does not anonymise peer signals. It cannot pre-compute a national typology trend. It cannot serve a BFIU director a network graph on a subject in three seconds. It was never designed to.

The compounding signal across the banking system — the entity flagged at five banks in thirty days, the layering pattern that touches NPSB and bKash and a TBML LC in the same window — exists only when the data is read together. goAML reads it apart. Kestrel reads it together.

---

**What Kestrel adds, in production today.**

**Cross-bank entity resolution at full strength.** Every STR submitted by every Kestrel-connected bank is matched against every other STR. The shared entity pool surfaces clusters by NID, phone, account, wallet, device. Bank-side analysts see anonymised signal — *"your subject is also flagged at four peer institutions"* — without seeing peer-bank books. BFIU sees the full picture: real bank names, full match keys, aggregate exposure across the system, FATF Recommendation 9 compliance built in.

**The complete goAML vocabulary, modernised.** Catalogue Search, IER, Match Definitions, Disseminations, Reference Tables, Statistics, Scheduled Processes, the eleven STR / SAR / CTR / TBML / IER / complaint / adverse-media variants — every screen your analysts know, in the same vocabulary, on a modern web stack. No Windows desktop client. No vendor consultation cycle to add a custom rule. JSON-DSL match definitions your senior analysts author themselves.

**Egmont workflow, native.** Inbound and outbound IERs to peer FIUs, counterparty FIU dropdown, Egmont reference, deadline tracking, response narrative — all dispatched in goAML XML format your peer FIU expects. The dissemination ledger is append-only, audit-trailed, exportable to your committee in one click.

**AI-native intelligence, with provenance.** Every alert opens with an AI-drafted explanation citing the rule that fired and the evidence behind it. STR narrative drafts are generated on submit. Investigation agents walk a subject across hops. The complete AI invocation log records provider, model, redaction mode, input and output digests — every prompt is logged for compliance review.

---

**Production state, today.**

| 134 | Production API routes across STR / CTR / IER / case / screening / realtime / agentic. |
| 459 | Pytest suite, all passing on every commit. |
| 11 | Scheduled jobs in production, including audit retention and watchlist refresh. |
| 27,481 | Sanctions records screened daily, OFAC + UN + UK FCDO, refreshed every 24h. |
| 99.9% | Uptime SLA at the regulator tier. Live status page. |

---

## ┼ BACK

### Deployment options.

**Option A · Hosted.** Production runs on Supabase Postgres in Singapore (ap-southeast-1) with the engine on Render in the same region. Single-region contractual guarantee. Fastest path to deployment; nothing for BFIU to install.

**Option B · On-premise inside BFIU's data centre.** Same engine image, same web image, sovereign LLM running on your infrastructure (vLLM-compatible endpoint). Air-gapped AI routing — no outbound network calls to OpenAI or Anthropic. Watchlist refresh runs from operator-supplied source archives instead of live HTTP. License file. Optional, opt-in telemetry pingback.

**Option C · Hybrid.** BFIU on-premise, banks on the hosted platform, peering at the cross-bank intelligence layer. Banks file in goAML XML (their existing pipeline); BFIU reads the resolved view from inside BFIU's perimeter. The cross-bank entity pool is the only data that crosses the boundary, and it crosses anonymised on the bank side and decrypted only inside BFIU.

All three options carry the same core engine, the same API surface, and the same upgrade cadence. The choice is operational, not functional.

---

### Procurement framing.

**Multi-year contract. Scope-priced. Not on the public site.**

National regulator deployments are different from bank SaaS subscriptions. The contract bundles:

- Multi-year licence to the platform
- On-premise deployment (when chosen) including engineering on-site
- Dedicated technical account manager named in the contract
- Analyst training programme tailored to BFIU's existing workflows
- Custom rule authoring + the national typology library specific to Bangladesh
- Direct access to platform engineering for any feature request that is regulator-specific
- Source-code escrow for business continuity
- Service-level commitments backed by liquidated damages

Because every regulator deployment is differently scoped, the price is structured against scope, not against a fixed sticker. The proposal-request form on `kestrelfin.com/contact?audience=regulator` walks BFIU's procurement team through the scope inputs we need to issue a written proposal within ten business days.

---

### Compliance posture.

- **BB Circular 26/2024** — AI AML compliance pipeline aligned by design.
- **FATF Recommendations 9 & 21** — tipping-off prohibitions and reporting-entity confidentiality enforced at the service boundary in code.
- **Money Laundering Prevention Act, 2012** + **Anti-Terrorism Act, 2009** — STR / CTR / dissemination workflow native to the act vocabulary.
- **Egmont Group intelligence exchange** — IER workflow with counterparty FIU + reference + deadline.
- **Audit log** — append-only at the policy layer; per-org isolation; no regulator escape hatch.
- **AI safety** — continuous prompt-injection and PII-leak red-team harness in CI on every commit.

Full Postgres `pg_policies` dump and tenant-isolation simulation transcript available under NDA on request.

---

### What happens next.

Submit the proposal-request form at `kestrelfin.com/contact?audience=regulator` with deployment scope, country, timeline, and procurement vehicle.

We respond with a written proposal within ten business days, including a deployment-options matrix and a draft contract framework.

For peer-FIU references and the technical architecture deep-dive, request access to the engineering ground-truth document under NDA.

---

### Direct.

**Ripon Chowdhury** · Founder
intake@kestrelfin.com
Dhaka, Bangladesh
**Enso Intelligence Inc.**

`kestrelfin.com`

---

*Document version 2026-Q2. National-deployment terms are contracted directly. Source-code escrow and liquidated damages are negotiated per deployment.*
