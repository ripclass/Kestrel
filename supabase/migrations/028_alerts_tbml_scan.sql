-- Migration 028: alerts gains TBML-scan source_type + predicate_offences + linked_trade_id + bfiu_avenue_ref (2026-05-16)
--
-- Phase B continuation. The TBML detection rules from the previous PR emit
-- TradeRuleHit objects that need to land in `alerts` with:
--
--   * source_type = 'tbml_scan'   — distinct from 'scan' (account-centric
--                                    detection runs) and 'cross_bank' (entity
--                                    match alerts). A TBML scan is its own
--                                    workflow and its own queue.
--   * predicate_offences[]        — MLPA §2(cc) codes the rule pre-populates
--                                    (e.g. ['smuggling_customs_excise',
--                                    'tax_related_offences']). Migration 025
--                                    put this column on STR + Case +
--                                    Dissemination; this brings alerts into
--                                    the same regulatory shape.
--   * linked_trade_id             — FK to trade_transactions so a reviewer
--                                    can open the source trade in one click.
--   * bfiu_avenue_ref             — BFIU TBML Guidelines section that the
--                                    matched rule cites (e.g. '2.4.1.iv').
--                                    Traceability for procurement reviewers.
--
-- Two CHECK relaxations + three additive columns + one index. Idempotent
-- and zero data shift — existing alerts continue to resolve against the
-- new constraints with NULL/empty defaults.

-- Allow source_type='tbml_scan'.
ALTER TABLE public.alerts
  DROP CONSTRAINT IF EXISTS alerts_source_type_check;

ALTER TABLE public.alerts
  ADD CONSTRAINT alerts_source_type_check
  CHECK (source_type IN (
    'scan',
    'cross_bank',
    'str_enrichment',
    'manual',
    'match_definition',
    'kyc_rescreen',
    'tbml_scan'
  ));

-- Add predicate_offences[] with the same canonical 28-code set as STR/Case/Dissemination.
ALTER TABLE public.alerts
  ADD COLUMN predicate_offences text[] NOT NULL DEFAULT '{}'::text[],
  ADD CONSTRAINT alerts_predicate_offences_check
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

-- Add linked_trade_id (nullable FK to trade_transactions).
ALTER TABLE public.alerts
  ADD COLUMN linked_trade_id uuid NULL REFERENCES public.trade_transactions(id) ON DELETE SET NULL,
  ADD COLUMN bfiu_avenue_ref text NULL;

-- Lookup index for the TBML alerts queue and per-trade alert lookup.
CREATE INDEX idx_alerts_predicate_offences ON public.alerts USING gin (predicate_offences);
CREATE INDEX idx_alerts_linked_trade_id ON public.alerts (linked_trade_id)
  WHERE linked_trade_id IS NOT NULL;
CREATE INDEX idx_alerts_tbml_scan ON public.alerts (org_id, created_at DESC)
  WHERE source_type = 'tbml_scan';
