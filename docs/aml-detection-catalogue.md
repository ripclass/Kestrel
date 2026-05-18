# Kestrel AML Detection Catalogue

**Version**: 2026-05-18 · **Status**: production reference · **Audience**: bank CAMLCO + Internal Audit + Bangladesh Bank inspection teams + BFIU procurement review.

This document is the canonical list of AML detection patterns Kestrel implements. It exists because every reporting bank's AML programme is audited against (a) the pattern coverage Bangladesh Bank expects under MLPR 2019 + BFIU Circular 26 and (b) the international AML standards Bangladesh has committed to via FATF mutual evaluation. This catalogue maps Kestrel's detection rules to both reference frameworks.

## Methodology

Kestrel's detection rule catalogue is derived from the publicly available AML regulatory framework Bangladesh's banking sector operates under:

- **FATF Recommendations 10–22** — the international AML/CFT standard. Recommendations 10 (CDD), 11 (record-keeping), 20 (STR), 13 (correspondent banking), 16 (wire transfers), and 22 (DNFBPs) are particularly relevant.
- **The Wolfsberg Group Statements** — global private-banking AML principles. The Wolfsberg AML Principles + the Wolfsberg Statement on Monitoring Screening and Searching define the canonical AML monitoring patterns adopted by every Tier-1 bank.
- **Egmont Group Typology Reports** — public typology guidance issued by the Egmont Group (which BFIU belongs to). The Operational Typology Reports cover real-world ML/TF patterns.
- **BFIU Circular 26 (Scheduled Banks AML/CFT Master Instructions, June 2020)** — Bangladesh's master compliance circular. § 4 covers transaction monitoring; § 5 covers KYC; § 6 covers STR/CTR filing.
- **BFIU Circular 22 (2019)** — inter-bank information exchange.
- **BFIU TBML Guidelines (December 2019)** — Bangladesh's trade-based money laundering authority document. The 29 BD-specific TBML avenues (§ 2.4.1 + § 2.4.2 + § 2.5) drive Kestrel's TBML rule set.
- **MLPA 2012 § 2(cc)** — the 28 predicate offences against which every STR is classified.
- **ATA 2009 § 15** — parallel terrorist-financing authority.

Each rule below cites the regulatory basis in its description. Rules are organised by category, then by implementation status (Active = live today; Pilot-track = Day 1 of pilot; Roadmap = next phase).

---

## Category 1 · Cash structuring and threshold avoidance

| ID | Rule | Pattern | Regulatory basis | Status |
|---|---|---|---|---|
| `structuring` | **Sub-threshold cash structuring** | Cash deposits or withdrawals in the BDT 9.0–9.99 lakh band repeating ≥ 3 times per account per month. Designed to stay just below the BDT 10 lakh CTR mandatory reporting threshold. | BFIU Circular 26 § 4.2 (CTR threshold); FATF R.10 + R.20; Wolfsberg AML Principles § 4.3 | **Active** (tune-for-bank) |
| `smurfing_multi_branch` | **Cross-branch fragmented deposits** | Fragmented deposits each above BDT 1 lakh from multiple branches (5+ different branches, online deposits) within a single calendar day into the same account or related accounts. Designed to avoid single-branch detection. | BFIU Circular 26 § 4.4 (smurfing); Egmont Typology Report — "Smurfs and shells" | **Pilot-track** (multi-branch attribution needs the branch dimension to be tracked on each transaction) |
| `multi_account_aggregation` | **Same-owner multi-account accumulation** | Same person or entity holding ≥ 3 accounts within the bank, with combined cash deposits above BDT 10 lakh on the same day across those accounts. Intent: spread across own-name accounts to dilute single-account threshold checks. | BFIU Circular 26 § 4.4; FATF R.10 (CDD); Wolfsberg § 5.2 | **Pilot-track** |
| `round_amount_repetition` | **Round-amount transaction repetition** | Repeated transactions at round BDT thresholds (5L / 10L / 25L / 50L exactly) on the same account within a 30-day window. Classic indicator of pre-calculated structuring. | FATF R.20 implementation guidance; Wolfsberg § 5.4 | **Roadmap** |

## Category 2 · Rapid disposal and layering

| ID | Rule | Pattern | Regulatory basis | Status |
|---|---|---|---|---|
| `rapid_cashout` | **Rapid withdrawal after deposit** | Funds credited then withdrawn or transferred out within the same business day, repeating ≥ 5 times in a 7-day window. Alternative trigger: ≥ 90% of any single credited amount withdrawn the next day, repeating 5 times in 10 days. | BFIU Circular 26 § 4.5; FATF Recommendation 20 implementation; Wolfsberg AML Statement § 5.5 | **Active** (tune-for-bank) |
| `fan_out_burst` | **Fan-out distribution burst** | Single account dispatches funds to ≥ 10 distinct beneficiaries in a 24-hour window. Classic layering indicator for funds moving through an intermediary account. | Egmont Operational Typology Reports; FATF R.20 | **Active** |
| `fan_in_burst` | **Fan-in concentration burst** | Single account receives funds from ≥ 10 distinct payers in a 24-hour window. Mule-account indicator. | Egmont OTRs; FATF R.20 | **Active** |
| `layering` | **Cross-bank multi-hop layering** | Funds move across 3+ bank hops within a 72-hour window for the same identifier chain. Detected against the shared cross-bank entity graph. | FATF R.20; Wolfsberg § 5.5; Egmont — "Mules and chains" | **Active** |
| `wire_to_new_beneficiary` | **First-time wire to new beneficiary** | First outbound wire transfer (RTGS / SWIFT / cross-border) from an account to a beneficiary it has not transacted with before, where the wire amount exceeds BDT 5 lakh. | FATF R.16 (wire transfers); Wolfsberg AML Principles § 5.5 | **Pilot-track** |

## Category 3 · Account age and dormancy

| ID | Rule | Pattern | Regulatory basis | Status |
|---|---|---|---|---|
| `first_time_high_value` | **High-value transaction in new account** | Account < 30 days old, with either a single transaction > BDT 10 lakh or ≥ 10 transactions cumulatively totalling > BDT 20 lakh. Applies to individual and proprietorship accounts. | BFIU Circular 26 § 4.3; FATF R.10 (CDD); Wolfsberg § 5.4 | **Active** (tune-for-bank) |
| `dormant_spike` | **Dormant account reactivation spike** | Account inactive for ≥ 6 months reactivated and transacting ≥ BDT 5 lakh (individual) or ≥ BDT 10 lakh (proprietorship / corporate) within 30 days of reactivation. | BFIU Circular 26 § 4.6; FATF R.10 implementation; Wolfsberg § 5.5 | **Active** (tune-for-bank) |
| `account_age_velocity_mismatch` | **Activity-age velocity mismatch** | Daily transaction count or volume exceeds the average for accounts of similar age + customer-type by ≥ 3 standard deviations. | FATF R.20; Wolfsberg AML Statement § 5.3 (behavioural baselining) | **Roadmap** |

## Category 4 · Time and velocity

| ID | Rule | Pattern | Regulatory basis | Status |
|---|---|---|---|---|
| `off_hours_burst` | **Off-hours transaction burst** | ≥ 5 transactions from the same account between 10 PM and 6 AM in a single calendar day (online / ATM / card / interbank). Indicates either automation, mule operation, or attempt to avoid daytime review. | BFIU Circular 26 § 4.7 (timing indicators); Wolfsberg § 5.5 | **Pilot-track** |
| `velocity_anomaly` | **Velocity baseline anomaly** | Daily transaction count for the account exceeds its rolling 30-day median by ≥ 5x. | FATF R.20 implementation; Wolfsberg behavioural-baselining principles | **Roadmap** |

## Category 5 · Geographic risk

| ID | Rule | Pattern | Regulatory basis | Status |
|---|---|---|---|---|
| `country_pair_high_risk` | **High-risk jurisdiction exposure** | Inbound or outbound transaction to/from a high-risk country exceeding BDT 5 lakh (individuals) or BDT 10 lakh (non-individuals). High-risk jurisdictions defined by FATF grey/blacklist + OFAC comprehensive sanctions + UN sanctions + UK OFSI. | FATF R.19 (high-risk countries); BFIU Circular 24; OFAC SDN; UN Consolidated; Wolfsberg § 4.5 | **Active** (realtime modifier; tune-for-bank list) |
| `geographic_dispersion` | **Same-NID multi-district activity** | Same NID withdrawing or transacting across ≥ 5 different districts of Bangladesh within a 7-day window. Indicates either money-mule operation or identity reuse. | FATF R.20 implementation; Wolfsberg AML Statement § 5.5 | **Pilot-track** |
| `border_corridor_exposure` | **Border-corridor remittance pattern** | Cross-border MFS or wire transfers concentrated through the Sylhet / Cox's Bazar / Banglabandha corridors (recognised hundi routes) exceeding BDT 2 lakh per transaction. | BFIU Circular 26 § 4.5; Egmont Hundi typology report; Wolfsberg § 5.5 | **Roadmap** |

## Category 6 · Customer-profile and KYC mismatch

| ID | Rule | Pattern | Regulatory basis | Status |
|---|---|---|---|---|
| `proximity_to_bad` | **Two-hop proximity to flagged entity** | The transaction's source or destination is within 2 hops in the shared entity graph of a previously-flagged subject (cross-bank). | FATF R.18 (cross-border information sharing); Egmont graph-analytics OTR; BFIU Circular 22 | **Active** |
| `customer_profile_mismatch` | **Activity vs. declared profile mismatch** | Transaction volume or counterparty mix significantly diverges from the customer's declared occupation, business type, or expected activity profile at KYC. | FATF R.10 (CDD risk-based approach); BFIU Circular 26 § 5.3 (ongoing monitoring); Wolfsberg § 5.4 | **Pilot-track** |
| `dealer_cash_high_value` | **Cash transaction by precious-metal / gemstone dealer** | Cash transactions above BDT 20 lakh by customers whose KYC indicates dealer-in-precious-metals, gemstones, or high-value-goods business type. | FATF R.22 (DNFBPs); BFIU Circular 20 (DNFBPs); Wolfsberg § 4.4 | **Pilot-track** |
| `pep_exposure_spike` | **PEP-linked account activity spike** | Account linked to a Politically Exposed Person (per the PEP watchlist) shows transaction volume or counterparty count ≥ 3x its rolling baseline. | FATF R.12 (PEPs); BFIU Circular 26 § 5.5; Wolfsberg PEP Principles | **Roadmap** |
| `ubo_pattern_inference` | **Beneficial-owner pattern inference** | Account's transaction pattern (counterparty graph + amount distribution) is statistically consistent with a different UBO than the declared one. | FATF R.24 + R.25 (beneficial ownership); BFIU Circular 26 § 5.4 | **Roadmap** |

## Category 7 · Charity and NGO

| ID | Rule | Pattern | Regulatory basis | Status |
|---|---|---|---|---|
| `charity_donation_anomaly` | **Unusual charity / NGO donation pattern** | Donations to registered charitable organisations exceeding BDT 20 lakh in a calendar month OR donation frequency > 5 events/month from the same account. | FATF R.8 (NPO sector); BFIU Circular 26 § 4.9; ATA 2009 (TF concerns on NPOs) | **Pilot-track** |

## Category 8 · Virtual assets and digital channels

| ID | Rule | Pattern | Regulatory basis | Status |
|---|---|---|---|---|
| `crypto_keyword_indicator` | **Crypto / virtual-asset description match** | Transaction description, narrative, or memo field contains keywords associated with crypto / virtual-asset transactions (e.g. "BTC", "ETH", "USDT", "binance", "exchange wallet"). Bangladesh Bank prohibits cryptocurrency dealings; any reference is suspicious. | Bangladesh Bank FE Circular 18/2017 (crypto prohibition); FATF R.15 (virtual assets) | **Pilot-track** (transaction-text scanning rule; low engineering effort) |
| `vasp_counterparty` | **Virtual-asset service provider counterparty** | Inbound or outbound transfer where the counterparty institution is a known VASP (virtual asset service provider) — Binance, Coinbase, etc. | FATF R.15; FATF Updated Guidance on Virtual Assets (June 2023); BFIU forthcoming VASP guidance | **Roadmap** |

## Category 9 · Cards

| ID | Rule | Pattern | Regulatory basis | Status |
|---|---|---|---|---|
| `credit_card_third_party_payment` | **Third-party credit card bill payment pattern** | Credit card bill paid by parties other than the cardholder ≥ X times within a calendar month, OR aggregate third-party bill payments exceed Y% of total bill settlement. Default thresholds: X=3, Y=50%. | FATF R.20; Wolfsberg Statement on Monitoring § 4.3; BFIU Circular 26 § 4.8 | **Pilot-track** |
| `credit_card_fund_transfer_dispersion` | **Credit-card fund transfer to many unrelated parties** | Fund transfers from credit card account to ≥ 10 different beneficiary accounts (individuals) or ≥ 20 (proprietorship / corporate) within a calendar month. | Wolfsberg Card AML Principles; FATF R.16 | **Pilot-track** |
| `credit_card_limit_utilisation_pattern` | **Repeated full-limit utilisation with rapid repayment** | Credit card usage ≥ 80% of approved limit occurring ≥ 4 times in a calendar month, with repayments by self or third party. Indicates either layering through the card line or hidden-source repayment activity. | Wolfsberg Card AML Principles; BFIU Circular 26 § 4.8 | **Pilot-track** |
| `card_off_hours_pos` | **Off-hours POS / ATM activity** | POS or ATM transactions ≥ 5 in a single day between 11 PM and 5 AM. | BFIU Circular 26 § 4.7 (timing indicators); Wolfsberg § 5.5 | **Roadmap** |

## Category 10 · Pay orders, cheques, and instruments

| ID | Rule | Pattern | Regulatory basis | Status |
|---|---|---|---|---|
| `pay_order_unclaimed_aged` | **Aged unclaimed pay order** | Pay order remains unclaimed (not encashed by the payee) for ≥ 6 months after issuance. Indicates either parking of funds, broken transaction chain, or instrument issued without clear underlying purpose. | BFIU Circular 26 § 4.11 (instruments); Bangladesh Bank Negotiable Instruments Act guidance | **Pilot-track** |
| `cheque_serial_pattern` | **Repetitive cheque payments to same payee** | Series of consecutive-numbered cheques (≥ 5) from the same account paid to the same payee within 30 days. Indicates structured payment with intent to obscure single-transaction visibility. | BFIU Circular 26 § 4.11; FATF R.20 | **Roadmap** |

## Category 11 · Trade-based money laundering (BFIU TBML Guidelines 2019)

These 6 rules implement the operational detection layer for Bangladesh's TBML Guidelines (Dec 2019), § 2.4.1 import avenues + § 2.4.2 export avenues + § 2.5 royalty/technical fee + Appendix B operational alerts. The 29-avenue regulatory taxonomy is encoded in the Kestrel typology library (`/intelligence/typologies`).

| ID | Rule | Pattern | Regulatory basis | Status |
|---|---|---|---|---|
| `over_invoicing` | **Import / export over-invoicing** | Declared transaction value exceeds market reference price by ≥ 2x for the same HS code and origin-destination corridor. | BFIU TBML Guidelines § 2.4.1.3 + § 2.4.2.3; FATF TBML Typology Report (2006) | **Active** |
| `under_invoicing` | **Import / export under-invoicing** | Declared transaction value is below market reference by ≥ 50% for the same HS code and corridor. | BFIU TBML Guidelines § 2.4.1.4 + § 2.4.2.4; FATF TBML Typology (2006) | **Active** |
| `multiple_invoicing` | **Multi-bank invoice presentation** | Same Bill of Lading or LC reference presented at ≥ 2 banks. Cross-bank detection. | BFIU TBML Guidelines § 2.4.1.5; FATF TBML Typology (2006) — multi-invoicing | **Active** |
| `phantom_shipment` | **LC settlement without shipment evidence** | LC settled but no Bill of Lading / port-of-loading / vessel record / customs Bill of Entry traceable. | BFIU TBML Guidelines § 2.4.1.7 + § 2.4.1.8 | **Active** |
| `declaration_value_mismatch` | **Customs declaration value mismatch** | Customs Bill of Entry declared value differs from LC settlement value by ≥ 30%. | BFIU TBML Guidelines § 2.4.1.6; FATF TBML Typology (2006) — declaration mismatch | **Active** |
| `transshipment_routing` | **High-risk transshipment routing** | Goods routed through high-risk transshipment jurisdiction (HK / SG / AE / IR-adjacent corridors) inconsistent with stated trade economics. | BFIU TBML Guidelines § 2.4.1.13; BFIU Circular 24; FATF R.19 | **Active** |

## Category 12 · Realtime transaction-scoring modifiers

These three modifiers are applied per-call to `POST /transactions/score` (the per-transaction decisioning API). They adjust the realtime score without being primary rules.

| ID | Rule | Pattern | Regulatory basis | Status |
|---|---|---|---|---|
| `payment_mode_high_risk` | **High-risk payment mode** | High-risk channels (CASH, WIRE, certain MFS patterns) adjust the realtime score upward at decisioning time. | Wolfsberg AML Principles § 5.3 (channel risk); BFIU Circular 26 § 4.7 | **Active** |
| `hs_code_anomaly` | **HS-code activity inconsistency** | The declared HS code on a trade transaction is inconsistent with the shipper's declared business sector or historical activity. | BFIU TBML Guidelines § 2.4.1.7; FATF TBML Typology (2006) | **Active** |
| `country_pair_high_risk_modifier` | **High-risk corridor pair** | The (from-country, to-country) pair for this transaction is in the high-risk corridor list (e.g. BD ↔ AE ↔ HK ↔ shell-incorporated). | FATF R.19; BFIU Circular 24 | **Active** |

## Category 13 · Sanctions / PEP / adverse-media screening (inline)

These rules fire inline during realtime scoring + KYC onboarding + daily Beat re-screening. Not numbered as separate rules because they're part of the screening service, but listed for completeness.

| ID | Rule | Pattern | Regulatory basis | Status |
|---|---|---|---|---|
| `sanctions_party_hit` | **OFAC / UN / UK / EU / BB Domestic sanctions hit on transaction party** | The from-party or to-party of a transaction matches an entry on OFAC SDN, UN consolidated, UK OFSI, EU FSF, or Bangladesh Bank's domestic sanctions list at score ≥ 0.7 (4-dimension composite: name + DOB + nationality + identifier). | FATF R.6 (targeted financial sanctions); BFIU Circular 19; UN Security Council Resolutions 1267/1373/1989 | **Active** (5 sources live in screening service) |
| `pep_hit` | **Politically Exposed Person watchlist match** | Customer or counterparty matches a domestic or foreign PEP list. | FATF R.12 (PEPs); BFIU Circular 26 § 5.5; Wolfsberg PEP Principles | **Active** |
| `adverse_media_finding` | **Adverse media on customer or counterparty** | News + media database search returns adverse content (fraud / corruption / sanctioned activity) about the customer or counterparty. | FATF R.10 (CDD); Wolfsberg Statement on Adverse Media (2018) | **Roadmap** (adapter is wired to ComplyAdvantage; requires customer credential to activate) |

---

## Summary — coverage status

| Status | Count | What it means |
|---|---|---|
| **Active** | 17 rules | Live in production today. Banks see alerts from these rules now. |
| **Pilot-track** | 11 rules | Engineering-complete or low-effort additions. Shipped as part of any commercial pilot's Day 0–Day 30 ramp. |
| **Roadmap** | 8 rules | Further-out work. Either requires new data ingestion (credit card, branch attribution, etc.), new dependencies (adverse-media API), or customer-driven prioritisation. |
| **Total catalogue** | **36 rules** | Covers every category in the canonical AML monitoring framework. |

### Active rule list (17 in production today)

`structuring` · `rapid_cashout` · `fan_in_burst` · `fan_out_burst` · `layering` · `first_time_high_value` · `dormant_spike` · `proximity_to_bad` · `country_pair_high_risk` · `over_invoicing` · `under_invoicing` · `multiple_invoicing` · `phantom_shipment` · `declaration_value_mismatch` · `transshipment_routing` · `sanctions_party_hit` · `pep_hit` + realtime modifiers `payment_mode_high_risk` / `hs_code_anomaly` / `country_pair_high_risk_modifier`.

### Pilot-track (11 — committed Day 0–30 of any pilot)

`smurfing_multi_branch` · `multi_account_aggregation` · `wire_to_new_beneficiary` · `off_hours_burst` · `geographic_dispersion` · `customer_profile_mismatch` · `dealer_cash_high_value` · `charity_donation_anomaly` · `crypto_keyword_indicator` · `credit_card_third_party_payment` · `credit_card_fund_transfer_dispersion` · `credit_card_limit_utilisation_pattern` · `pay_order_unclaimed_aged`.

### Roadmap (8 — phased delivery beyond pilot baseline)

`round_amount_repetition` · `account_age_velocity_mismatch` · `velocity_anomaly` · `border_corridor_exposure` · `pep_exposure_spike` · `ubo_pattern_inference` · `vasp_counterparty` · `card_off_hours_pos` · `cheque_serial_pattern` · `adverse_media_finding`.

---

## How rules are tuned per bank

Each rule in the Active list is **a YAML file under `engine/app/core/detection/rules/` or `engine/app/core/detection/trade_rules/`** with default thresholds. Per-bank overrides live in the `rules` Postgres table. A bank admin tunes rules via the **Admin → Rules** surface (see Tutorial 24 of the platform walk).

Tuning examples typical for a Tier-1 commercial bank in Bangladesh:

- `structuring`: threshold band → 9.0–9.99 lakh (default 9.0–9.99 lakh — matches BFIU Circular 26 § 4.2 implicitly).
- `rapid_cashout`: 5-times-per-week + 90%-next-day branches both active.
- `first_time_high_value`: thresholds → single tx > BDT 10 lakh OR ≥ 10 txns totalling > BDT 20 lakh.
- `dormant_spike`: thresholds → BDT 5 lakh (individual) / BDT 10 lakh (proprietorship) within 30 days of reactivation.
- `country_pair_high_risk`: thresholds → BDT 5 lakh (individuals) / BDT 10 lakh (non-individuals).

These specific numerical tunings are documented per-bank in the pilot onboarding plan; the system rule's defaults are deliberately set close to BFIU's expected baseline so onboarding tuning is light.

---

## Map to MLPA § 2(cc) predicate offences

Every alert produced by these rules can be tagged with one or more MLPA 2012 § 2(cc) predicate offences when the analyst drafts the resulting STR. The 28 predicate offences are enumerated on `/admin/reference-tables → Agencies` and selectable on every dissemination form. Typical mappings:

- Cash structuring rules → `(5) Fraud` + `(21) Concealment/disguise of criminal proceeds`.
- Trade-based rules → `(18) Smuggling/customs offences (TBML)` + often `(5) Fraud` + `(6) Forgery`.
- High-risk country / sanctions hit → `(17) Terrorist financing` (when ATA § 15 invoked) or sector-specific predicate.
- Charity / NPO rule → `(17) Terrorist financing` (ATA 2009 + FATF R.8).
- Credit card rules → `(5) Fraud` + `(20) Insider trading + market manipulation` depending on counterparty.

---

## How this catalogue evolves

New rules enter Kestrel through three channels:

1. **Public regulatory updates** — when BFIU issues a new circular, FATF updates its Recommendations, or Bangladesh Bank publishes new guidance, the Kestrel team adds rules in the next release.
2. **Bank-specific risk patterns** — banks can author bespoke detection patterns via the **Match Definitions** surface (`/admin/match-definitions` — see Tutorial 25). These run alongside the system rules.
3. **Cross-bank intelligence** — patterns surfaced by the cross-bank match aggregation that no single bank could detect alone, codified back into the catalogue.

The Active + Pilot-track sets above represent Kestrel's 2026-Q2 production baseline. The Roadmap items are sequenced for delivery through 2026-Q3 and 2026-Q4 based on customer prioritisation.

---

## References

1. FATF. *International Standards on Combating Money Laundering and the Financing of Terrorism & Proliferation — The FATF Recommendations.* Updated edition.
2. The Wolfsberg Group. *Wolfsberg Anti-Money Laundering Principles for Private Banking.* Most recent revision.
3. The Wolfsberg Group. *Wolfsberg Statement on Monitoring Screening and Searching.*
4. Egmont Group. *Operational Typology Reports (public summaries).*
5. Bangladesh Bank Financial Intelligence Unit. *BFIU Circular 26 — Anti Money Laundering and Combating Financing of Terrorism Instructions for Scheduled Banks.* 16 June 2020.
6. Bangladesh Bank Financial Intelligence Unit. *BFIU Circular 22 — Inter-Bank Information Exchange.* 31 January 2019.
7. Bangladesh Bank Financial Intelligence Unit. *BFIU Guidelines for Prevention of Trade-Based Money Laundering.* December 2019.
8. Bangladesh Parliament. *The Money Laundering Prevention Act, 2012* (as amended).
9. Bangladesh Parliament. *The Anti-Terrorism Act, 2009* (as amended 2013).
10. FATF. *Trade-Based Money Laundering — Typology Report.* 2006 + 2020 supplements.

---

*This catalogue is the canonical reference for Kestrel's AML detection coverage and is updated on each platform release. For per-rule implementation detail, refer to the YAML rule definitions in `engine/app/core/detection/` in the Kestrel codebase. For tuning surface walkthrough, see Tutorial 24 — Admin · Rules.*
