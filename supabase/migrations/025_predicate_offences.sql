-- Migration 025: Predicate offences (MLPA 2012 §2(cc)) on STR / Case / Dissemination (2026-05-16)
--
-- MLPA Section 2(cc) defines 28 categories of "predicate offence" by
-- committing which (within or outside the country) the money laundered is
-- derived. A procurement-grade ledger must capture which predicate offence
-- drove each STR / Case / Dissemination — both because BFIU's intelligence
-- routing follows the predicate (NBR for customs/tax, ACC for corruption,
-- DNC for narcotics, etc.) and because the Schedule is the legal basis for
-- the ML charge under §4.
--
-- Implemented as text[] so a single STR / Case / Dissemination can cite
-- multiple predicate offences (a TBML case may cite both §2(cc)(18) customs
-- and §2(cc)(19) tax-related offences). Empty array = no predicate offence
-- tagged yet (legacy rows, draft state).
--
-- The 28 categories below are an exact transcription of MLPA 2012 §2(cc)
-- (clauses 1-27 named + 28 catch-all):
--
--    (1)  corruption_and_bribery
--    (2)  counterfeiting_currency
--    (3)  counterfeiting_deeds_and_documents
--    (4)  extortion
--    (5)  fraud
--    (6)  forgery
--    (7)  illegal_trade_firearms
--    (8)  illegal_trade_narcotics              -- drugs, psychotropics, intoxicants
--    (9)  illegal_trade_stolen_goods
--    (10) kidnapping_restraint_hostage
--    (11) murder_grievous_injury
--    (12) trafficking_women_children
--    (13) black_marketing
--    (14) smuggling_currency
--    (15) theft_robbery_dacoity_piracy_hijacking
--    (16) human_trafficking
--    (17) dowry
--    (18) smuggling_customs_excise             -- TBML lives here
--    (19) tax_related_offences                 -- and here
--    (20) infringement_intellectual_property
--    (21) terrorism_or_terrorist_financing
--    (22) adulteration_title_infringement
--    (23) environmental_offences
--    (24) sexual_exploitation
--    (25) insider_trading_market_manipulation
--    (26) organized_crime
--    (27) racketeering
--    (28) other_bb_gazetted                    -- catch-all per MLPA §2(cc)(28)
--
-- The check uses `<@` (is-subset-of) so an empty array always passes (legacy
-- rows continue to validate; new rows must use a value from the canonical set).

ALTER TABLE public.str_reports
  ADD COLUMN predicate_offences text[] NOT NULL DEFAULT '{}'::text[],
  ADD CONSTRAINT str_reports_predicate_offences_check
  CHECK (predicate_offences <@ ARRAY[
    'corruption_and_bribery','counterfeiting_currency','counterfeiting_deeds_and_documents',
    'extortion','fraud','forgery','illegal_trade_firearms','illegal_trade_narcotics',
    'illegal_trade_stolen_goods','kidnapping_restraint_hostage','murder_grievous_injury',
    'trafficking_women_children','black_marketing','smuggling_currency',
    'theft_robbery_dacoity_piracy_hijacking','human_trafficking','dowry',
    'smuggling_customs_excise','tax_related_offences','infringement_intellectual_property',
    'terrorism_or_terrorist_financing','adulteration_title_infringement','environmental_offences',
    'sexual_exploitation','insider_trading_market_manipulation','organized_crime',
    'racketeering','other_bb_gazetted'
  ]::text[]);

ALTER TABLE public.cases
  ADD COLUMN predicate_offences text[] NOT NULL DEFAULT '{}'::text[],
  ADD CONSTRAINT cases_predicate_offences_check
  CHECK (predicate_offences <@ ARRAY[
    'corruption_and_bribery','counterfeiting_currency','counterfeiting_deeds_and_documents',
    'extortion','fraud','forgery','illegal_trade_firearms','illegal_trade_narcotics',
    'illegal_trade_stolen_goods','kidnapping_restraint_hostage','murder_grievous_injury',
    'trafficking_women_children','black_marketing','smuggling_currency',
    'theft_robbery_dacoity_piracy_hijacking','human_trafficking','dowry',
    'smuggling_customs_excise','tax_related_offences','infringement_intellectual_property',
    'terrorism_or_terrorist_financing','adulteration_title_infringement','environmental_offences',
    'sexual_exploitation','insider_trading_market_manipulation','organized_crime',
    'racketeering','other_bb_gazetted'
  ]::text[]);

ALTER TABLE public.disseminations
  ADD COLUMN predicate_offences text[] NOT NULL DEFAULT '{}'::text[],
  ADD CONSTRAINT disseminations_predicate_offences_check
  CHECK (predicate_offences <@ ARRAY[
    'corruption_and_bribery','counterfeiting_currency','counterfeiting_deeds_and_documents',
    'extortion','fraud','forgery','illegal_trade_firearms','illegal_trade_narcotics',
    'illegal_trade_stolen_goods','kidnapping_restraint_hostage','murder_grievous_injury',
    'trafficking_women_children','black_marketing','smuggling_currency',
    'theft_robbery_dacoity_piracy_hijacking','human_trafficking','dowry',
    'smuggling_customs_excise','tax_related_offences','infringement_intellectual_property',
    'terrorism_or_terrorist_financing','adulteration_title_infringement','environmental_offences',
    'sexual_exploitation','insider_trading_market_manipulation','organized_crime',
    'racketeering','other_bb_gazetted'
  ]::text[]);

-- GIN indexes — predicate-offence filtering is common ("show me every TBML
-- STR" = `predicate_offences && ARRAY['smuggling_customs_excise']`).
CREATE INDEX idx_str_predicate_offences ON public.str_reports USING gin (predicate_offences);
CREATE INDEX idx_cases_predicate_offences ON public.cases USING gin (predicate_offences);
CREATE INDEX idx_dissem_predicate_offences ON public.disseminations USING gin (predicate_offences);
