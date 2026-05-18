# Sample goAML XML files

Three synthetic goAML report XMLs ready to import via the **STR tab → Import goAML XML** path on `kestrelfin.com/strs`.

All data is synthetic. Reporting org is Sonali Bank PLC (`rentity_id=SBPL`). When imported by a Sonali-tenant CAMLCO they appear as own-bank submissions; when imported by a BFIU Director they appear as Sonali's filings in the national pool.

## Files

| File | Type | Subject | Pattern |
|---|---|---|---|
| **`01-str-rapid-cashout.xml`** | STR | Salim Reza (person + NID + phone) | Rapid cash-out: 2 inbound BEFTN+NPSB credits (BDT 27,50,000 total) followed by 3 cash withdrawals across Motijheel / Gulshan / Dhanmondi / Uttara branches within 18 hours. 5 transactions. |
| **`02-ctr-cash-deposit.xml`** | CTR | Rizwana Garments Ltd (business) | Single threshold cash deposit BDT 12,75,000 at Karwan Bazar branch. Mandatory CTR per BFIU Circular 26. |
| **`03-tbml-over-invoicing.xml`** | TBML | Padma Trading Ltd → Eastern Bay Machinery Holdings (HK) | Import LC settled at USD 4.8M; Customs BE declared USD 1.9M for the same consignment. 2.5x over-invoicing. Filed under MLPA § 2(cc)(18) + (5). |

## How the demo flows

1. Sign in as Sonali CAMLCO (`camlco@kestrel-sonali.test`).
2. Navigate to `/strs`.
3. Click **Choose File** in the Import goAML XML panel.
4. Pick one of the files above.
5. Click **Import XML**.
6. Kestrel parses, creates the draft, ingests transactions into the shared entity pool, resolves subjects.
7. The draft appears in the lifecycle list — open the detail page, see the parsed transactions, edit the narrative, submit.

## What the parser extracts

For each XML the parser pulls:
- `<submission_code>` → report type (STR / CTR / TBML)
- `<reason>` + `<action>` → narrative
- `<reporting_person>` → reporter context
- Every `<transaction>` → a `transactions` row tagged with the import run_id
- Every `<t_from>` / `<t_to>` subject (account / person / phone / entity) → entries in the shared `entities` pool with `same_owner` connections

After import, the subjects show up on `/intelligence/entities` and in cross-bank match clusters if other banks have filed against them.

## Schema notes

The parser is **permissive** — it accepts variations across goAML deployments:
- `<amount>` or `<amount_local>` both accepted.
- `<transactionnumber>` or `<transaction_number>` both accepted.
- `<date_transaction>` ISO 8601 or `<transactiondatetime>` both accepted.
- Subjects can live under `<from_account>` directly or under `<t_from><from_account>` (older Bangladesh goAML profile uses the wrapped form).

These sample files use the wrapped `<t_from>` / `<t_to>` form to match what Sonali Bank's existing goAML pipeline actually emits.

## Editing / extending

Feel free to copy these files, change names + accounts + amounts, and re-import to populate the demo workspace with more variety. The parser is at `engine/app/parsers/goaml_xml.py` if you need to add new field handling.

## Provenance

All amounts, names, account numbers, and NIDs are **synthetic**. Account numbers follow Sonali's 11-13 digit format but do not match any real account. NIDs follow the 10/13/17-digit format but are randomly composed. Hong Kong supplier name is fictional. Do not interpret as real intelligence.
