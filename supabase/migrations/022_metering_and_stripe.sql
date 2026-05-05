-- Migration 022: Stripe identifiers + monthly transaction metering (V3 phase 7)
-- Applied: 2026-05-05
--
-- V3 P7.1 wires the Stripe billing relationship onto each tenant; V3 P7.2
-- adds the metered-write counter that gates POST /transactions/score on
-- the per-plan monthly cap (starter: 500k; professional + enterprise: no
-- cap). The two are bundled because they share the same audit-period
-- shape — counter rolls at first-of-month (Asia/Dhaka) and the Stripe
-- subscription period maps onto the same calendar.

ALTER TABLE organizations
  ADD COLUMN IF NOT EXISTS stripe_customer_id text UNIQUE,
  ADD COLUMN IF NOT EXISTS stripe_subscription_id text UNIQUE,
  ADD COLUMN IF NOT EXISTS stripe_subscription_status text
    CHECK (stripe_subscription_status IS NULL OR stripe_subscription_status IN
      ('trialing','active','past_due','canceled','unpaid','incomplete','incomplete_expired','paused')),
  ADD COLUMN IF NOT EXISTS stripe_price_id text,
  ADD COLUMN IF NOT EXISTS plan_grace_until timestamptz;

CREATE INDEX IF NOT EXISTS idx_organizations_stripe_customer
  ON organizations (stripe_customer_id);
CREATE INDEX IF NOT EXISTS idx_organizations_stripe_subscription
  ON organizations (stripe_subscription_id);


-- Monthly metered-write counter. PK on (org_id, period_start) so an
-- org has at most one row per month. period_start is always the first
-- of a month at 00:00 UTC; the application layer rolls at first-of-month
-- in Asia/Dhaka by computing period_start from the Dhaka calendar then
-- storing it as UTC midnight (kept simple — one row per Asia/Dhaka month).
CREATE TABLE IF NOT EXISTS metered_writes (
  org_id uuid NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
  period_start date NOT NULL,
  transaction_count integer NOT NULL DEFAULT 0,
  last_incremented_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (org_id, period_start)
);

CREATE INDEX IF NOT EXISTS idx_metered_writes_period
  ON metered_writes (period_start DESC);

ALTER TABLE metered_writes ENABLE ROW LEVEL SECURITY;

-- Read: own org or regulator. Insert/Update: own org only (the engine
-- writes via the BYPASSRLS postgres role; this policy gates direct
-- PostgREST access).
DROP POLICY IF EXISTS metered_writes_select ON metered_writes;
CREATE POLICY metered_writes_select ON metered_writes
  FOR SELECT
  USING (org_id = public.auth_org_id() OR public.is_regulator());

DROP POLICY IF EXISTS metered_writes_insert ON metered_writes;
CREATE POLICY metered_writes_insert ON metered_writes
  FOR INSERT
  WITH CHECK (org_id = public.auth_org_id());

DROP POLICY IF EXISTS metered_writes_update ON metered_writes;
CREATE POLICY metered_writes_update ON metered_writes
  FOR UPDATE
  USING (org_id = public.auth_org_id())
  WITH CHECK (org_id = public.auth_org_id());
