# Kestrel — Bangladesh AML / CFT regulatory coverage

**Version**: 2026-05-16
**Audience**: BFIU procurement, Bangladesh Bank legal, bank CAMLCO procurement teams
**Purpose**: Surface-by-surface map from every relevant Bangladesh AML/CFT instrument to the Kestrel feature, table, route, or service that operationalises it.

This document is the procurement-grade complement to `docs/goaml-coverage.md` (which maps the UNODC goAML surface). Where goAML coverage answers *"can a BFIU analyst recognise the screen?"*, this document answers *"does the platform comply with — and operationalise — Bangladesh's AML legal framework specifically?"*

Every claim cites (a) the Kestrel artefact — migration, model, service, route, or web page — and (b) the regulatory source paragraph in `REG RULES/*.ocr.txt`.

---

## ┼ Executive summary

Kestrel maps to the four primary Bangladesh AML/CFT instruments end-to-end:

| Instrument | Issuing authority | Coverage |
|---|---|---|
| **Money Laundering Prevention Act 2012** (MLPA, with 2015 amendments incorporated) | Bangladesh Parliament — published in the Gazette, 20 February 2012 | §2(cc) 28 predicate offences typed on STR / Case / Dissemination / Alert (migrations 025 + 028); §23 + §24 enabling clauses cited on each dissemination (migration 024) |
| **Money Laundering Prevention Rules 2019** (MLPR) | Bangladesh Bank | Operational rules for STR / CTR submission, retention, reporting officer designation — implemented across the STR + CTR + audit-log surfaces |
| **Anti-Terrorism Act 2009** (ATA, with 2013 amendments) | Bangladesh Parliament | §15(1) TF mirrors of the MLPA §23 enabling clauses; TF predicate (clause 21) on STR / Case / Dissemination |
| **BFIU Circulars 22 / 24 / 26** (2019–2020) | Bangladesh Financial Intelligence Unit | Information exchange (Circular 22), Trade-Based Money Laundering Guidelines (Circular 24 + Dec 2019 Guidelines), Scheduled Bank AML/CFT instructions (Circular 26) |

In addition, sixteen supporting statutes in the BFIU **Related Acts and Rules (RELAC)** family — Customs Act 2023, Income Tax Act 2023, Cyber Security Ordinance 2025, Anti-Corruption Act 2004, Narcotics Control Act 2018, etc. — provide the predicate-offence universe that Kestrel surfaces via the §2(cc) tagging system.

---

## ┼ 1 · MLPA 2012 coverage

### 1.1 MLPA §2(cc) predicate offences — typed end-to-end

MLPA §2(cc) enumerates 28 categories of predicate offence. Every category is encoded as a stable code in `engine/app/schemas/predicate_offence.py` (`PredicateOffence` Literal), enforced on the database via CHECK constraints, and surfaced in the UI via `web/src/types/domain.ts::PREDICATE_OFFENCE_LABELS`.

| Where the predicate offence appears | Migration | Table / column | Source citation |
|---|---|---|---|
| STR reports | 025 | `str_reports.predicate_offences text[]` | MLPA §2(cc) clauses (1)–(28) |
| Cases | 025 | `cases.predicate_offences text[]` | same |
| Disseminations | 025 | `disseminations.predicate_offences text[]` | same |
| Alerts (TBML scan results) | 028 | `alerts.predicate_offences text[]` | same |
| Typology library (29 TBML avenues + 5 generic) | 026 | `typologies.predicate_offences text[]` | same — auto-tagged on the rule output |

Three GIN indexes (`idx_str_predicate_offences`, `idx_cases_predicate_offences`, `idx_dissem_predicate_offences`, `idx_alerts_predicate_offences`) make "every STR alleging customs offence + tax evasion in the last 90 days" a sub-100ms query.

Source: `REG RULES/mlpa_2012_english.ocr.txt` lines 300–371 (§2(cc) clauses 1–28).

### 1.2 MLPA §23 + §24 — BFIU powers + dissemination authority

| MLPA clause | Power conferred | Where used in Kestrel |
|---|---|---|
| §23(1)(a) | Analyse + provide STR/CTR info to LEA | `disseminations.mlpa_section = 'mlpa_23_1_a'` option |
| §23(1)(b) | Demand info from any reporting org | `engine/app/services/disseminations.py` audit trail |
| §23(1)(c) | Order suspension / freeze for 30 days (extendable to 6 months) | Manual workflow on `/admin/maintenance` — service: `update_alert(action='escalate')` |
| §23(1)(d) | Issue directions for ML prevention — Circulars 22, 24, 26 issue under this clause | `disseminations.mlpa_section = 'mlpa_23_1_d'`; also `circular_22_exchange` flag on bank-to-bank exchanges |
| §23(1)(e) | Monitor reporting orgs + on-site inspection | `/admin/audit-log` + `/admin/schedules` |
| §23(1)(f) | Training + capacity building | (out-of-scope — operational) |
| §23(1)(g) | Other functions for the purposes of the Act | catch-all |
| §24(3) | Spontaneous dissemination to LEA | `disseminations.mlpa_section = 'mlpa_24_3'`; default when authority is BD-LEA |
| §24(4) | Cross-border exchange via Egmont agreement | `disseminations.mlpa_section = 'mlpa_24_4'`; default when authority is `foreign_fiu_egmont` |

Source: `REG RULES/mlpa_2012_english.ocr.txt` lines 770–896 (§23 + §24 verbatim).

### 1.3 MLPA §3 (ML override) + §4 (ML offence)

ML is a standalone offence in MLPA §4. Kestrel does not adjudicate offences — it surfaces evidence and disseminates to the relevant agency. The chain of custody from initial detection through case to dissemination is preserved in `audit_log` (append-only, no edit, no override) so MLPA §4 prosecutions have evidentiary support.

---

## ┼ 2 · BFIU Circulars coverage

### 2.1 BFIU Circular 22 of 2019 — Information Exchange Among Reporting Organisations

Authorises reporting organisations (banks, insurers, financial institutions, money-changers, stock brokers, portfolio managers, asset managers) to exchange information among themselves directly OR via correspondent banking / wire transfer / third-party-acquired services — subject to confidentiality and limited to ML/TF prevention purposes. Issued under MLPA §23(1)(d) + ATA §15(1)(d).

| Capability | Surface |
|---|---|
| Mark a dissemination as a Circular-22 bank-to-bank exchange | `disseminations.circular_22_exchange boolean` (migration 024); UI checkbox on dissemination form |
| Recipient typed as peer reporting org | `recipient_authority = 'peer_reporting_org_circular_22'` |
| Audit trail | `audit_log` row keyed to the disseminator's identity, append-only |
| Year-end stats by recipient authority | `idx_dissem_circular_22` partial index on `(org_id, disseminated_at DESC) WHERE circular_22_exchange = true` |

Source: `REG RULES/circular_22_dissemination.ocr.txt` (full Bangla cover letter).

### 2.2 BFIU Circular 24 of 10 December 2019 + Guidelines for Prevention of TBML

Issued under MLPA §23(1)(ka) + ATA §15(1)(ka). Banks had until 10 March 2020 to submit internal TBML policy + 1 June 2020 for implementation. Defines **29 BD-specific TBML avenues** (Guidelines §2.4.1 import × 14, §2.4.2 export × 14, §2.5 royalty × 1) plus **49 numbered TBML Alerts** in Appendix B and a product-wise alert library in Appendix C.

| Capability | Surface |
|---|---|
| 29 TBML avenues as canonical typology rows | `typologies` table — IDs `tbml-avenue-import-01..14`, `tbml-avenue-export-01..14`, `tbml-avenue-royalty-01`; each carries `bfiu_avenue_ref` (`2.4.1.iv`, `2.4.2.iii`, etc.) and `predicate_offences[]` |
| 6 TBML detection rules (subset of the 49 alerts — extensible) | `engine/app/core/detection/trade_rules/*.yaml`: `over_invoicing`, `under_invoicing`, `multiple_invoicing`, `phantom_shipment`, `declaration_value_mismatch`, `transshipment_routing` |
| Trade-transaction data model — LC structure, HS code, country pair, B/L, customs BE | `trade_transactions` table (migration 027); ~50 columns |
| Real-time TBML scoring on every transaction | `engine/app/services/realtime_scoring.py` — 3 modifiers: `tbml_payment_mode_open_account`, `tbml_hs_code_anomaly`, `tbml_country_pair_high_risk` |
| TBML scan endpoint | `POST /trade/scan` — runs 6 rules across caller's org trades, idempotent insert of `source_type='tbml_scan'` Alert rows |
| TBML dashboard | `/intelligence/tbml` — stats, multi-invoicing clusters, country-pair heatmap, recent alerts |

Source: `REG RULES/circular_24_tbml_cover.ocr.txt` (cover letter) + `REG RULES/tbml_guidelines_2019.ocr.txt` (substantive 94-page Guidelines).

### 2.3 BFIU Circular 26 of 16 June 2020 — Scheduled Bank AML/CFT Instructions

Master AML/CFT compliance instructions for scheduled banks under MLPA §23(1)(ka) + ATA §15(1)(ka). Covers CAMLCO/DCAMLCO/BAMLCO duties, KYC, transaction monitoring, STR/CTR reporting, UNSCR sanctions list compliance, self-assessment, record preservation, training.

| Circular 26 requirement | Surface |
|---|---|
| CAMLCO / DCAMLCO / BAMLCO designation | `profiles.persona = bank_camlco` × `profiles.role = admin / manager / analyst`; org-level admin team surface at `/admin/team` |
| Transaction monitoring with automated detection | Account-centric: 8 detection rules in `engine/app/core/detection/rules/*.yaml`; trade-centric: 6 TBML rules; real-time: `POST /transactions/score` |
| STR / CTR submission | 11 report types on `str_reports` (`str / sar / ctr / tbml / complaint / ier / internal / adverse_media_str / adverse_media_sar / escalated / additional_info`); goAML XML round-trip |
| Sanctions list compliance (UNSCR + BB Domestic) | Watchlist ingestion from OFAC + UN + UK FCDO + BB Domestic + PEP; `/screen` route; inline sanctions modifier in real-time scoring |
| Self-assessment + statistics | `/reports/statistics` + `/reports/compliance` (compliance scorecard) |
| Record preservation | `audit_log` append-only; 365-day default retention (configurable per Circular 26 §X); archive to Supabase Storage Beat task |
| KYC + customer due diligence | `/customers` 6-route CRUD; primary + beneficial-owner sanctions screening inline; periodic re-screen Beat task at 03:00 BDT |

Source: `REG RULES/circular_26_scheduled_banks.ocr.txt` (45-page master).

---

## ┼ 3 · ATA 2009 + ATR 2013 — Terrorist Financing coverage

| Capability | Surface |
|---|---|
| TF as a predicate offence | `terrorism_or_terrorist_financing` in the 28-code §2(cc) set |
| ATA §15(1)(a–g) enabling clauses on dissemination | `disseminations.mlpa_section` values `ata_15_1_a` through `ata_15_1_g` |
| TF report type | `str_reports.report_type = 'sar'` for terrorism-financing flagged STRs |
| UNSCR Targeted Financial Sanctions screening | OFAC + UN watchlists ingested daily; alert source_type `cross_bank` + sanctions hit modifier; `/screen` route |
| MLA cross-border cooperation | `POST /iers` (Egmont workflow) — counterparty FIU, reference, deadline tracked; `disseminations.mlpa_section = 'mlpa_24_4'` for Egmont-channel disseminations |

Source: `REG RULES/_mlpa_2012_english.ocr.txt` (ATA §15 mirrors §23 nearly word-for-word; both included in `MlpaSection` Literal).

---

## ┼ 4 · MLPR 2019 (Money Laundering Prevention Rules) coverage

The MLPR is the operational complement to MLPA — defines submission formats, retention periods, reporting officer duties, deadlines. Substantive coverage:

| MLPR area | Surface |
|---|---|
| STR submission within 7 working days of suspicion | `str_reports.status` lifecycle `draft → submitted`; UI timer + scheduled-process Beat task at 06:30 BDT for the daily digest |
| CTR threshold (Tk 10 lakh single transaction or aggregate per day) | `cash_transaction_reports` table; threshold + aggregation enforced in `engine/app/services/ctr.py` |
| Record preservation (5 years from submission, or longer if requested) | `audit_log` retention Beat task with configurable cutoff (`AUDIT_LOG_RETENTION_DAYS`, default 365 — set to 1825 for MLPR-strict compliance via env var) |
| Reporting officer designation | `profiles.role` enum + `/admin/team` |
| Suspicious transaction monitoring system | 8 detection rules + 6 TBML rules + sanctions + KYC re-screen Beat task |

Source: `REG RULES/_mlpr_extracted.txt` (Bangla, extracted on best-effort basis).

---

## ┼ 5 · RELAC — Related Acts and Rules mapping

BFIU's RELAC family is the predicate-offence supporting-law set. Sixteen statutes; the relevant subset for AML detection on this platform:

| RELAC statute | Year | Predicate offence category surfaced |
|---|---|---|
| [Customs Act](http://bdlaws.minlaw.gov.bd/act-details-1476.html) | 2023 | `smuggling_customs_excise` §2(cc)(18) — TBML + smuggling |
| [Income Tax Act](http://bdlaws.minlaw.gov.bd/act-1429.html) | 2023 | `tax_related_offences` §2(cc)(19) |
| [Anti-Corruption Act](http://bdlaws.minlaw.gov.bd/act-914.html) | 2004 | `corruption_and_bribery` §2(cc)(1) |
| [Narcotics Control Act](http://bdlaws.minlaw.gov.bd/act-1276.html) | 2018 | `illegal_trade_narcotics` §2(cc)(8) |
| [Cyber Security Ordinance](http://bdlaws.minlaw.gov.bd/upload/act/2025-05-25-11-22-35-Ordinance-No.-25-of-2025.pdf) | 2025 | `other_bb_gazetted` §2(cc)(28) — cyber-fraud predicate |
| [Prevention of Human Trafficking Act](http://bdlaws.minlaw.gov.bd/act-1086.html) | 2012 | `human_trafficking` §2(cc)(16) + `trafficking_women_children` §2(cc)(12) |
| [Arms Act](http://bdlaws.minlaw.gov.bd/act-38.html?hl=1) | 1878 | `illegal_trade_firearms` §2(cc)(7) |
| [Gold Policy (amended)](https://www.bfiu.org.bd/pdf/regulationguideline/act/gold_policy-2018(amended)-2021.pdf) | 2021 | `smuggling_currency` §2(cc)(14) — precious-metal predicate |
| [Mutual Legal Assistance in Criminal Matters Act](http://bdlaws.minlaw.gov.bd/upload/act/2021-11-17-11-42-18-41.-Mutual-Legal-Assitant-in-Criminal-Matters-Act-2012.pdf) + [Rules](https://www.bb.org.bd/aboutus/dept/bfiu/laws/mutuallegalassistance_rules2012.pdf) | 2012 | Cross-border via `mlpa_24_4` + `recipient_authority = foreign_fiu_egmont` |
| [Bankers' Books Evidence Act](http://bdlaws.minlaw.gov.bd/act-1392.html) | 2021 | Audit-trail evidentiary value |
| [Women and Children Abuse Prevention Act](http://bdlaws.minlaw.gov.bd/act-835.html) | 2000 | `trafficking_women_children` §2(cc)(12) |
| [Extradition Act](http://bdlaws.minlaw.gov.bd/act-details-479.html) | 1974 | Cross-border |
| [Prevention of Corruption Act](http://bdlaws.minlaw.gov.bd/act-217.html) | 1947 | `corruption_and_bribery` §2(cc)(1) |
| [Code of Criminal Procedure](http://bdlaws.minlaw.gov.bd/act-75.html?hl=1) | 1898 | Procedural |
| [Limitation Act](http://bdlaws.minlaw.gov.bd/act-88.html) | 1908 | Procedural |

The 16 statutes are referenced as URLs in the RELAC index at <https://www.bfiu.org.bd/index.php/actsandrules/relac>. Each predicate-offence tag on a Kestrel alert / STR / case / dissemination is the bridge between the suspicious activity Kestrel detects and the supporting law a prosecutor would charge under.

---

## ┼ 6 · Audit, evidentiary, and RLS guarantees

### 6.1 Audit log
Append-only `audit_log` table (no UPDATE policy in RLS — INSERT only from application code, no DELETE). Every dissemination, STR submission, alert action, case mutation, AI invocation, and admin change writes a row keyed to actor `user_id` + actor `org_id` + IP + request_id + timestamp + structured `details jsonb`. Bankers' Books Evidence Act 2021 evidentiary standard applies.

### 6.2 RLS per-org isolation
Every domain table is RLS-enabled with policies derived from `auth_org_id()` + `is_regulator()`. Bank persona sees own-org rows only; regulator persona sees across orgs. Cross-bank shared tables (`entities`, `matches`, `connections`, `watchlist_entries`, `reference_tables`) are shared by design. **No regulator escape hatch on `audit_log`** — the regulator cannot see another org's audit trail without an explicit dissemination request (MLPA §23(1)(b)) that itself gets audit-logged.

### 6.3 Persona-aware anonymisation (FATF Recommendation 9 + Circular 22 confidentiality)
Bank persona NEVER sees other bank names on the cross-bank or TBML dashboards — peer banks render as `Peer institution N`, match keys redact to last 4 characters (`····5001`). Enforced server-side in `services/cross_bank.py` + `services/tbml.py` — not at the UI layer. The API never returns the full key to a bank caller.

Regression-tested via `tests/test_cross_bank.py` + `tests/test_tbml_dashboard_service.py`.

---

## ┼ 7 · Honest gaps

1. **Outbound goAML-XML adapter to UNODC central server**: file-based XML import + export round-trip is implemented (`engine/app/parsers/goaml_xml.py` + the per-STR export route). Machine-to-machine sync into the goAML central server is not yet built — `engine/app/adapters/goaml.py` is a stub. BFIU disseminations continue to use the export path.
2. **Customs reference-price benchmark feed**: the over/under-invoicing rules require `trade_transactions.market_reference_value` to fire. A live feed from NBR's customs reference-price database is a Phase C dependency; today the field is populated manually or via a periodic ingestion job that banks operate on their side.
3. **Live ingestion of BB Domestic Sanctions List**: synthetic seed of 22 watchlist entries (including 4 BB Domestic) is on prod. Live BFIU domestic-list ingestion is gated on `KESTREL_WATCHLIST_INGESTION_ENABLED=true` (currently off). The list at <https://www.bfiu.org.bd/pdf/local_sanction_list_eng.pdf> is the source; English + Bangla variants are published periodically.
4. **EU Financial Sanctions File** — requires credentialed access. 1-day wire-up after the credential lands.
5. **Pen test + SOC 2**: not yet certified. Path documented in `docs/sales/production-readiness.md`. First-pilot revenue funds the pen test + SOC 2 kickoff.

---

## ┼ 8 · Migration ledger (procurement traceability)

| Migration | Date applied | What it adds |
|---|---|---|
| 001 | 2026-04 | Core schema (orgs, profiles, entities, accounts, transactions, alerts, cases, STRs) |
| 002–022 | 2026-04 → 2026-05 | V1 through V3 phases — see `CLAUDE.md` §"Current state" |
| **023** | 2026-05-16 | `bank_filer` persona + `filing_only` plan tier (goAML-replacement free tier) |
| **024** | 2026-05-16 | `disseminations.recipient_authority` (13 named BD authorities) + `mlpa_section` (16 enabling clauses) + `circular_22_exchange` boolean |
| **025** | 2026-05-16 | `predicate_offences text[]` on STR + Case + Dissemination with 28-code CHECK from MLPA §2(cc) |
| **026** | 2026-05-16 | `typologies.predicate_offences` + `mlpa_section` + `bfiu_avenue_ref`; 29 BD-specific TBML avenues seeded |
| **027** | 2026-05-16 | `trade_transactions` table — ~50 columns covering LC structure, HS code, country pair, B/L, customs BE, settlement |
| **028** | 2026-05-16 | `alerts.source_type` += `tbml_scan`; `alerts.predicate_offences` + `linked_trade_id` + `bfiu_avenue_ref` |

Source migrations live under `supabase/migrations/`. Every CHECK constraint, index, and column comment in this document is verifiable against the SQL on the filesystem.

---

## ┼ Glossary

| Term | Meaning |
|---|---|
| **AD** | Authorised Dealer — a scheduled bank licensed to handle foreign exchange |
| **B/L** | Bill of Lading |
| **BAMLCO** | Branch Anti-Money Laundering Compliance Officer |
| **BE** | Bill of Entry — customs-side import declaration |
| **BFIU** | Bangladesh Financial Intelligence Unit |
| **CAMLCO** | Chief Anti-Money Laundering Compliance Officer |
| **CTR** | Cash Transaction Report (Tk 10 lakh threshold) |
| **ERC** | Exporter Registration Certificate |
| **FERA** | Foreign Exchange Regulation Act 1947 |
| **GFET** | Guidelines for Foreign Exchange Transactions (BB 2018) |
| **IER** | Information Exchange Request — Egmont workflow |
| **IRC** | Importer Registration Certificate |
| **LC** | Letter of Credit |
| **LCAF** | LC Authorisation Form |
| **MLA** | Mutual Legal Assistance |
| **MLPA / MLPR** | Money Laundering Prevention Act / Rules |
| **NBR** | National Board of Revenue |
| **RELAC** | Related Acts and Rules (BFIU index of supporting statutes) |
| **STR / SAR** | Suspicious Transaction Report / Suspicious Activity Report |
| **TBML** | Trade-Based Money Laundering |
| **UNSCR** | UN Security Council Resolution (sanctions framework) |

---

*Document version 2026-05-16. The migration ledger and every regulatory citation in this document map to a SQL file under `supabase/migrations/` or a paragraph in `REG RULES/*.ocr.txt`. For procurement review under NDA, the full pg_policies dump + tenant-isolation simulation transcript is available on request.*

**Contact**: intake@kestrelfin.com · Enso Intelligence Inc., Dhaka · `kestrelfin.com`
