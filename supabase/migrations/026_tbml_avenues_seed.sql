-- Migration 026: TBML-avenue support columns on typologies + seed 29 BD-specific TBML avenues (2026-05-16)
--
-- BFIU TBML Guidelines 2019 (issued under BFIU Circular 24 of 10 Dec 2019)
-- enumerates 29 BD-specific TBML avenues in Sections 2.4.1 (14 import), 2.4.2
-- (14 export), and 2.5 (1 royalty / technical-fee remittance). The procurement
-- meeting feedback that motivates this seed: "you have 5 generic typologies;
-- BFIU recognises 29 BD-specific TBML avenues — align."
--
-- Schema additions (additive, nullable for back-compat with the 5 existing
-- rows):
--
--   * predicate_offences text[]   — MLPA 2012 §2(cc) clauses cited (from
--                                    migration 025; same canonical 28-set).
--                                    Most TBML avenues cite §2(cc)(18)
--                                    smuggling+customs and §2(cc)(19) tax
--                                    together.
--   * mlpa_section text           — Enabling clause if BFIU has tagged this
--                                    typology to a specific MLPA / ATA
--                                    section (mostly unused on TBML rows;
--                                    populated where the source doc cites
--                                    a section explicitly).
--   * bfiu_avenue_ref text        — Stable BFIU citation key: section ref
--                                    in the TBML Guidelines (e.g. '2.4.1.i'
--                                    for the first import avenue) so a
--                                    reviewer can map any row back to the
--                                    source paragraph in 1 step.
--
-- Seed inserts 29 rows with deterministic IDs `tbml-avenue-import-NN`,
-- `tbml-avenue-export-NN`, `tbml-avenue-royalty-01`. ON CONFLICT DO NOTHING
-- so re-running the migration is idempotent.

ALTER TABLE public.typologies
  ADD COLUMN predicate_offences text[] NOT NULL DEFAULT '{}'::text[],
  ADD COLUMN mlpa_section text NULL,
  ADD COLUMN bfiu_avenue_ref text NULL;

CREATE INDEX idx_typologies_bfiu_avenue_ref ON public.typologies (bfiu_avenue_ref)
  WHERE bfiu_avenue_ref IS NOT NULL;
CREATE INDEX idx_typologies_predicate_offences ON public.typologies USING gin (predicate_offences);

-- Seed: 14 import TBML avenues — BFIU TBML Guidelines 2019 §2.4.1 ----------

INSERT INTO public.typologies
  (id, title, category, channels, indicators, narrative, predicate_offences, bfiu_avenue_ref)
VALUES
  ('tbml-avenue-import-01', 'IRC abuse — multiple registrations per trader', 'tbml',
   ARRAY['LC','BTB','open_account'],
   ARRAY['Multiple IRCs per family or business address','Trader identified only by IRC, not name'],
   'Importers identified through Importer Registration Certificate (IRC) — not by name. Holders take multiple IRCs (one commercial + one industrial, family-linked, or surrendered-and-renewed) to obscure beneficial ownership during TBML.',
   ARRAY['smuggling_customs_excise','tax_related_offences']::text[], '2.4.1.i'),

  ('tbml-avenue-import-02', 'LCAF value violation via FC / ERQ payment', 'tbml',
   ARRAY['LC','wire'],
   ARRAY['Payment exceeds declared LCAF value','FC / ERQ accounts used to top up'],
   'Letter of Credit Authorisation Form (LCAF) declares amount + HS code + description. Importers abuse FC or ERQ accounts to pay more than the declared LCAF or beyond expiry, settling the difference outside the formal banking channel.',
   ARRAY['smuggling_customs_excise','tax_related_offences']::text[], '2.4.1.ii'),

  ('tbml-avenue-import-03', 'CFR freight charge inflation', 'tbml',
   ARRAY['LC'],
   ARRAY['Freight charges several times FOB value','CFR-basis imports'],
   'Most BD imports are CFR — freight charges are invoiced to the importer. Inflated freight (multiples of FOB value) is a TBML channel moving value out via the freight leg rather than the goods leg.',
   ARRAY['smuggling_customs_excise','tax_related_offences']::text[], '2.4.1.iii'),

  ('tbml-avenue-import-04', 'Under / over-invoicing + hundi-hawala settlement', 'tbml',
   ARRAY['LC','informal'],
   ARRAY['Invoice value below market for high-duty goods','Invoice value above market for low-duty capital machinery','Hundi or hawala flows in parallel'],
   'Value of imported goods is quoted below actual (under-invoicing) to evade duties + the differential is paid via hundi or hawala. Alternately, capital machinery and low-duty raw materials are over-invoiced to siphon money abroad through the LC. Tax evasion is the underlying ML predicate.',
   ARRAY['smuggling_customs_excise','tax_related_offences','black_marketing']::text[], '2.4.1.iv'),

  ('tbml-avenue-import-05', 'Direct-to-importer documents + customs BE fabrication', 'tbml',
   ARRAY['LC'],
   ARRAY['Documents not routed through bank','Payment authorised on submitted Bill of Entry'],
   'When documents are received directly by the importer (not routed through the bank) and customs releases goods on copy documents, banks may pay based on the importer-submitted BE. Fabrication of import documents + matching BE becomes a TBML medium.',
   ARRAY['smuggling_customs_excise','forgery','fraud']::text[], '2.4.1.v'),

  ('tbml-avenue-import-06', 'Fabricated bank-guarantee advance import payment', 'tbml',
   ARRAY['wire','LC'],
   ARRAY['Advance remittance against import without BB approval','Foreign-bank repayment guarantee suspicious'],
   'ADs are permitted advance import payment without prior BB approval if backed by a foreign bank repayment guarantee (not needed below USD 5,000 / USD 25,000 ERQ). Fabricated or false guarantees enable TBML through advance remittance.',
   ARRAY['smuggling_customs_excise','fraud','forgery']::text[], '2.4.1.vi'),

  ('tbml-avenue-import-07', 'Overdue Bill of Entry → IRC surrender → fresh start', 'tbml',
   ARRAY['LC'],
   ARRAY['BE overdue beyond 4 months','IRC surrender pattern','New IRC issued to same beneficial owner'],
   'Importer fails to transport goods within 4 months → BE becomes overdue → importer surrenders the IRC (to escape import liability) and obtains a new IRC for a fresh start. The surrendered remittance is the laundered amount.',
   ARRAY['smuggling_customs_excise','tax_related_offences']::text[], '2.4.1.vii'),

  ('tbml-avenue-import-08', 'Insurance compensation rerouted to third party', 'tbml',
   ARRAY['wire'],
   ARRAY['Damage / loss / cancellation event','Compensation received from unrelated third party','BE waiver claimed'],
   'Loss or damage of in-transit goods, or shipment cancellation, becomes a TBML medium when compensation is received from a third party unrelated to the exporter. Manufactured loss-before-release events enable BE waivers + capital flight.',
   ARRAY['fraud','smuggling_customs_excise']::text[], '2.4.1.viii'),

  ('tbml-avenue-import-09', 'Back-to-back LC + bonded warehouse abuse', 'tbml',
   ARRAY['BTB','LC'],
   ARRAY['BTB LC against arranged or fake master LC','Bonded warehouse goods diverted to local market','No matching export against the BTB'],
   'Back-to-back import LCs against fake or arranged master export LCs allow raw materials in duty-free under the bonded-warehouse system — then diverted to local market without the export ever occurring. Tax evasion is the predicate ML offence.',
   ARRAY['smuggling_customs_excise','tax_related_offences','fraud']::text[], '2.4.1.ix'),

  ('tbml-avenue-import-10', 'Deferred / usance / buyers credit misuse', 'tbml',
   ARRAY['LC'],
   ARRAY['Deferred or usance LC structure','Buyers credit / suppliers credit settlement','Credit terms inconsistent with trade profile'],
   'Deferred LC under Chapter 7 Para 33(a) of GFET 2018, or usance-basis LC, allows settlement through buyers credit or suppliers credit — abused for value transfer when credit terms are inconsistent with trade profile.',
   ARRAY['smuggling_customs_excise','tax_related_offences']::text[], '2.4.1.x'),

  ('tbml-avenue-import-11', 'CMT + Free-of-Cost raw material manipulation', 'tbml',
   ARRAY['LC','FOC'],
   ARRAY['Cutting Making and Trimming exports','Free-of-Cost raw material import','No bank endorsement on FOC items'],
   'Exporters on Cutting / Making / Trimming basis are allowed Free-of-Cost raw material imports. No bank endorsement + no BE matching with value enables manipulation of FOC quantities / values for TBML.',
   ARRAY['smuggling_customs_excise','tax_related_offences']::text[], '2.4.1.xi'),

  ('tbml-avenue-import-12', 'Non-physical goods (software / services) import', 'tbml',
   ARRAY['wire'],
   ARRAY['Import of software, IP, or services','No customs tracking on non-physical goods'],
   'Import of non-physical goods (software, services, IP) is hard for any reporting / regulatory agency to track. The lack of physical-good verification turns these imports into a hidden TBML channel.',
   ARRAY['smuggling_customs_excise','tax_related_offences','infringement_intellectual_property']::text[], '2.4.1.xii'),

  ('tbml-avenue-import-13', 'Personal-consumption USD 7,000 limit abuse', 'tbml',
   ARRAY['wire','card'],
   ARRAY['Import Policy Order USD 7,000 / year personal limit','Same individual importing through multiple ADs','Commercial-scale onward sale'],
   'Import Policy Order allows actual users to import up to USD 7,000 / year for personal consumption. With no AD-side monitoring of the aggregate limit, individuals import through different ADs above the cap and sell commercially.',
   ARRAY['smuggling_customs_excise','tax_related_offences']::text[], '2.4.1.xiii'),

  ('tbml-avenue-import-14', 'Online card payment + courier import', 'tbml',
   ARRAY['card','courier'],
   ARRAY['International debit / credit / prepaid card import payment','Courier delivery from foreign supplier','Travel Quota balance used'],
   'Consumers purchase goods online via international debit / credit / prepaid cards or unused Travel Quota and receive courier delivery. Criminal proceeds can be moved via this online-card import channel.',
   ARRAY['smuggling_customs_excise','tax_related_offences']::text[], '2.4.1.xiv'),

  -- Seed: 14 export TBML avenues — BFIU TBML Guidelines 2019 §2.4.2 ---------

  ('tbml-avenue-export-01', 'ERC abuse — multiple registrations per exporter', 'tbml',
   ARRAY['LC','open_account'],
   ARRAY['Multiple ERCs per exporter','Reporting by ERC not by name'],
   'Exporter Registration Certificate (ERC) identifies exporters in reporting. Holders take multiple ERCs to use one in TBML — obscuring beneficial ownership and aggregate export volume.',
   ARRAY['smuggling_customs_excise','tax_related_offences']::text[], '2.4.2.i'),

  ('tbml-avenue-export-02', 'Under-invoicing of export goods', 'tbml',
   ARRAY['LC','open_account'],
   ARRAY['Invoice value below market','Settlement outside banking channel'],
   'Export goods are invoiced below actual value with the differential settled outside the formal banking channel — value is siphoned abroad. Customs and tax authorities are the most affected predicate-offence regulators.',
   ARRAY['smuggling_customs_excise','tax_related_offences']::text[], '2.4.2.ii'),

  ('tbml-avenue-export-03', 'Overdue export bill / repatriation failure', 'tbml',
   ARRAY['LC'],
   ARRAY['Export proceeds not repatriated within 4 months','Section 12 FERA breach','Pattern of overdue bills'],
   'Section 12 of FERA 1947 requires exporters to repatriate full export proceeds within 4 months of shipment. Deliberate failure to repatriate is a TBML signal — proceeds are retained abroad.',
   ARRAY['smuggling_customs_excise','tax_related_offences','smuggling_currency']::text[], '2.4.2.iii'),

  ('tbml-avenue-export-04', 'Commission / brokerage padding to foreign agents', 'tbml',
   ARRAY['wire'],
   ARRAY['Foreign-agent commission near 5% cap','Brokerage payments inconsistent with deal economics'],
   'ADs can allow up to 5% of export value as commission, brokerage or trade charges to foreign importers / agents. Padding the commission to the cap is a value-transfer channel.',
   ARRAY['smuggling_customs_excise','tax_related_offences','fraud']::text[], '2.4.2.iv'),

  ('tbml-avenue-export-05', 'International card payment manipulation', 'tbml',
   ARRAY['card'],
   ARRAY['Debit / credit / prepaid card payment for export','Card-issuance + end-use mismatch with Chapter 19 GFET 2018'],
   'Payments in foreign exchange via international cards (debit / credit / prepaid) per Chapter 19 of GFET 2018 should be meticulously monitored by ADs. Card-payment manipulation outside the documented end-use is a TBML medium.',
   ARRAY['smuggling_customs_excise','tax_related_offences']::text[], '2.4.2.v'),

  ('tbml-avenue-export-06', 'Partial drawing / advance receipt abuse', 'tbml',
   ARRAY['LC'],
   ARRAY['Partial drawing on export bill','Advance receipt against export with balance never realised'],
   'Partial drawing of export bills or advance receipts where the balance amount is never realised. ADs must follow up each such case — pattern of unrealised balances is a TBML indicator.',
   ARRAY['smuggling_customs_excise','tax_related_offences','fraud']::text[], '2.4.2.vi'),

  ('tbml-avenue-export-07', 'Shipment shut-out + re-shipment routing', 'tbml',
   ARRAY['LC'],
   ARRAY['Vessel shut-out','Re-shipment via different vessel / jurisdiction','Transshipment without economic rationale'],
   'Shutting out of shipment by one vessel and re-shipment by another — particularly via transshipment through one or more jurisdictions with no apparent economic reason — is a classic TBML routing technique.',
   ARRAY['smuggling_customs_excise','smuggling_currency']::text[], '2.4.2.vii'),

  ('tbml-avenue-export-08', 'Export-side insurance compensation from third party', 'tbml',
   ARRAY['wire'],
   ARRAY['Loss / damage event on exported goods','Compensation from third party unrelated to importer'],
   'Compensation against damaged exported goods, or cancellation compensation, received from a third party unrelated to the importer is a TBML routing — the third party is the off-the-books settler.',
   ARRAY['fraud','smuggling_customs_excise']::text[], '2.4.2.viii'),

  ('tbml-avenue-export-09', 'Non-physical goods (software / services) export', 'tbml',
   ARRAY['wire'],
   ARRAY['Software / IP / service export','No customs tracking on non-physical exports'],
   'Export of non-physical goods (software, services) is hard to track for any reporting / regulatory agency — making it a hidden TBML channel for value movement disguised as service export.',
   ARRAY['smuggling_customs_excise','tax_related_offences','infringement_intellectual_property']::text[], '2.4.2.ix'),

  ('tbml-avenue-export-10', 'Buying house / buyer-nominated supplier arrangement', 'tbml',
   ARRAY['LC'],
   ARRAY['Buying house intermediary','Buyer-nominated supplier','Arranged delay + discount on export value'],
   'Buying House Arrangement / Buyer-Nominated Supplier Arrangement: shipments are delayed by buying houses through arranged-game tactics for export-value discount, or buyer-nominated suppliers quote higher raw material prices to launder money.',
   ARRAY['smuggling_customs_excise','tax_related_offences','fraud']::text[], '2.4.2.x'),

  ('tbml-avenue-export-11', 'Large-volume non-banking-channel transactions', 'tbml',
   ARRAY['exchange_house','informal'],
   ARRAY['Large-volume settlement via exchange house','Non-banking channel for export proceeds'],
   'Transactions in large volume settled through channels other than banking — exchange houses, informal routes — are inherently vulnerable to TBML because they bypass AD-side recording.',
   ARRAY['smuggling_customs_excise','smuggling_currency']::text[], '2.4.2.xi'),

  ('tbml-avenue-export-12', 'Wage-earner remittance disguised as export proceeds (cash-incentive fraud)', 'tbml',
   ARRAY['wire'],
   ARRAY['Inward remittance branded as export proceeds','Wage-earner-style sender names','Cash-incentive claim filed'],
   'Wage-earner remittance is brought into Bangladesh in the name of export proceeds to claim BB cash incentives. The cash incentive scheme is gamed via mis-attributed inward remittance.',
   ARRAY['fraud','tax_related_offences']::text[], '2.4.2.xii'),

  ('tbml-avenue-export-13', 'Related-business-country inward remittance for cash incentive', 'tbml',
   ARRAY['wire'],
   ARRAY['Inward remittance from country where Bangladeshi has business','Cash-incentive claim filed'],
   'Inward remittance from countries where Bangladeshis have direct or indirect business may be brought in as export proceeds, with cash incentive claimed — looping value through related-party offshore companies.',
   ARRAY['fraud','tax_related_offences']::text[], '2.4.2.xiii'),

  ('tbml-avenue-export-14', 'Usance bill discounting / documentary export bill abuse', 'tbml',
   ARRAY['LC'],
   ARRAY['Usance bill discounting','Foreign documentary export bill purchase','Discount inconsistent with deal economics'],
   'ADs are allowed to discount usance bills and purchase foreign documentary export bills per Chapter 8 Para 25 of GFET 2018. Abuse via aggressive discounting on suspicious bills is a TBML channel — utmost care is mandated.',
   ARRAY['smuggling_customs_excise','tax_related_offences','fraud']::text[], '2.4.2.xiv'),

  -- Seed: 1 royalty / technical-fee avenue — BFIU TBML Guidelines 2019 §2.5 ---

  ('tbml-avenue-royalty-01', 'Royalty / technical-fee / management-fee remittance', 'tbml',
   ARRAY['wire'],
   ARRAY['Ambiguous agreement between local company + foreign technical-service provider','Suspicious auditor certificate on net remittable amount','Lack of due diligence on underlying trade'],
   'Remittance of royalty, technical assistance, operational service fees, management fees, franchise fees under BIDA Act 2016 §18. Without proper due diligence on the underlying agreement + auditor certificate, this becomes a TBML channel disguised as fee remittance.',
   ARRAY['smuggling_customs_excise','tax_related_offences','infringement_intellectual_property']::text[], '2.5')
ON CONFLICT (id) DO NOTHING;
