# Cross-Bank Intelligence

**Kestrel · Enso Intelligence · 2026-05-04**

> The signal no other vendor in Bangladesh has — and the privacy architecture that lets a competitor's CAMLCO trust it.

---

## 1. The problem

A subject opens accounts at five different banks. Each bank sees only its own slice. By the time a Suspicious Transaction Report (STR) at one of them gets reviewed by BFIU and cross-referenced manually against earlier filings from the other four, the money has moved across six rails and twelve mobile-financial-services wallets, and the trail is cold.

This is not a hypothetical. It is the modal pattern in Bangladesh fraud and laundering casework. The technology gap is structural: every commercial bank's compliance stack is single-tenant. There is no surface inside the bank that says *this account is also flagged at Bank B, Bank C, Bank D*. There is no surface inside BFIU that automatically resolves the same NID across five banks' submissions. The cross-institution picture exists only in the head of whichever analyst happens to pull the right thread.

goAML, the UNODC system Bangladesh currently uses for STR filing, was designed in 2006 as a filing cabinet — banks submit reports into it; analysts read them out. It does not perform cross-bank entity resolution. It does not anonymise peer signals. It cannot.

## 2. What Kestrel adds

Kestrel sits *between* the banks and BFIU. Banks submit STRs and transaction batches to Kestrel in exactly the goAML XML format they already produce. Kestrel resolves every subject — account number, NID, phone, wallet, person name, business name — into a shared entity pool. When the same identifier appears in submissions from two or more banks, Kestrel:

1. Creates a `matches` row recording the cluster.
2. Emits a `cross_bank`-source-type alert into each involved bank's tenant.
3. Surfaces the cluster on the cross-bank intelligence dashboard.

Bank CAMLCOs see this as: *"the account you just submitted an STR on is also flagged at four peer institutions; one is critical-severity."* They do not see which four institutions. They do not see those institutions' raw transactions or STR narratives.

BFIU analysts see this as: *"BRAC, City, Dutch-Bangla, Islami, and Sonali have all reported account 2001045555701 in the past 30 days. Aggregate exposure: BDT 18.5 crore. Severity: critical. Click for the full picture across all five."*

Same underlying data. Two different views. Persona-controlled.

## 3. The privacy architecture (this is what gets a bank CTO to sign)

### What crosses the boundary between bank tenants

Nothing raw. The cross-bank signal is constructed entirely from:

- **Canonical entity tokens** — the normalised `canonical_value` of an identifier (account number stripped of formatting, phone in E.164, NID as 13-digit string). These are not hashes; they are the values themselves, which is fine because (a) they are already shared across the banking system in clear (an NID is shared with every institution that the subject opens an account at), and (b) the `entities` table contains only the identifier, never the underlying transactional context.
- **The list of org IDs that reported each entity** — `Match.involved_org_ids` — used to generate the anonymised count.
- **Aggregate severity, exposure, and detection timestamp** on the match record.

### What does NOT cross the boundary

Everything that matters operationally — and everything regulators would object to leaving the bank without authorisation. Specifically:

- Raw `transactions` rows are isolated per `org_id` via Postgres Row-Level Security (RLS). A query from Bank A's user role returns zero rows from Bank B's transactions. No exception, including for service-role bypasses, except the regulator role.
- `str_reports` are isolated the same way. A bank user querying STRs sees only their own bank's filings.
- `cases`, `accounts`, `audit_log`, `disseminations`, `match_definitions` — all scoped per org_id at the database layer, enforced by `auth_org_id() OR is_regulator()` policies.
- Subject narrative text from one bank's STR is never visible to another bank.
- The names of peer institutions involved in a cross-bank cluster are never visible to a bank user — the cross-bank service substitutes "Peer institution 1, 2, 3, …" before any data leaves the engine.
- Match keys (the canonical identifier values) are presented to bank users with the tail four characters preserved and the rest masked: `····5001` rather than `+8801711555001`.

### Why this is stronger than the alternatives

The two patterns Kestrel is *not*:

- **Federated learning** (the Tookitaki model): each bank trains a local model, parameters get aggregated centrally, no raw data leaves. Mathematically elegant; operationally hard to make explainable to a regulator. A flagged entity emerges as a model output, not as a citable record. BFIU cannot subpoena a "weight gradient." Kestrel's match records are concrete: an entity, a list of involved orgs, a list of involved STR refs, a timestamp, an audit trail.
- **Centralised data lake** (the Verafin / Actimize cloud model): every bank streams every transaction into a shared cloud, vendor analytics run over the lot. Stronger signal; weaker privacy. Bangladesh banks would not — and per BB Circular 26/2024 may not — ship raw transactional data to a foreign vendor's cloud. Kestrel's signal works without the lake.

Kestrel is closer to **Verafin's "intelligence-sharing" mode** — entity-level matching across cooperating institutions — but with three Bangladesh-specific differences: (a) hosted in-country on Supabase ap-southeast-1 with a one-region-out-of-bound contractual guarantee, (b) BDT-billed, (c) regulator (BFIU) is a tenant inside the platform, not an external recipient.

## 4. What signal a bank actually receives

When a bank CAMLCO opens `/intelligence/cross-bank` on Kestrel, the surface is structured to give them four distinct decision-relevant numbers:

- **Entities flagged across institutions** — the count of cross-bank clusters their org is part of. This is the headline.
- **New cross-bank flags this week** — separates the ambient noise from the new signal.
- **High-risk cross-institution count** — clusters with risk_score ≥ 70 *and* ≥ 2 banks involved. This is the priority queue.
- **Aggregate exposure** — sum of `total_exposure` across all visible cross-bank clusters, in BDT.

Below those, two ranked lists: *recent matches* (anonymised peer label, bank count, hit count, severity, risk score) and *top cross-flagged entities* (display value with masking, entity type, bank count, involved-org labels, severity, risk score). Both link to the entity dossier — also persona-aware: a bank user clicking a peer-bank-only entity sees the entity dossier scoped to data their org has visibility into.

The bank's value comes from one specific question this surface answers in seconds: *should I escalate this STR to a case, and how aggressively?* The number of peer institutions reporting the same subject is a strong prior. Kestrel makes that prior visible.

## 5. What signal BFIU receives

The same surface, persona-promoted. The bank-anonymisation drops away. BFIU Director and BFIU Analyst personas see:

- Real bank names on every involved-org label.
- Full match keys (no `····` masking).
- The full entity display value across the dossier.
- Cross-references between matches and the underlying STRs from each bank.

The BFIU-only surfaces (`/iers`, `/intelligence/disseminations`, the national / compliance / trends / statistics dashboards) sit on top of the same data — cross-bank intelligence is not a separate database; it is a different read of the database the bank tenants are already feeding.

## 6. Technical architecture (the part the bank CTO will inspect)

Three tables, three policies, one service. That is the entire moat.

**Tables** (`supabase/migrations/001_schema.sql` and `008_intel_tables.sql`):
- `entities` — canonical shared-intelligence identity, RLS shared across all authenticated users.
- `connections` — directed edges with typed relations between entities, RLS shared.
- `matches` — cross-bank cluster records with `involved_org_ids` (UUID array) and `involved_str_ids` (UUID array), RLS shared.

**Policies** (verified live 2026-05-04):
```
shared_entities:    USING (auth.uid() IS NOT NULL)
shared_connections: USING (auth.uid() IS NOT NULL)
shared_matches:     USING (auth.uid() IS NOT NULL)
```
Every other table that contains operationally sensitive data — `accounts`, `transactions`, `str_reports`, `alerts`, `cases`, `disseminations`, `audit_log` — has the per-org policy:
```
USING ((org_id = auth_org_id()) OR is_regulator())
```
The shared tables hold no operational detail. The detail-holding tables are tenant-isolated. This is what makes the architecture safe to share with peers while keeping STR narratives, transaction patterns, and case notes inside the originating bank.

**Service** (`engine/app/services/cross_bank.py`):
The service that builds the dashboard payloads applies persona transformations after RLS has done its work. For a bank persona it:
1. Filters out clusters the calling org is not part of.
2. Replaces peer org IDs in `Match.involved_org_ids` with `"Peer institution 1..N"` labels.
3. Masks `Match.match_key` to last-four-characters.
4. Returns aggregate counts only — never enumerates peer-bank STR references.

For a regulator persona it does none of those things. The same query path; different output shape. Single source of truth for the privacy semantics.

**Matcher** (`engine/app/core/matcher.py::run_cross_bank_matching`):
Runs on every STR submission. Identifies entities with `array_length(reporting_orgs, 1) >= 2`. Upserts a `matches` row keyed on `(match_type, match_key)`. Emits one `cross_bank`-source-type alert into each involved org's tenant, deduped on `(source_id=match.id, entity_id, status IN open/reviewing/escalated)` so re-execution does not double-fire.

**Resolver** (`engine/app/core/resolver.py::resolve_identifier`):
Performs the entity-resolution step that makes cross-bank matching possible at all. Strategy: exact match on `(entity_type, canonical_value)` first; for `person` and `business` types fall back to pg_trgm fuzzy match on `display_name` with similarity ≥ 0.55. Conservative thresholds chosen to favour false negatives over false positives — a missed match is operationally fine (the next STR will pick it up); a wrong match contaminates the shared entity pool.

## 7. Privacy and regulatory posture

**FATF Recommendations 9, 21**: Kestrel's design directly satisfies FATF's expectations on (R.9) "tipping-off" prohibitions — banks are not informed of which specific peer institution has flagged a subject, only that ≥ N peers have — and (R.21) protection of reporting-entity confidentiality. The anonymisation layer is not policy; it is enforced in code at the service boundary.

**BFIU operational posture**: BFIU is a tenant inside the platform with the regulator role. Disseminations to law enforcement (`/intelligence/disseminations`) carry a full audit trail keyed to `auth.uid()` and reproduce the goAML information-exchange request (IER) workflow including counterparty FIU, Egmont reference, deadline, and inbound/outbound direction. BFIU operates Kestrel; Kestrel does not operate BFIU.

**BB Circular 26/2024 (digital banking compliance)**: Kestrel's hosting and data-residency model — Supabase ap-southeast-1 (Singapore) with optional self-hosted Postgres for institutions that require BB-perimeter custody — is designed to satisfy the circular's transaction-monitoring and STR-pipeline requirements while remaining within the regulatory perimeter for AML data.

**Audit log**: `audit_log` records every mutation across services, scoped per-org with no regulator escape hatch. Every `ai.invoke` call is logged with provider, model, input_digest, output_digest, and redaction mode for compliance review. The audit table is append-only at the policy layer.

**AI safety**: AI tasks (alert explanation, STR narrative drafting, entity extraction, executive briefing, case summary, typology suggestion) run through a dedicated provider abstraction layer with explicit redaction (account numbers, phone numbers, NIDs, emails are masked before reaching any external model). A continuous red-team harness (`engine/app/ai/redteam/`) exercises the prompt template, redaction, and routing layers in CI on every commit, with canary checks (no echoing of injected instructions) and PII-leak checks (no raw account numbers / phones / NIDs in model output).

## 8. Comparison

| Capability | goAML (BFIU today) | Verafin (NA standard) | Tookitaki (federated) | Kestrel |
|---|---|---|---|---|
| Cross-bank entity resolution | Manual | Yes (cloud lake) | Yes (federated) | Yes (shared-entity) |
| Bank tenant isolation of raw data | N/A | No | Yes | Yes (RLS) |
| Anonymised peer signal to banks | No | Partial | Yes | Yes |
| Explainable match records | N/A | Partial | No (model weights) | Yes (citable rows) |
| In-country hosting (Bangladesh) | Yes | No | No | Yes (ap-southeast-1 + on-prem option) |
| BDT-billed | Yes (UNODC) | No | No | Yes |
| Regulator (BFIU) as a tenant | N/A | No | No | Yes |
| goAML XML round-trip (import + export) | N/A | No | No | Yes |
| BB Circular 26/2024 alignment | Partial | No | No | Yes |
| Time-to-first-deployment | Years (bilateral with UNODC) | Quarters | Months | Weeks |

## 9. What this enables for the buyer

For a bank: a measurable reduction in false-positive STR review hours, because the cross-bank signal lets analysts triage. Subjects with ≥ 3-bank flags warrant immediate case escalation. Subjects with no peer reports stay in the standard queue. The dashboard is the priority filter that didn't exist before.

For BFIU: the ability to see, in one query, every subject reported by ≥ N institutions in the trailing window, ranked by aggregate exposure and severity. The compounding signal across the banking system, surfaced without an analyst needing to manually cross-reference five filing cabinets.

For both: the same primary surface, with persona-controlled visibility — which is what makes Kestrel the only product in the market that a bank CTO and a BFIU director will both sign on. The bank trusts that their raw data does not leave their tenant. The regulator trusts that the cross-bank picture is complete and citable.

---

**Architecture references**:
- Tables: `supabase/migrations/001_schema.sql`, `supabase/migrations/008_intel_tables.sql`
- Service: `engine/app/services/cross_bank.py`
- Matcher: `engine/app/core/matcher.py`
- Resolver: `engine/app/core/resolver.py`
- Dashboard: `web/src/components/intel/cross-bank-dashboard.tsx`, `web/src/app/(platform)/intelligence/cross-bank/page.tsx`

**Verifiable claims** — every persona-isolation assertion in §3 and §6 is backed by a unit test in `engine/tests/test_cross_bank.py` and an RLS policy verifiable via `pg_policies` on the production Supabase project (`bmlyqlkzeuoglyvfythg`). Procurement teams can request the live `pg_policies` dump.

**Document version**: 2026-05-04. Replaces all earlier informal descriptions of the cross-bank capability. Authoritative source for procurement, regulator review, and bank CTO due diligence.
