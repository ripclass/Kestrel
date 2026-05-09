# Kestrel Pilot Agreement (Template)

> **⚠ This is a starting template, not a finalised contract.**
>
> Every paragraph below should be reviewed by a Bangladesh-licensed lawyer before first signature. The structure is sound and covers the substantive points a bank's legal team will look for, but specific clauses around limitation of liability, data residency, indemnification, and dispute resolution must be checked against current Bangladesh contract law (the Contract Act 1872, the Digital Security Act 2018, and any BFIU circulars in effect at signing). Sections flagged with `[LAWYER REVIEW]` are the ones most likely to need rewriting; the rest is structural and should hold.
>
> Also: never sign this without a counter-signed mutual NDA already in place. The NDA is a separate one-page document; if the bank doesn't have one ready, ours goes first.

---

## Kestrel Pilot Agreement

This Pilot Agreement ("**Agreement**") is entered into on **[Effective Date]** between:

**ENSO INTELLIGENCE INC.**, a company organised under the laws of [JURISDICTION OF INCORPORATION — to confirm], having its operational office at [Office Address, Dhaka, Bangladesh] (referred to as "**Kestrel**"); and

**[BANK NAME]**, a scheduled bank licensed by Bangladesh Bank under the Bank Companies Act 1991, having its registered office at [Bank Registered Address] (referred to as the "**Bank**"),

each a "**Party**" and together the "**Parties**".

---

## 1. Background

The Bank wishes to evaluate Kestrel's financial-crime intelligence platform ("**Platform**") for its Anti-Money Laundering ("**AML**") and Combating Financing of Terrorism ("**CFT**") workflows under a fixed-term pilot. Kestrel agrees to provision the Platform to the Bank under the terms set out below.

---

## 2. Pilot scope

### 2.1 Platform access

Kestrel shall provision a dedicated tenant on the Platform for the Bank's exclusive use during the Pilot Term. The tenant shall include:

- The full bank-persona surface — alerts, STR drafting, cross-bank intelligence (anonymised), real-time transaction scoring API, sanctions screening, KYC onboarding, goAML XML import and export.
- Up to **[N]** named user accounts for the Bank's CAMLCO and supporting compliance staff. Initial seat allocation is set out in **Schedule A**.
- A populated demo dataset for the first seven (7) days of the Pilot Term, after which the Bank may import its own goAML XML extracts to operate against real signal.
- Email and chat support during Bangladesh business hours (Sunday-Thursday, 09:00-18:00 BST) for the duration of the Pilot Term.

### 2.2 Out of scope

The pilot does **not** include:

- On-premise deployment of the Platform.
- Custom rule authoring beyond the JSON-DSL match-definitions surface.
- Integration with the Bank's core banking system in production. (The real-time scoring API is available for sandbox calls only during the Pilot Term.)
- Live STR filing to BFIU through the Platform. The Bank shall continue to file STRs and CTRs to BFIU through its existing goAML pipeline for the duration of the Pilot Term.

The Bank acknowledges that the Platform is being made available for evaluation only and shall not be relied upon as the Bank's sole AML or CFT control during the Pilot Term.

---

## 3. Term and pilot fee

### 3.1 Pilot Term

The pilot shall commence on **[Pilot Start Date]** and end thirty (30) calendar days later on **[Pilot End Date]** ("**Pilot Term**"), unless terminated earlier in accordance with Section 11.

### 3.2 Pilot fee

The Bank shall pay Kestrel a Pilot Fee of **BDT [Amount]** (the "**Pilot Fee**"), inclusive of all applicable taxes other than VAT, which shall be charged separately if applicable.

### 3.3 Payment terms

The Pilot Fee shall be invoiced on the Effective Date and shall be paid by the Bank within **[fifteen (15)]** business days of invoice receipt. Payment shall be made by bank transfer to the account specified on the invoice.

### 3.4 First-mover discount

If this is one of Kestrel's first three paid pilots in Bangladesh, the Bank is entitled to a fifty percent (50%) reduction in the first six (6) months of any subscription that converts from this pilot, in exchange for being identified as a named reference customer in Kestrel's procurement and marketing materials. The Bank's consent to be named as a reference shall be confirmed in writing before any public reference is made.

`[LAWYER REVIEW]` — confirm the discount mechanism is not characterised as a kickback under any applicable banking regulation.

---

## 4. Success criteria

The Parties shall agree the following success criteria for the pilot, to be assessed jointly at the end of the Pilot Term:

| # | Criterion | Target |
|---|---|---|
| 1 | Cross-bank entity matches surfaced for Bank's existing STR subjects | At least **[3]** clusters where Bank's subjects overlap with peer-bank submissions |
| 2 | AI-drafted STR narratives produced and reviewed by Bank's CAMLCO | At least **[5]** drafts reviewed |
| 3 | Real-time transaction scoring calls made against the API | At least **[1,000]** calls processed end-to-end |
| 4 | Bank-side analyst time saved per STR drafted | At least **[50%]** reduction vs the Bank's existing baseline |
| 5 | Platform availability during Bangladesh business hours | At least **[99%]** measured against `kestrelfin.com/status` |

These targets are indicative starting points; the Parties shall confirm or adjust them within five (5) business days of the Effective Date and record the agreed values in **Schedule B**.

---

## 5. Bank's responsibilities

The Bank shall:

- Designate a Chief AML Compliance Officer (CAMLCO) or equivalent as the Bank's primary contact for the pilot, named in **Schedule A**, with authority to accept user accounts, agree imports of goAML XML, and sign off on success-criteria assessment at end of Pilot Term.
- Designate a technical contact (head of IT or equivalent) for any integration questions during the Pilot Term, also named in **Schedule A**.
- Provide goAML XML extracts of its own choosing for import into the pilot tenant. The Bank decides which extracts to share; Kestrel does not require any particular volume or scope.
- Make its named users available for a one-hour onboarding session within the first three (3) days of the Pilot Term.
- Provide reasonable feedback to Kestrel during weekly pilot check-ins, in particular flagging any issues that affect the success-criteria assessment.

The Bank is not obligated to use the Platform exclusively. The Bank may run any other AML system in parallel during the Pilot Term, and may compare outputs.

---

## 6. Data and confidentiality

### 6.1 Bank's data

All goAML XML extracts, transaction records, customer information, STR narratives, and any other data that the Bank uploads or generates within the pilot tenant shall remain the **exclusive property of the Bank**. Kestrel acquires no ownership rights in such data.

### 6.2 Data residency

Bank Data shall be stored in Singapore (Supabase, ap-southeast-1) for the duration of the Pilot Term. Kestrel undertakes that Bank Data shall not be replicated or transferred outside this region. `[LAWYER REVIEW]` — confirm whether any current BFIU or Bangladesh Bank circular requires AML pilot data to remain inside Bangladesh; if so, the on-premise option must be offered for the pilot itself.

### 6.3 No use for AI training

Kestrel undertakes that Bank Data **shall not** be used to train, fine-tune, or otherwise condition any AI model — whether Kestrel's own, the Platform's third-party providers, or any future model — without the Bank's express prior written consent for each specific use.

### 6.4 Data deletion on termination

Within fifteen (15) business days of the end of the Pilot Term (whether by completion, conversion, or termination), Kestrel shall:
- Permanently delete all Bank Data from production systems, including any backups older than one (1) day; and
- Provide the Bank with a written attestation of deletion signed by an authorised officer of Kestrel.

If the Bank converts to a paid subscription within thirty (30) days of Pilot End, this clause does not apply — the Bank Data carries forward into the subscription tenant.

### 6.5 Mutual confidentiality

Each Party shall keep confidential all information disclosed by the other Party in connection with this Agreement that a reasonable person would regard as confidential, including without limitation the Pilot Fee, the Bank's success-criteria results, and the contents of weekly check-ins.

`[LAWYER REVIEW]` — if a separate Mutual NDA is already executed between the Parties, replace this clause with a cross-reference to it.

---

## 7. Intellectual property

### 7.1 Platform IP

Kestrel retains all right, title, and interest in the Platform, including all software, models, prompts, rules, documentation, and underlying intellectual property. No license is granted under this Agreement except the limited right to access and use the pilot tenant for evaluation purposes during the Pilot Term.

### 7.2 Configurations and rules

Any custom match-definitions, saved queries, or configurations the Bank creates within its pilot tenant are owned by the Bank, but the underlying Platform infrastructure that executes them remains Kestrel's property.

### 7.3 Feedback

The Bank may provide feedback, suggestions, or feature requests to Kestrel during the pilot. Kestrel may use such feedback freely without obligation to compensate the Bank, provided the feedback is anonymised and does not identify the Bank or its customers.

---

## 8. Use restrictions and risk allocation

### 8.1 Evaluation use only

The Platform is provided for evaluation purposes only during the Pilot Term. The Bank shall not rely on the Platform as its production AML or CFT control. The Bank's regulatory obligations to BFIU and Bangladesh Bank under the Money Laundering Prevention Act 2012, the Anti-Terrorism Act 2009, and any related circulars **remain unchanged** and continue to be discharged through the Bank's existing systems.

### 8.2 No regulatory advice

Nothing in this Agreement shall be construed as Kestrel providing legal, regulatory, or compliance advice to the Bank. The Bank's compliance with applicable AML, CFT, and banking regulations remains the Bank's sole responsibility.

### 8.3 Hold harmless during pilot

The Bank acknowledges that the Platform is being evaluated and that no Service Level Agreement applies during the Pilot Term. The Bank agrees to hold Kestrel harmless from any claim, loss, or damage arising from the Bank's use of the Platform during the Pilot Term, **except** in cases of Kestrel's gross negligence, wilful misconduct, or breach of Section 6 (Data and Confidentiality).

`[LAWYER REVIEW]` — the hold-harmless clause is the most contested clause in any pilot agreement; expect to negotiate the carve-outs.

---

## 9. Conversion to paid subscription

### 9.1 Conversion option

Within thirty (30) days of the end of the Pilot Term, the Bank may elect to convert the pilot into a paid subscription on one of Kestrel's then-current commercial tiers (Starter, Professional, or Enterprise) by signing a Subscription Agreement.

### 9.2 Pilot fee credit

If the Bank converts within thirty (30) days of Pilot End, the Pilot Fee shall be credited in full against the first invoice under the resulting Subscription Agreement.

### 9.3 Tier and pricing

The published BDT pricing on `kestrelfin.com/pricing` at the date of Pilot End shall apply, subject to the first-mover discount in Section 3.4 if applicable.

### 9.4 No obligation to convert

The Bank is under no obligation to convert. If the Bank elects not to convert, this Agreement shall terminate at the end of the conversion window in accordance with Section 11.

---

## 10. Limitation of liability

### 10.1 Cap

`[LAWYER REVIEW]` — Each Party's total aggregate liability under this Agreement, whether in contract, tort, or otherwise, shall not exceed the Pilot Fee actually paid by the Bank to Kestrel under this Agreement.

### 10.2 Excluded damages

Neither Party shall be liable for any indirect, incidental, consequential, or special damages, including without limitation lost profits, lost data, or business interruption, even if advised of the possibility of such damages.

### 10.3 Carve-outs

The limitation in Section 10.1 shall not apply to:
- Either Party's breach of Section 6 (Data and Confidentiality);
- Either Party's wilful misconduct or fraud;
- Either Party's indemnification obligations under this Agreement, if any.

---

## 11. Termination

### 11.1 Termination at end of Pilot Term

This Agreement shall terminate automatically at the end of the Pilot Term unless extended by written agreement of both Parties or converted into a Subscription Agreement under Section 9.

### 11.2 Termination for breach

Either Party may terminate this Agreement on written notice to the other Party if:
- The other Party materially breaches this Agreement and fails to cure the breach within ten (10) business days of receiving written notice; or
- The other Party becomes insolvent, enters into liquidation, or is unable to pay its debts as they fall due.

### 11.3 Effect of termination

On termination for any reason:
- All access to the pilot tenant shall be revoked within twenty-four (24) hours.
- Section 6.4 (Data deletion on termination), Section 6.5 (Mutual confidentiality), Section 7 (Intellectual property), Section 10 (Limitation of liability), and this Section 11.3 shall survive.

---

## 12. Governing law and dispute resolution

### 12.1 Governing law

This Agreement shall be governed by and construed in accordance with the laws of the People's Republic of Bangladesh.

### 12.2 Dispute resolution

`[LAWYER REVIEW]` — Any dispute arising out of or in connection with this Agreement that cannot be resolved by good-faith negotiation between the Parties within thirty (30) days shall be submitted to arbitration under the rules of the Bangladesh International Arbitration Centre (BIAC), seated in Dhaka, in English, before a sole arbitrator appointed by mutual agreement (or, failing agreement, by BIAC).

### 12.3 Injunctive relief

Notwithstanding Section 12.2, either Party may seek injunctive or other equitable relief in any court of competent jurisdiction in respect of breaches of Section 6 (Data and Confidentiality) or Section 7 (Intellectual property).

---

## 13. General

### 13.1 Notices

Any notice under this Agreement shall be in writing and sent to the addresses set out at the beginning of this Agreement, with a copy by email to the addresses set out in **Schedule A**. Notices sent by email shall be deemed received on the next Bangladesh business day.

### 13.2 Assignment

Neither Party may assign this Agreement without the prior written consent of the other Party, except that Kestrel may assign this Agreement in connection with a merger, acquisition, or sale of substantially all of its assets, on written notice to the Bank.

### 13.3 Entire agreement

This Agreement (together with its Schedules and any Mutual NDA executed between the Parties) constitutes the entire agreement between the Parties in respect of the pilot and supersedes all prior discussions, proposals, and agreements.

### 13.4 Amendments

Any amendment to this Agreement must be in writing and signed by authorised representatives of both Parties.

### 13.5 Severability

If any provision of this Agreement is held to be unenforceable, the remaining provisions shall continue in full force and effect.

---

## 14. Signatures

**For Enso Intelligence Inc. ("Kestrel"):**

Name:  ____________________________________
Title: ____________________________________
Date:  ____________________________________
Signature: ________________________________

**For [Bank Name] ("the Bank"):**

Name:  ____________________________________
Title: ____________________________________
Date:  ____________________________________
Signature: ________________________________

**Witness (Bank side):**

Name:  ____________________________________
Designation: ______________________________
Signature: ________________________________

---

## Schedule A — Named contacts and seat allocation

**Bank side:**

| Role | Name | Email | Phone |
|---|---|---|---|
| CAMLCO (primary contact) | | | |
| Technical contact | | | |
| Additional named users | | | |

**Kestrel side:**

| Role | Name | Email | Phone |
|---|---|---|---|
| Founder / pilot lead | Ripon Chowdhury | ripon.chowdhury@kestrelfin.com | [Phone] |
| Technical contact | | support@kestrelfin.com | |

---

## Schedule B — Agreed success criteria

To be completed within five (5) business days of the Effective Date and signed by both CAMLCO and Founder.

| # | Criterion | Target | Measurement source | Reviewed by |
|---|---|---|---|---|
| 1 | | | | |
| 2 | | | | |
| 3 | | | | |
| 4 | | | | |
| 5 | | | | |

---

## Schedule C — Mutual NDA

`[LAWYER REVIEW]` — Either reference the existing Mutual NDA between the Parties (with execution date) or attach a one-page Mutual NDA as a separate document. Do not skip; a pilot agreement without a counter-signed NDA is unenforceable.

---

*Template version 2026-Q2. Maintained by Enso Intelligence Inc. Not legal advice. Review by Bangladesh-licensed counsel required before first signature.*
