# Kestrel — Production-Readiness Roadmap

**Audience**: bank IT/risk committees evaluating Kestrel during pilot. Procurement reviewers asking *"is this production-ready?"* before authorising a paid subscription.

**Document version**: 2026-Q2

---

## TL;DR

**Kestrel is past the bar for a 30-day evaluation pilot.** The platform is feature-complete, externally tested, internally instrumented, and contractually framed for evaluation use under the pilot agreement.

**Kestrel is not yet at the bar for a year-long production subscription.** Several procurement requirements that a bank's IT/risk committee reasonably demands — third-party security audit, SOC 2, signed Data Processing Agreement, documented disaster-recovery procedure, professional indemnity insurance — are still in flight or not yet in place.

The pilot is the bridge. We use the pilot window to prove the platform fits your reality. In parallel, the production-readiness work below is funded and executed so the subscription contract that follows the pilot is signable on production-grade terms — not pilot terms — by the time conversion lands.

---

## What's already in place today

These are verifiable on the live platform and in the codebase. Procurement reviewers can request artefacts under NDA.

| Capability | Evidence |
|---|---|
| Comprehensive automated test suite | 459 pytest tests passing on every commit; CI gate enforces. |
| Production deployment pipeline | Vercel for web, Render for engine + worker + beat, Supabase for Postgres. Auto-deploy on `main`. Blue-green via Vercel's atomic deployments. |
| Public status page | `kestrelfin.com/status` shows component-level uptime + recent incidents, driven by a 5-minute uptime ping ledger. |
| Audit log | Every mutation across the platform writes a row carrying user_id, org_id, action, resource_type, resource_id, IP, request_id. AI invocations log provider, model, redaction mode, input and output digests. Append-only at the policy layer; per-org isolated; no regulator override. 365-day retention with optional archive to encrypted object storage. |
| Multi-tenant isolation | Postgres Row-Level Security on every per-tenant table with verbatim policy `(org_id = auth_org_id()) OR is_regulator()`. Verified with a live production simulation as a bank CAMLCO; every per-tenant table returns the correct subset. Full `pg_policies` dump available under NDA. |
| Cross-bank persona invariants | Bank persona never sees peer-bank names (rendered as *"Peer institution N"*); match keys redacted to last four characters. Enforced in the service layer before data leaves the engine. Backed by 8 unit tests. |
| AI safety posture | Continuous prompt-injection + PII-leak red-team harness in CI on every commit. Account numbers, NIDs, phone numbers, wallet addresses, emails are masked before any payload reaches an external model. Canary checks fail the build if a model echoes injected instructions. |
| Compliance alignment (designed, not yet audited) | BB Circular 26/2024 pipeline expectations; FATF Recommendations 9 + 21 (tipping-off prohibitions and reporting-entity confidentiality enforced in code at the service boundary); Money Laundering Prevention Act 2012 + Anti-Terrorism Act 2009 STR/CTR/dissemination workflows native to the act vocabulary; Egmont IER workflow with counterparty FIU + reference + deadline. |
| Sanctions screening corpus | 27,000+ records aggregating OFAC, UN, UK FCDO, BB Domestic, refreshed daily via a scheduled Beat task. ComplyAdvantage adapter shipped for paid PEP / adverse-media when activated. |
| Data residency | Hosted production runs on Supabase Postgres in Singapore (ap-southeast-1) with the engine on Render in the same region. Single-region contractual guarantee. On-premise deployment option for tier-1 banks and regulators using the same engine + web images, with sovereign LLM hosted locally and air-gapped AI routing. |
| Disaster recovery posture | Supabase point-in-time recovery enabled. Daily automated backups with 7-day retention. *(See §Production-readiness gaps below — drill not yet practised.)* |

---

## Production-readiness gaps — the work between pilot and subscription

These are the items a serious bank IT committee will require before signing a production subscription. We're explicit about what's in flight, the timeline, and what each pilot funds.

| # | Requirement | Today | Target | Funded by |
|---|---|---|---|---|
| 1 | **External penetration test report** | Internal red-team CI suite only. No third-party report. | Engagement scheduled with a reputable firm. Report delivered within first 90 days of pilot. Findings remediated in parallel. | First paid pilot |
| 2 | **SOC 2 readiness → Type 1 → Type 2** | Internal readiness statement. No formal audit. | SOC 2 Type 1 audit kicked off during pilot 1; Type 1 report by month 6, Type 2 (12-month observation) by month 18. Industry-standard timeline for early-stage AML platforms. | First two paid pilots |
| 3 | **DR drill: documented restore procedure with measured RTO/RPO** | Backups exist; restore not yet practised end-to-end on production data. | Drill executed and documented inside the first 30 days of pilot 1. Procedure published as part of every customer's onboarding pack. | Self-funded — engineering effort, not capex |
| 4 | **Errors-and-omissions / cyber liability insurance** | Not yet bound. | Bound before first production subscription signs. ~$5-15k/year — cost predictable. Proof of cover provided to every customer on request. | First paid pilot |
| 5 | **Signed Data Processing Agreement** | Pilot agreement covers data terms for evaluation use only. No standalone DPA. | DPA template lawyer-drafted during pilot 1, executed alongside subscription contract. GDPR-flavoured terms even where Bangladesh law doesn't strictly require them — banks read DPAs against international expectations. | Lawyer review of pilot 1's pilot agreement extends to DPA |
| 6 | **Subscription Agreement** (for production conversion) | Pilot agreement template ends at *"convert to Subscription Agreement on contract"*; subscription template not yet drafted. | Drafted during pilot 1 with input from the converting bank's legal team. Subsequent banks adopt the same shape with negotiated specifics. | First paid pilot |
| 7 | **Documented incident response + on-call rotation** | Internal runbook (`docs/RUNBOOK.md`); founder is the human in the loop. | First operations engineer hired before pilot 3 conversion. 24/7 on-call rotation contractually committed for production tier; pilot tier remains best-effort during business hours. | Pilot revenue |
| 8 | **Bangladesh Bank regulator approval (if required)** | Not formally sought — pilots are evaluation use under the Bank's existing AML control framework. | If applicable BB circulars require third-party AML vendor approval, the application is filed by the converting bank during pilot, with Kestrel's full co-operation on the technical packet. | Joint pilot work |
| 9 | **Source-code escrow** | Promised in pricing copy; not yet arranged. | Escrow agreement set up with a third-party escrow agent (Iron Mountain or local equivalent) before first Enterprise tier subscription signs. | Self-funded |
| 10 | **Bus-factor: at least one engineer beyond founder** | Single founder operates the platform. | First hire (full-time SRE / DevOps) targeted within 60 days of pilot 1 signing. Second engineer (back-end, AML domain) within 6 months. | Pilot revenue |

---

## Why we're transparent about this

Pretending production-ready when we're not gets caught in your procurement review. Once caught, the relationship burns. So we're explicit:

- **The pilot is the right move now.** It's contractually framed as evaluation use under §8.3 of the pilot agreement (*"hold harmless during pilot"*). No production SLA applies. The pilot fee covers the platform access and our pilot-period support, not a regulated production guarantee.
- **The production-readiness work is fully funded by the pilot revenue.** The pen test, the SOC 2 audit kickoff, the insurance binding, the first SRE hire are budgeted against pilot fees from your bank and the next two banks. By the time you convert, those items have shifted from *"in flight"* to *"in hand"*.
- **The subscription conversion happens against production-grade contract terms, not pilot-grade ones.** When the pilot agreement converts to a Subscription Agreement, the new contract carries: 99.5% (Pro) or 99.9% (Enterprise) uptime SLA backed by liquidated damages; 24/7 incident response committed in writing; pen-test and SOC 2 reports included as schedules; DPA executed; insurance-backed liability cap raised from "pilot fee" to a commercially-reasonable production multiple.

---

## Realistic timeline — pilot signing to production live

For a bank signing a paid pilot in **Q3 2026**:

| Month | Pilot milestone | Production-readiness milestone |
|---|---|---|
| 0 | Pilot signed, kickoff call, tenant provisioned | Pen test engagement booked |
| 1 | First STRs imported, CAMLCO live in tenant | DR drill executed and documented |
| 2 | Cross-bank intelligence first hits surfaced; first AI-drafted STR submitted | Pen test report delivered; remediation in parallel |
| 3 | Pilot success-criteria assessment (day 30 + 14 conversion window) | E&O insurance bound; SOC 2 Type 1 kickoff |
| 4-5 | If converting: subscription contract drafting + DPA + (if required) BB regulatory packet | First SRE hire onboarded |
| 6 | **Production subscription begins.** Live in CAMLCO daily workflow. | SOC 2 Type 1 report in hand; pen test clean; insurance bound; on-call rotation active. |

**Total pilot-signed → production-live: 6 months.**

This timeline is built specifically for the *first* bank — pilot 1. By pilot 3 the production-readiness work is largely done; the timeline compresses to ~3 months from signed pilot to production conversion.

---

## What we ask of pilot banks

A pilot is the right place to be early. We extend the half-price-for-six-months first-mover discount to the first three pilot banks who sign before **[Date]**, in exchange for being identified as named reference customers in our procurement materials. The discount is per the pilot agreement §3.4.

Two practical asks during pilot:

1. **A named CAMLCO who has the time** to use the platform daily for 30 days. The pilot succeeds or fails on whether your CAMLCO actually uses it, not on whether your CTO checks a box. We'd rather a one-CAMLCO pilot that runs deep than a five-seat pilot that no one logs into.
2. **Your goAML XML extracts**, of whatever scope you choose. The first week runs on synthetic demo data; from week two onward, your CAMLCO works against real signal from your own bank. Your data stays exclusively yours (pilot agreement §6); deletion within 15 business days of pilot end is contractually committed (§6.4).

---

## Direct

Questions during pilot evaluation:
**Ripon Chowdhury** · Founder
intake@kestrelfin.com
Dhaka, Bangladesh
**Enso Intelligence Inc.**

`kestrelfin.com`

---

*Document version 2026-Q2. Updated quarterly as production-readiness milestones land. Latest is published at `kestrelfin.com/docs/security` (companion to this document, focused on security posture specifically).*
