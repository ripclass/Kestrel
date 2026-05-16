-- Migration 023: bank_filer persona + filing_only plan (2026-05-16)
--
-- Adds the "goAML replacement" tier that BFIU procurement provisions for every
-- bank in Bangladesh at no cost. Filer-persona users see only the STR / CTR /
-- IER submission surface; cross-bank intelligence, AI explanations, real-time
-- scoring, KYC, sanctions, case management, and admin surfaces stay hidden.
--
-- This is the path that makes Kestrel a credible goAML replacement under a
-- national contract — banks keep filing, BFIU consumes the intelligence layer,
-- commercial revenue is a separate bank-direct relationship at a paid tier.
--
-- Two CHECK relaxations, no data shift:
--   1. profiles.persona += 'bank_filer'
--   2. organizations.plan_id += 'filing_only'
--
-- No regulator org gets bumped (they stay on 'enterprise').
-- No bank org gets bumped automatically — BFIU operator runs the bulk
-- onboarding tool to flip newly provisioned bank tenants to filing_only.

ALTER TABLE public.profiles
  DROP CONSTRAINT IF EXISTS profiles_persona_check;

ALTER TABLE public.profiles
  ADD CONSTRAINT profiles_persona_check
  CHECK (persona IN ('bfiu_analyst', 'bank_camlco', 'bfiu_director', 'bank_filer'));

ALTER TABLE public.organizations
  DROP CONSTRAINT IF EXISTS organizations_plan_id_check;

ALTER TABLE public.organizations
  ADD CONSTRAINT organizations_plan_id_check
  CHECK (plan_id IN ('starter', 'professional', 'enterprise', 'filing_only'));
