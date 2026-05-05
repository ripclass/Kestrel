-- Migration 018: Pricing tier columns on organizations (V2 phase 6.2)
-- Applied: 2026-05-05
--
-- Three plans are defined in code (engine/app/services/billing.py):
--   * starter       - Tk 60 lakh/year, 5 seats, core features only
--   * professional  - Tk 1.5 crore/year, 15 seats, +cross_bank+realtime+sanctions+kyc
--   * enterprise    - Tk 4 crore/year, 50 seats, everything + on-prem flag
--
-- For v1 plan_id is set manually by superadmins (Stripe integration is a
-- post-pilot concern). The plan_overrides jsonb gives BFIU procurement the
-- ability to grant feature bumps to specific banks without changing tiers
-- (e.g. {"realtime_scoring": true} on a starter plan).

ALTER TABLE organizations
  ADD COLUMN plan_id text NOT NULL DEFAULT 'starter'
    CHECK (plan_id IN ('starter','professional','enterprise')),
  ADD COLUMN plan_set_by uuid REFERENCES auth.users(id),
  ADD COLUMN plan_set_at timestamptz,
  ADD COLUMN plan_overrides jsonb NOT NULL DEFAULT '{}'::jsonb;

CREATE INDEX idx_organizations_plan_id ON organizations (plan_id);

-- Existing tenants default to 'starter'. The single regulator org should
-- run as 'enterprise' since it's the platform operator. Set explicitly
-- so future migrations can assume regulator orgs have the full feature set.
UPDATE organizations
   SET plan_id = 'enterprise',
       plan_set_at = now()
 WHERE org_type = 'regulator';
