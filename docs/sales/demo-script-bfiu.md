# Demo Script — BFIU (Director + Analyst lead)

**Audience**: BFIU Director (or Joint Director) + Analyst lead + (often) IT/procurement
**Run-time**: 50-60 minutes
**Login**: `director@kestrel-bfiu.test` / `Kestrel!BFIU!2026`
**Goal**: They walk out wanting a national-deployment proposal.

The path runs against the live production environment using the BFIU director persona — anonymisation off, real bank names visible, full match keys, regulator-only surfaces unlocked.

---

## Stop 0 · Setup (before they enter the room)

- Same as bank flow, except logged in as `director@kestrel-bfiu.test`
- Already at `/reports/national`
- Leave-behind is the **regulator** version — emphasises on-prem, sovereign LLM, multi-year contract, no public sticker
- Bring two extra copies — BFIU meetings always grow mid-conversation

## Stop 1 · Anchor (2 min)

> *"BFIU receives roughly fourteen thousand STRs and SARs every year. They are read by hand. Cross-referenced by hand. Disseminated by hand. The system you use to receive them — goAML — was designed in 2006 as a filing cabinet. It does not perform cross-bank entity resolution. It cannot anonymise peer signals. It cannot. Kestrel does both. And it preserves every goAML vocabulary your analysts already know. Let me show you what we mean by that."*

## Stop 2 · The Director's command view (4 min)

**Screen**: `/reports/national`.

> *"Six banks reporting today. Forty alerts in the trailing thirty days. Ten STRs across the system. Seven cross-bank match clusters, two of them critical. Four banks with declining alert-conversion. This is the picture no one in Bangladesh has had before because no one operated above all the banks at once. You do, now."*

## Stop 3 · Cross-bank intelligence at full strength (8 min)

Click **Intelligence → Cross-bank** in the sidebar.

**Screen**: `/intelligence/cross-bank` — but rendered for the regulator persona.

> *"This is the same dashboard your bank-CAMLCOs see — but rendered for you, with anonymisation off. Real bank names. Full match keys. Aggregate exposure across the system. The marquee cluster at the top — Mohammad Karim's phone — is reported by five institutions in the last thirty days. BRAC, City, Dutch-Bangla, Islami, Sonali. Bank-side analysts each see four of those six STRs. You see all six. Click in."*

Click into the marquee cluster.

**Screen**: entity dossier with the full network graph.

> *"Network graph rendered automatically. Each node is an entity. Each edge is a connection — same NID, same phone, transaction flow, KYC overlap. Vermillion edges are flagged paths. You can two-hop neighbours, save the dossier as a case, dispatch an IER to a peer FIU, or hand the case-pack as a watermarked PDF to law enforcement. Let me show you the IER workflow."*

## Stop 4 · IER workflow (7 min)

Click **Operations → IERs**.

**Screen**: `/iers` list.

> *"Information Exchange Request. The Egmont workflow. Inbound on the left, outbound on the right. Your director can dispatch a request to FinCEN, AUSTRAC, or a peer Egmont FIU directly from any subject record. Each one carries the counterparty FIU, an Egmont reference, a deadline, and request and response narratives. Outbound dispatched goes into your dissemination ledger. Inbound from peers comes into the same surface. Click."*

Click **+ New IER**.

> *"Dropdowns for the counterparty FIU. Free-text Egmont reference. Outbound or inbound direction. Subject auto-resolves from the entity pool. The whole thing posts in the goAML format your peer FIU expects. You don't write XML. We write XML."*

Cancel without sending.

## Stop 5 · Dissemination ledger (5 min)

Click **Intelligence → Disseminations**.

**Screen**: `/intelligence/disseminations`.

> *"Every dissemination from BFIU to law enforcement, peer FIUs, prosecutors, and courts. Recipient typed. Source record linked. Audit trail keyed to the disseminator's identity, append-only, no edit, no override. This is the ledger your audit committee asks for. It exports to Excel with one click."*

## Stop 6 · National statistics (7 min)

Click **Command → National**.

**Screen**: `/reports/national` deeper view.

> *"Reports by type by month, stacked. Reports by org, horizontal bar. CTR volume trend. Disseminations by recipient, pie. Case outcomes. Average time-to-review per report type. Each of these used to take BFIU's data team a week to compile from goAML exports plus Excel. They are live here. Press export, you get the file your finance committee asked for."*

Click **Export → Compliance scorecard**.

> *"Or this — the compliance scorecard. Bank-by-bank rank on submission timeliness, alert conversion rate, peer coverage. Your benchmark against the system. The bank in last place will know that they're in last place."*

## Stop 7 · goAML vocabulary preserved (5 min)

Click **Investigate → Catalogue**.

**Screen**: `/investigate/catalogue` — twelve-tile grid.

> *"This is the screen your analysts already know. The same twelve labelled lookups you use in goAML — Account, Person, Entity, Address, Text, Quick Finder, Transaction, Report, Intelligence Report, Templates, Journal, Dissemination Lookup. Same vocabulary, same rationale, same muscle memory. Underneath: a single fuzzy search across the entire reporting universe. Faster, better, but the screen reads as goAML to the operator."*

Hover over each tile. Show the goAML provenance tooltip.

## Stop 8 · Match definitions (5 min)

Click **Admin → Match Definitions**.

> *"Custom rule authoring. JSON DSL. Your senior analysts write match conditions — 'flag any subject reported by ≥ 3 banks within a 14-day window with aggregate exposure above five crore' — they go live, the engine runs them on every scan, alerts come in deduped against existing alerts. This is the goAML Match Definitions surface, modernised. No Windows desktop. No vendor consultation."*

## Stop 9 · Hand them the laptop (5 min) ⭐

> *(sliding the laptop to the analyst, not the director)*
>
> *"Click around for two minutes. Find a subject. Pull up the dossier. Open the network graph. I'll watch."*

The analyst is the one who will actually use this. The director makes the decision but the analyst makes the case for the decision. Five minutes of analyst clicking is worth twenty minutes of you presenting.

## Stop 10 · The procurement framing (8-10 min)

**Hand over the regulator leave-behind.**

> *"Three deployment options. Hosted on Singapore Supabase, which we run today. On-premise inside BFIU's data centre — same engine image, same web image, sovereign LLM running locally, watchlist refresh from offline source archives, no outbound network calls to OpenAI or Anthropic. Or hybrid — BFIU on-prem, banks on the hosted platform, peering at the cross-bank intelligence layer. Pricing is structured around scope of deployment, multi-year contract, bundled with implementation, training, and a dedicated technical account manager. The page you have in your hand has the proposal-request form. You'll know the numbers within ten business days of returning it. Questions."*

Stop talking. Let them.

---

## Network fallback line (memorise verbatim)

If `kestrelfin.com` doesn't load on their wifi:

> *"Their wifi is restricting our domain — totally normal for a regulator network, gives us our first deployment question to answer. Switching to my hotspot, two seconds."*

## Practice notes

- BFIU meetings tend to grow. Plan the script for 50-60 min of platform demo + budget another 30-45 min for procurement / deployment / contracting questions you can't fully predict.
- The analyst lead's reaction is the leading indicator. If the analyst is leaning forward by Stop 4, the deal works. If they're leaning back, you've lost the room — pivot to "what would you need to see to be convinced?" and re-anchor.
- Avoid technical detail unless the IT representative asks. Director and analyst care about workflow, vocabulary, and outcomes — not RLS policies. Save the architecture deep-dive for a follow-up call with their CTO.
- Don't quote price during the meeting. The leave-behind says *"pricing structured around scope of deployment, not published publicly"* — let the proposal request form do the work.
