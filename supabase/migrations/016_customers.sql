-- Migration 016: KYC / CDD customers (V2 phase 5.1)
-- Applied: 2026-05-05
--
-- Greenfield. The customer onboarding flow at POST /customers calls the
-- screening service from V2 phase 4 inline (against the customer name +
-- DOB + nationality + NID + passport, plus each beneficial owner). The
-- composed customer-level risk_score drives the kyc_status (pending /
-- approved / review / declined). RLS scopes rows per tenant.

CREATE TABLE customers (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  org_id uuid NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
  customer_external_id text NOT NULL,
  customer_type text NOT NULL CHECK (customer_type IN ('individual','business')),
  full_name text NOT NULL,
  nid text,
  passport text,
  date_of_birth date,
  nationality text,
  phone text,
  email text,
  address jsonb NOT NULL DEFAULT '{}'::jsonb,
  metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
  beneficial_owners jsonb NOT NULL DEFAULT '[]'::jsonb,
  risk_score integer,
  risk_level text CHECK (risk_level IS NULL OR risk_level IN ('low','medium','high','declined')),
  kyc_status text NOT NULL DEFAULT 'pending' CHECK (kyc_status IN ('pending','approved','review','declined')),
  screening_results jsonb NOT NULL DEFAULT '{}'::jsonb,
  onboarded_at timestamptz NOT NULL DEFAULT now(),
  reviewed_at timestamptz,
  reviewed_by uuid REFERENCES auth.users(id),
  last_rescreened_at timestamptz,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE(org_id, customer_external_id)
);

CREATE INDEX idx_customers_org_status ON customers (org_id, kyc_status);
CREATE INDEX idx_customers_org_risk ON customers (org_id, risk_level);
CREATE INDEX idx_customers_onboarded ON customers (org_id, onboarded_at DESC);
-- Trigram on full_name so the screening service can also resolve customers
-- when a transaction comes in with the customer's name in metadata.
CREATE INDEX idx_customers_name_trgm ON customers USING gin (full_name gin_trgm_ops);
-- For the periodic re-screening Beat task — pull approved/review customers
-- where the last rescreen is stale.
CREATE INDEX idx_customers_rescreen_due
  ON customers (org_id, last_rescreened_at NULLS FIRST)
  WHERE kyc_status IN ('approved', 'review');

ALTER TABLE customers ENABLE ROW LEVEL SECURITY;

CREATE POLICY customers_select ON customers
  FOR SELECT
  USING (org_id = public.auth_org_id() OR public.is_regulator());

CREATE POLICY customers_insert ON customers
  FOR INSERT
  WITH CHECK (org_id = public.auth_org_id());

CREATE POLICY customers_update ON customers
  FOR UPDATE
  USING (org_id = public.auth_org_id())
  WITH CHECK (org_id = public.auth_org_id());

-- updated_at maintenance via the existing trigger helper from migration 001.
CREATE TRIGGER trg_customers_updated_at
  BEFORE UPDATE ON customers
  FOR EACH ROW
  EXECUTE FUNCTION public.update_timestamp();

-- Relax alerts.source_type to allow the Beat-driven KYC re-screening
-- escalations from V2 phase 5.4. Same drop-and-readd pattern as
-- migration 011 for `match_definition`.
ALTER TABLE alerts DROP CONSTRAINT IF EXISTS alerts_source_type_check;

ALTER TABLE alerts
  ADD CONSTRAINT alerts_source_type_check
  CHECK (source_type IN (
    'scan',
    'cross_bank',
    'str_enrichment',
    'manual',
    'match_definition',
    'kyc_rescreen'
  ));
