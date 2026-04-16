-- Migration 003: Add report_type to str_reports + cash_transaction_reports table
-- Applied: 2026-04-16

-- 1. Add report_type column to str_reports
ALTER TABLE str_reports ADD COLUMN report_type text NOT NULL DEFAULT 'str'
  CHECK (report_type IN ('str','sar','ctr'));

-- 2. Update trigger to use report_type as reference prefix
CREATE OR REPLACE FUNCTION gen_str_ref() RETURNS trigger AS $$
BEGIN
  IF NEW.report_ref IS NULL OR NEW.report_ref = '' THEN
    NEW.report_ref := upper(coalesce(NEW.report_type, 'str')) || '-'
      || to_char(now(), 'YYMM') || '-'
      || lpad(nextval('str_ref_seq')::text, 6, '0');
  END IF;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- 3. Cash Transaction Reports table (lightweight, bulk-oriented)
CREATE TABLE cash_transaction_reports (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  org_id uuid NOT NULL REFERENCES organizations(id),
  account_number text NOT NULL,
  account_name text,
  transaction_date date NOT NULL,
  amount numeric(18,2) NOT NULL,
  currency text NOT NULL DEFAULT 'BDT',
  transaction_type text CHECK (transaction_type IN ('deposit','withdrawal','transfer')),
  branch_code text,
  reported_at timestamptz NOT NULL DEFAULT now(),
  created_at timestamptz NOT NULL DEFAULT now(),
  metadata jsonb NOT NULL DEFAULT '{}'::jsonb
);

CREATE INDEX idx_ctr_org ON cash_transaction_reports(org_id);
CREATE INDEX idx_ctr_account ON cash_transaction_reports(account_number);
CREATE INDEX idx_ctr_date ON cash_transaction_reports(transaction_date DESC);

ALTER TABLE cash_transaction_reports ENABLE ROW LEVEL SECURITY;
CREATE POLICY ctr_org ON cash_transaction_reports FOR ALL
  USING (org_id = auth_org_id() OR is_regulator());
