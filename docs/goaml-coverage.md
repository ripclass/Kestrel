# Kestrel vs. goAML — Coverage and Design Decisions

_Last updated: 2026-05-04_

## Summary

Kestrel provides complete functional coverage of goAML for BFIU's regulatory and operational workflows while modernising the interface and adding AI-native intelligence capabilities goAML cannot provide. Banks continue filing in the goAML XML format they already know; BFIU analysts continue using the vocabulary they learned (IER, SAR, CTR, Catalogue Search, Match Definitions, Disseminations); and the underlying architecture is a modern web stack with real-time search, cross-bank entity resolution, and AI-assisted alert explanations.

This document lists every goAML feature area, Kestrel's approach, and the rationale for any deviation. It is the procurement-facing answer to "can Kestrel replace goAML for BFIU?"

## Coverage matrix

| goAML capability | Kestrel approach | Notes |
|---|---|---|
| **Reports — STR** | First-class with AI narrative drafting, AI alert explanations, cross-bank resolution on submit | `/strs` + native lifecycle (draft → submitted → under_review → flagged → confirmed / dismissed). Every STR submit runs `run_str_pipeline` — resolves identifiers, emits cross-bank matches, escalates alerts. |
| **Reports — SAR** | First-class variant | `report_type='sar'`, same lifecycle as STR. |
| **Reports — CTR** | First-class with bulk import + dedicated table | `report_type='ctr'` for individual reports; bulk CTR table `cash_transaction_reports` for the high-volume flows. |
| **Reports — Suspected TBML** | First-class variant with trade-specific columns | `report_type='tbml'` + `tbml_invoice_value`, `tbml_declared_value`, `tbml_lc_reference`, `tbml_hs_code`, `tbml_commodity`, `tbml_counterparty_country`. |
| **Reports — Complaint Report** | First-class variant | `report_type='complaint'`. |
| **Reports — FIU Escalated Report** | First-class variant | `report_type='escalated'`. |
| **Reports — Information Exchange Request (IER)** | First-class with dedicated Egmont workflow | `report_type='ier'` with direction (inbound/outbound) + counterparty FIU + Egmont ref + deadline + request/response narratives. Dedicated `/iers` surface with Inbound/Outbound tabs, respond, and close actions. |
| **Reports — Internal Report** | First-class variant | `report_type='internal'`, BFIU-only. |
| **Reports — Adverse Media-STR** | First-class variant with media provenance | `report_type='adverse_media_str'` + `media_source`, `media_url`, `media_published_at`. |
| **Reports — Adverse Media-SAR** | First-class variant with media provenance | `report_type='adverse_media_sar'`. |
| **Reports — Additional Information File** | First-class supplementary workflow | `report_type='additional_info'` + `supplements_report_id` FK. "Supplement this report" button on every STR detail page; "Supplements" section on parent reports listing all children. Subject identity auto-inherits from the parent. |
| **XML report upload (goAML format)** | Supported via `POST /str-reports/import-xml` | Banks continue emitting goAML-format XML from their existing pipelines — no rewrite. Parser (`lxml`) is defensive: extracts header + transactions + subjects, maps `submission_code` to Kestrel's `report_type`, ingests transactions tagged with the import batch's `run_id`, resolves every subject into the shared entity pool. |
| **XML report export** | Supported via `GET /str-reports/{id}/export.xml` | Exact inverse of the parser. BFIU can hand off a Kestrel STR in goAML format to peer FIUs or legacy systems. Emits `primary_subject`, `ier` block when variant='ier', and every linked transaction. |
| **Catalogue Search — 12 labelled lookups** | Unified omnisearch with 12 labelled entry points at `/investigate/catalogue` | One `pg_trgm` + ILIKE search handles every lookup; the 12 tiles (Account / Person / Entity / Address / Text / Quick Finder / Transaction / Report / Intelligence Report / Templates / Journal / Dissemination Lookup) preserve the goAML vocabulary while routing into Kestrel's existing surfaces. Labels carry their goAML rationale in each tile's caption. |
| **New Subjects — Account / Person / Entity** | Unified "New subject" flow with three tabs at `/intelligence/entities/new` | Each tab has focused form fields (Account: number + name + bank + phone + NID; Person: name + NID + phone + wallet + aliases; Entity: business name + registration + industry + UBO). Every submission runs through the resolver and emits pairwise `same_owner` connections so the graph picks up linkage immediately. |
| **Business Processes — Cases** | First-class cases with AI summaries + case-pack PDF export | `cases.variant='standard'`. WeasyPrint PDF export with "Confidential — BFIU" watermark at `/cases/{id}/export.pdf`. |
| **Business Processes — Case Proposals** | `cases.variant='proposal'` + proposal decision flow | Kanban view (pending / approved / rejected) on `/cases?variant=proposal`. Manager+ can approve (flips variant to 'standard') or reject; decision + decider + timestamp recorded. |
| **Business Processes — Requests For Info** | `cases.variant='rfi'` with `requested_by` / `requested_from` | RFI routing between analysts; case workspace surfaces the routing info. |
| **Business Processes — Operations / Projects** | `cases.variant='operation'` and `cases.variant='project'` with `parent_case_id` | Multi-case operations and long-running thematic projects linked via parent FK. |
| **Business Processes — Escalated / Complaint / Adverse Media Cases** | `cases.variant='escalated'` / `'complaint'` / `'adverse_media'` | Filter pills on the case board drop the view to any variant. |
| **Matching — System Rules** | 8 pre-built YAML rules (rapid_cashout, fan_in_burst, fan_out_burst, structuring, layering, first_time_high_value, dormant_spike, proximity_to_bad) with all 11 modifier conditions wired (4 graph-lookup modifiers — `proximity_to_flagged ≤ 2`, `involves_multiple_banks`, `circular_flow_detected`, `target_confidence > 0.8` — landed 2026-04-19 in commit `a55d65d`). | Runs on every scan via `run_scan_pipeline`. |
| **Matching — Match Definitions / Executions** | Admin-configurable custom rules in `match_definitions` + `match_executions` tables with a real JSON-DSL executor | `/admin/match-definitions` — manager+ can create a JSON-defined rule, toggle active, run it, or delete. The executor (`engine/app/core/match_dsl.py`, commit `3ca6528`) validates the DSL, evaluates against every Entity the caller can see, emits alerts deduped by `(source_id, entity_id, status)`, and stamps `last_execution_at`. Migration 011 added `match_definition` to the `alerts.source_type` CHECK. |
| **Intel — Profiles (Saved Queries)** | Supported via `saved_queries` table | `/intelligence/saved-queries` with per-user + org-shared visibility. Typed: entity_search / transaction_search / str_filter / alert_filter / case_filter / custom. Tracks `run_count` and `last_run_at`. |
| **Intel — Create Diagram** | React Flow canvas at `/investigate/diagram` | Search for entities, drop them on the canvas, drag to connect, save to case or STR. Canvas state round-trips through the `diagrams.graph_definition` JSONB column. |
| **Intel — Message Board** | **Excluded** — see "Deliberate exclusions" below. | |
| **Dissemination tracking** | First-class `disseminations` table + audit ledger | `/intelligence/disseminations` list + detail. "Disseminate" action button drops into Alert, Case, Entity dossier, and STR workspaces — opens a modal pre-seeded with the source record, posts to `/disseminations`, and emits an audit log entry. Recipients typed by `recipient_type` (law_enforcement / regulator / foreign_fiu / prosecutor / other). |
| **Reference Tables / Lookup Master** | `reference_tables` with banks, branches, countries, channels, categories, currencies, agencies | `/admin/reference-tables` — regulator admin CRUD. Seeded day-one with 10 channels, 12 AML categories, 64 Bangladesh banks + MFS providers (tagged by category), 64 ISO-3166 country codes (BFIU-relevant subset), 30 ISO-4217 currency codes, and 17 recipient agencies (Bangladesh LE + regulators + Egmont peer FIUs). |
| **Statistics** | `/reports/statistics` + purpose-built dashboards | Recharts-rendered dashboards over `/admin/statistics`: reports-by-type-by-month (stacked), reports-by-org (horizontal bar), CTR volume by month, disseminations by recipient (pie), case outcomes (pie), avg time-to-review by report type. |
| **Scheduled Processes** | `/admin/schedules` read-only status view + live Celery worker ping | 3 declared jobs running on a Celery Beat schedule pinned to Asia/Dhaka (commit `b561949`): `nightly_scan_all_orgs` at 02:00, `daily_digest_bfiu` at 06:30, `weekly_compliance_report` Mon at 05:00. Live worker probe shows attached workers. |
| **User / Role / Workflow Maintenance** | Supabase Auth + persona system | `/admin/team` manages roles (superadmin / admin / manager / analyst / viewer) and personas (bfiu_director / bfiu_analyst / bank_camlco). RLS enforces per-org scoping with regulator overrides. |
| **Audit log / Journal** | `audit_log` table with every mutation + X-Request-ID tracing | Every service-layer mutation writes a row with `action`, `resource_type`, `resource_id`, `user_id`, `org_id`, `ip`, and request details. Phase 10 observability adds per-request IDs that thread through structured JSON logs. AI invocations log `provider`, `model`, `input_digest`, `output_digest`, `redaction_mode` for compliance review (`action='ai.invoke'`). |
| **AI safety — red-team harness** | Continuous prompt-injection / PII-leak / canary-echo regression suite (commit `d122e7d`) | `engine/app/ai/redteam/{corpus,rubric}.py` + `tests/test_ai_redteam.py`. 14 fixtures across all 6 AITaskName values cover injected canaries (must NOT echo), PII embedded in keyed fields (must be redacted before reaching any provider), empty/extreme inputs. Runs in CI today against the heuristic provider; flipping `skip_canary=False` once real provider keys are configured turns canary-echo checks into a hard CI gate against live model output. |
| **File — PDF Export** | WeasyPrint case-pack PDF at `/cases/{id}/export.pdf` | Watermarked "Confidential — BFIU". |
| **File — Excel Export** | `GET /str-reports/export.xlsx`, `/alerts/export.xlsx`, `/disseminations/export.xlsx`, `/intelligence/entities/export.xlsx` | openpyxl-rendered workbooks, respect query filters, download via a single "Export Excel" button on each list page. |
| **File — XML Export** | `GET /str-reports/{id}/export.xml` | goAML-format XML, inverse of the import parser. |
| **File — XML Import** | `POST /str-reports/import-xml` | See above. |
| **File — Print** | Browser `@media print` stylesheet on major pages | |
| **File — Retrieve / Clear Criteria** | Filter bars reset on change + real-time results | No "retrieve" button needed — queries run immediately on filter change. |
| **File — Graph** | Automatic network graph on every entity dossier + optional manual diagram builder | |
| **File — Change Password** | Supabase Auth reset flow | |
| **File — Pivot Table** | **Excluded** — see "Deliberate exclusions" below. | |
| **File — Grid Layout save/load/reset** | **Excluded** — see "Deliberate exclusions" below. | |
| **File — Translate MDI** | **Excluded** — see "Deliberate exclusions" below. | |
| **Localization** | English + Bangla (selective, growing) | Phase-rolled. |
| **ESW Configurations, PAE Tab Configuration, Report Topic Measure Mapping, XML Rejection Rules, Custom Numbering, Transaction Role Orientation, Group User Mapping, Agency Group Mapping, Group Based Data Filtering, Schema XML View, Data Correction tool** | **Excluded** — see "Deliberate exclusions" below. | These are goAML-internal configuration mechanisms. |

## Deliberate exclusions

The following goAML features are NOT implemented in Kestrel. Each has a specific rationale.

### Message Board (Intel menu)

**Excluded.** Built-in internal messaging is a 2006 enterprise pattern that underperforms dedicated communication tools. Kestrel provides contextual @-mentions and notes directly on cases, alerts, entities, and STRs — where the conversation needs to happen. Email notifications and webhook integrations connect to BFIU's existing channels. The stale Message Board pattern is replaced by conversations anchored to the work they're about, which is safer and auditable.

### Pivot Table (File menu)

**Excluded.** Kestrel's reporting views (national dashboard, compliance scorecard, trend analysis, operational statistics) are purpose-built for financial intelligence workflows. For ad-hoc pivoting, analysts export filtered datasets to Excel at any point and use Excel's own pivoting — which is more powerful than goAML's embedded pivot table. The goAML Pivot Table was a generic BI tool bundled into AML software; we replace it with AML-tuned analytics plus the export path to best-in-class tools.

### Schema XML View (System Admin)

**Excluded.** Kestrel is introspectable via the OpenAPI specification auto-generated at `/docs`. This is a standards-based API explorer that also enables automation, integration, and testing — capabilities the static XML schema view cannot provide.

### Grid Layout Save / Load / Reset (File menu)

**Excluded.** Kestrel uses modern web UI patterns (responsive layouts, persistent user preferences via Supabase). Per-page grid layout serialisation is an artefact of desktop software that doesn't apply to the web. Analysts' preferences (column visibility, filter state) can be saved explicitly through Intel → Profiles (Saved Queries) rather than implicitly through grid layouts.

### Translate MDI (File menu)

**Excluded.** Localisation is handled through per-user language preferences (English / Bangla) at the application level rather than per-window translation. This is the modern i18n pattern.

### ESW Configurations, PAE Tab Configuration, Report Topic Measure Mapping, XML Rejection Rules, Custom Numbering, Transaction Role Orientation, Group User Mapping, Agency Group Mapping, Group Based Data Filtering, Data Correction tool (Management menu)

**Excluded.** These are goAML-internal configuration mechanisms that exist because goAML is a customisable off-the-shelf product serving many FIUs with different regulatory frameworks. Kestrel is purpose-built for Bangladesh's regulatory framework (Money Laundering Prevention Act 2012, ATA 2009, related BFIU circulars) with BFIU-specific rules and workflows baked in. What goAML exposes as 20+ configuration surfaces, Kestrel delivers as code-level correctness plus the focused admin surfaces listed above (Reference Tables, Match Definitions, Scheduled Processes, User / Role management).

## Capabilities unique to Kestrel (not in goAML)

1. **AI-powered entity extraction** from STR narratives — automatic subject resolution on submit.
2. **AI-drafted STR narratives** — analysts describe facts, Kestrel drafts the narrative; "Draft STR from alert" action on every alert.
3. **AI alert explanations** — every alert opens with an AI-generated "why this fired" panel; no click required.
4. **Automatic cross-bank entity resolution** — `pg_trgm` fuzzy matching + `same_owner` graph edges emitted on every STR submit and scan run; shared entity pool with regulator-wide visibility.
5. **Network graphs on every entity** — automatic React Flow canvas, risk-weighted edges, suspicious-path detection.
6. **8 pre-built detection rules** with continuous scoring — rapid cashout, fan-in / fan-out burst, dormant spike, layering, proximity to flagged, structuring, first-time high value.
7. **Compliance scorecard** — ranks banks against each other on submission timeliness, alert conversion, and peer coverage.
8. **Modern web interface** — accessible from any browser, no desktop install, no VPN-only access.
9. **Production observability** — structured JSON logs, per-request tracing via `X-Request-ID`, standardised error envelopes, incident runbook at `docs/RUNBOOK.md`, readiness probe at `GET /ready` covering auth + database + Redis + storage + Celery worker + AI providers.
10. **BDT-native, Bangla-ready** — built for Bangladesh specifically; reference tables seeded with scheduled banks, MFS providers, recipient agencies, and BFIU-relevant country / currency subsets.
11. **Goodbye Windows-only desktop client** — Kestrel is a web application on Vercel + Render + Supabase. Any authorised analyst reaches it from a browser, including from mobile when incident response requires it.
12. **goAML round-trip** — the XML import + export pair means banks can keep their existing pipelines, and BFIU can hand off to peer FIUs or legacy systems without rewriting anything.

## Appendix — endpoint coverage

Every external surface BFIU or a bank operator interacts with:

| Surface | Path | Purpose |
|---|---|---|
| Readiness probe | `GET /ready` | Covers auth + DB + Redis + storage + Celery + AI providers. |
| STR / SAR / CTR / IER / TBML / complaint / internal / adverse_media_* / escalated / additional_info | `/str-reports` (list, create, update, submit, review, enrich, supplements) | All 11 report variants share one endpoint family. |
| goAML XML import | `POST /str-reports/import-xml` | Multipart upload. |
| goAML XML export | `GET /str-reports/{id}/export.xml` | |
| Excel export | `GET /{domain}/export.xlsx` (str-reports / alerts / disseminations / intelligence/entities) | |
| IER workflow | `/iers` (outbound, inbound, respond, close) | |
| Alerts | `/alerts` (list, detail, actions, AI explanation, create-case from alert) | |
| Cases | `/cases` (list, detail, actions, PDF export, propose, decide, RFI) | |
| Disseminations | `/disseminations` (list, detail, create) | "Disseminate" action on 4 detail surfaces. |
| Intelligence | `/intelligence/entities` (search + new subject), `/intelligence/matches`, `/intelligence/typologies` | |
| Saved queries | `/saved-queries` | |
| Diagrams | `/diagrams` | |
| Match definitions | `/match-definitions` (list, detail, execute) | |
| Reference tables | `/reference-tables` (any read, regulator write) | |
| Admin | `/admin/summary`, `/admin/settings`, `/admin/team`, `/admin/rules`, `/admin/api-keys`, `/admin/statistics`, `/admin/schedules`, `/admin/synthetic-backfill`, `/admin/maintenance/rules-policy-fix` | |
| AI | `/ai/entity-extraction`, `/ai/str-narrative`, `/ai/typology-suggestion`, `/ai/executive-briefing`, `/ai/alerts/{id}/explanation`, `/ai/cases/{id}/summary` | |

OpenAPI spec at `/docs` is the authoritative list — this appendix is an operator-level summary.
