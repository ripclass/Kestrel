# Demo Script — Bank (CAMLCO + CTO)

**Audience**: CAMLCO + (often) CTO + (sometimes) CFO/CRO
**Run-time**: 35-45 minutes
**Login**: `camlco@kestrel-sonali.test` / `Kestrel!Sonali!2026`
**Goal**: They walk out wanting to run a 30-day pilot.

The path runs against the live production environment using the Sonali Bank demo persona. Memorise the script — the point is to keep eye contact while clicking, not to read off the laptop.

---

## Stop 0 · Setup (before they enter the room)

- HDMI in, hotspot live, laptop already logged in as Sonali CAMLCO at `kestrelfin.com/overview`
- Five printed copies of the bank leave-behind on the table
- Browser zoomed to 110% so they can read from the back of the room

## Stop 1 · Anchor (90 seconds)

**Screen**: laptop closed or on `kestrelfin.com` landing.

> *"Before I show you anything — one number. Ninety percent of suspicious activity in Bangladesh originates inside the banking system. Source: BFIU's own annual report. The reason your CAMLCO finds two percent of it is not your CAMLCO. It's that they only see your bank. Kestrel sits above all of you and stitches the picture back together. That's the whole product. Let me show you what that means."*

Open laptop. Already at `/overview`.

## Stop 2 · The CAMLCO's home screen (3 min)

**Screen**: `/overview` — Sonali Bank PLC dashboard, overview KPIs.

> *"This is what your CAMLCO logs into every morning. Open alerts, recent STRs, the cases queue, and at the top — the cross-bank flag count. Today, four of your subjects are also flagged at peer institutions. Yesterday it was three. The arrow you see is real. Let me click into the cross-bank view."*

Click **Intelligence → Cross-bank** in the sidebar.

## Stop 3 · The centerpiece — Cross-bank intelligence (5 min)

**Screen**: `/intelligence/cross-bank`.

> *"Four entities, BDT 7.26 crore aggregate exposure, four match clusters. This is the view you, as Sonali, are allowed to see. Notice — every peer bank is anonymised. You see 'Peer institution 1, 2, 3, 4' — not the actual names. Match keys are redacted to last four characters. This is the privacy contract that makes the whole thing work: your competitor's CAMLCO sees that this account is also flagged at Sonali, but they don't see your transactions, your STR narratives, your customer book. We do that anonymisation in code, before the data leaves the engine. There's a unit test I can show you. Now — let me click into the highest-severity cluster."*

Click the top match in the **Recent matches** list (the marquee 5-bank cluster — Mohammad Karim phone).

## Stop 4 · The cross-bank dossier (4 min)

**Screen**: entity dossier for the marquee 5-bank match.

> *"Same phone number. Five reporting institutions. Your STR, plus four peers. Aggregate exposure on the trailing 30-day window. Severity critical. You couldn't see this from inside Sonali alone — you can only see four of your own STRs on this subject. The fifth STR sat at BRAC. The sixth at City. Your analyst would never have known. This is the value proposition in three seconds."*

Pause. Let it land.

Click **Operations → Alerts** in the sidebar.

## Stop 5 · An alert with AI explanation (5 min)

**Screen**: `/alerts` list.

Click the first critical alert.

**Screen**: alert detail page.

> *"Here's an alert your scanner generated last night. Risk score 94. Severity critical. But look at the panel on the right — the AI has already written the analyst-ready narrative. 'This account exhibited a structuring pattern across 23 transactions over 72 hours, all under the BDT 5 lakh threshold, all to MFS wallets associated with two peer-bank flagged subjects.' Your CAMLCO doesn't have to read three rules and reconstruct the story. The story is written. They review it, edit it if needed, and click submit."*

## Stop 6 · Draft an STR from the alert (5 min)

**Screen**: same alert page.

Click **Draft STR from alert**.

**Screen**: STR draft form, narrative field pre-filled by AI.

> *"This narrative was drafted in the four seconds it took the page to load. It's editable. It cites the rule that fired. It includes the cross-bank linkage. Your analyst's job becomes: read, judge, edit if necessary, submit. What used to be ninety minutes of writing is now eight minutes of reviewing. Multiply by your STR volume per year and that's the labour saving."*

Don't submit. Cancel and go back.

## Stop 7 · Real-time scoring (the CTO moment) (5 min)

**Screen**: `/monitoring/realtime`.

> *"This is for your CTO. The same engine that scores the alerts overnight also has a real-time API. Your core banking system can call it on every transaction as it goes through NPSB or BEFTN. Sub-500 millisecond decisioning. Returns a score, a decision band — approve / review / hold / reject — and an explainable reason array. Yesterday's calls are charted here in p50, p95, p99 latency. Let me click into a specific decision."*

Click a recent score-log row.

> *"Score 78. Decision: hold. Three reasons: amount-very-large, new-account-high-value, from-sanctions-hit (the receiving party matched OFAC with 0.91 confidence). Your hold-screen operator sees exactly this — score, decision, why. Not a black box."*

## Stop 8 · Hand them the laptop (5 min) ⭐

> *(sliding the laptop across the table to the CAMLCO)*
>
> *"You drive for two minutes. Click on any alert. See what the AI says. See what makes sense and what doesn't. I'll just watch."*

Stay quiet. Let them click. They will surface the questions you wouldn't have thought to address. Answer them in the moment.

## Stop 9 · The bank's own pipeline isn't broken (3 min)

**Screen**: `/strs` (STR reports list).

> *"One last thing your CTO will ask: do we have to throw out our existing goAML XML pipeline? No. Click here — Import STR — drop your goAML XML file, the parser ingests it, every subject lands in the entity pool, it shows up in cross-bank matching the next morning. Export is the inverse: we hand back goAML format XML for BFIU. Your filing pipeline doesn't change. Kestrel sits above it."*

## Stop 10 · Pilot offer + Q&A (5-10 min)

**Hand over the leave-behind.**

> *"Thirty-day pilot at a fixed fee that converts to year-one subscription on contract. Your CAMLCO works in their own tenant — populated with anonymised demo data within ten minutes of signup, then you import your own XML and within a week they're working on real signal. Pricing is on the back of the page you have now. Three tiers, BDT-denominated. We pilot at half-price for first-mover banks in exchange for being a reference. Questions."*

Stop talking. Let them.

---

## Network fallback line (memorise verbatim)

If `kestrelfin.com` doesn't load on their wifi:

> *"Their wifi is restricting our domain — totally normal for a bank, gives us our first compliance question to answer. Switching to my hotspot, two seconds."*

Smile. Switch tether. Move on.

## Practice notes

- Run the script standing up (laptop on a kitchen counter, facing a wall, talking out loud) at least 5 times before the first real meeting.
- Time yourself. Land 35-45 min. If you're running 20% over, you're talking too much. The platform makes the case; you narrate.
- The "hand them the laptop" beat is non-negotiable. Two minutes of them touching the product converts more than twenty minutes of you presenting. Even if it feels awkward.
- Always end the demo by stopping talking. The next sentence is theirs. Don't fill the silence.
