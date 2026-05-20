# Kestrel platform tutorials

**Audience**: bank AML teams, BFIU staff, and anyone evaluating Kestrel.
**Format**: one markdown file per tab, with embedded screenshots. Designed to read straight in any editor, or compile to PDF for distribution.
**Source URL throughout**: [`https://kestrelfin.com`](https://kestrelfin.com)

---

## How to read these tutorials

Each tutorial follows the same shape:

1. **Persona on screen** — which login captured the screenshots.
2. **URL** — the live route.
3. **Full-page screenshot** — orient yourself.
4. **Section-by-section breakdown** — what each visible block is, what it does, where it links to.
5. **Banking 101 boxes** — jargon explained inline so non-banking readers don't get stuck.

Screenshots live next to each tutorial under `screens/NN-tab-slug/`.

---

## Sequence — Director persona (BFIU national lens)

We walk top-down: highest-altitude first, drill down progressively. The Director sees everything, so this is the most complete pass.

| # | Tab | Status |
|---|---|---|
| 01 | [Overview](01-overview.md) | ✅ shipped |
| 02 | [Investigate](02-investigate.md) | ✅ shipped |
| 03 | [Catalogue](03-catalogue.md) | ✅ shipped |
| 04 | [Intelligence (entities)](04-intelligence-entities.md) | ✅ shipped |
| 05 | [New subject](05-new-subject.md) | ✅ shipped |
| 06 | [Saved queries](06-saved-queries.md) | ✅ shipped |
| 07 | [Diagram builder](07-diagram-builder.md) | ✅ shipped |
| 08 | [Cross-bank intelligence](08-cross-bank.md) | ✅ shipped |
| 09 | [Matches](09-matches.md) | ✅ shipped |
| 10 | [Typologies](10-typologies.md) | ✅ shipped |
| 11 | [TBML](11-tbml.md) | ✅ shipped |
| 12 | [STRs](12-strs.md) | ✅ shipped |
| 13 | [Alerts](13-alerts.md) | ✅ shipped |
| 14 | [Cases](14-cases.md) | ✅ shipped |
| 15 | [Disseminations](15-disseminations.md) | ✅ shipped |
| 16 | [Exchange (IERs)](16-iers.md) | ✅ shipped |
| 17 | [Compliance](17-compliance.md) | ✅ shipped |
| 18 | [Trends](18-trends.md) | ✅ shipped |
| 19 | [National · Statistics · Export](19-reports-export.md) | ✅ shipped |
| 20 | [Real-time scoring](20-realtime.md) | ✅ shipped |
| 21 | [Screening](21-screening.md) | ✅ shipped |
| 22 | [Customers (KYC)](22-customers.md) | ✅ shipped |
| 23 | [Admin · Team](23-admin-team.md) | ✅ shipped |
| 24 | [Admin · Rules](24-admin-rules.md) | ✅ shipped |
| 25 | [Admin · Match definitions](25-admin-match-defs.md) | ✅ shipped |
| 26 | [Admin · Reference tables](26-admin-reference.md) | ✅ shipped |
| 27 | [Admin · Schedules](27-admin-schedules.md) | ✅ shipped |
| 28 | [Admin · Status](28-admin-status.md) | ✅ shipped |
| 29 | [Admin · AI outcomes](29-admin-ai-outcomes.md) | ✅ shipped |
| 30 | [Admin · API Keys](30-admin-api-keys.md) | ✅ shipped |

---

## Sequence — Persona deltas (after the Director walk)

Once the Director sequence is done we add three short addendums showing what each lower-privileged persona sees *differently*:

- **D1** — [BFIU Analyst delta](D1-bfiu-analyst-delta.md) ✅ — investigator-tier regulator persona. Same data scope as Director; trimmed Command + Admin tabs.
- **D2** — [Bank CAMLCO delta](D2-bank-camlco-delta.md) ✅ — full commercial-tier surface, peer banks anonymised. Sonali + City demo credentials inside.
- **D3** — [Bank Filer delta](D3-bank-filer-delta.md) ✅ — locked-down filing-only tier (STRs, IERs, Export only). The goAML-replacement free tier under BFIU procurement. BRAC credentials inside.

---

## Compiling to PDF

The tutorials are pure markdown with relative-path PNG references, so any markdown-to-PDF tool works:

- **Pandoc** (preferred for typography): `pandoc tutorials/01-overview.md -o overview.pdf`
- **VS Code "Markdown PDF" extension** — right-click any tutorial → Export PDF.
- **Browser print** — open the markdown in any preview tool, Ctrl+P → Save as PDF.

For a single bundled PDF of the whole sequence, concatenate the tutorials in order before compiling.

---

## Credentials used in the screenshots

| Persona | Email | Password | Notes |
|---|---|---|---|
| BFIU Director | `director@kestrel-bfiu.test` | `Kestrel!BFIU!2026` | full national view |
| BFIU Analyst | `analyst@kestrel-bfiu.test` | `Kestrel!Analyst!2026` | national view, no admin |
| Sonali CAMLCO | `camlco@kestrel-sonali.test` | `Kestrel!Sonali!2026` | commercial tier, peers anonymised |
| City CAMLCO | `camlco@kestrel-city.test` | `Kestrel!City!2026` | commercial tier, peers anonymised |
| BRAC Filer | `filer@kestrel-brac.test` | `Kestrel!Filer!2026` | filing-only tier |

These are seeded test accounts on production, not real bank credentials.
