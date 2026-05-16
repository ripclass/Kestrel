-- Migration 027: trade_transactions table (2026-05-16)
--
-- Phase B foundation. Captures the per-trade-deal data that BFIU TBML
-- Guidelines 2019 expects every bank to record on each international trade
-- transaction:
--
--   * LC structure  (issuing / advising / confirming bank, LC type,
--                    transferable / standby / red-clause flags)
--   * LCAF reference + declared HS code + declared description
--   * IRC / ERC (importer/exporter registration certs)
--   * Counterparty banks across jurisdictions
--   * Goods detail  (HS code, qty, unit, unit_price, invoice_value,
--                    declared_value, currency)
--   * Country pair  (origin, destination, transshipment ports)
--   * Bill of Lading (B/L number, vessel, container numbers)
--   * Notify party + consignee
--   * Customs Bill of Entry (BE) number + date
--   * Settlement   (payment mode: LC / BTB / open_account / cash_in_advance /
--                    DA / DP / other; payment_to_account; settlement_amount;
--                    settlement_currency)
--   * Linked STR / Case when the transaction is escalated
--
-- The detection rules in the next PR (over_invoicing, under_invoicing,
-- multiple_invoicing, phantom_shipment, transshipment_routing, …) all read
-- against this schema. The realtime scorer also wires into it.

CREATE TABLE trade_transactions (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  org_id uuid NOT NULL REFERENCES organizations(id),

  -- Stable per-org reference. Auto-generated TBT-YYMM-##### like the other
  -- ledgers; see gen_trade_ref() trigger below.
  trade_ref text NOT NULL,

  -- Trade-side: import or export from the org's perspective.
  trade_side text NOT NULL
    CHECK (trade_side IN ('import','export','royalty')),

  -- Payment / settlement mode — drives the risk weighting in the scorer.
  payment_mode text NOT NULL
    CHECK (payment_mode IN (
      'lc_sight','lc_usance','lc_btb','lc_transferable','lc_standby','lc_red_clause',
      'open_account','cash_in_advance','documentary_collection_da','documentary_collection_dp',
      'royalty_fee','other'
    )),

  -- LC structure (only populated when payment_mode is an LC variant)
  lc_reference text NULL,
  lc_issuing_bank text NULL,
  lc_advising_bank text NULL,
  lc_confirming_bank text NULL,
  lc_issue_date date NULL,
  lc_expiry_date date NULL,
  lcaf_reference text NULL,

  -- Importer / Exporter registration cert
  irc_or_erc text NULL,

  -- Subject (the customer on the org's side of the deal)
  subject_name text NOT NULL,
  subject_account text NOT NULL,
  subject_bank text NULL,           -- own bank's branch / dept
  subject_country text NOT NULL DEFAULT 'BD',

  -- Counterparty (the foreign side)
  counterparty_name text NOT NULL,
  counterparty_country text NOT NULL,
  counterparty_bank text NULL,
  counterparty_account text NULL,

  -- Notify party + consignee (often the actual smurfs in TBML)
  notify_party text NULL,
  consignee text NULL,

  -- Goods
  hs_code text NULL,
  goods_description text NULL,
  quantity numeric(18, 4) NULL,
  unit text NULL,                   -- pcs, kg, mt, ltr, etc.
  unit_price numeric(18, 4) NULL,   -- per unit, in invoice currency

  -- Values (the four that the over/under-invoicing rule compares)
  invoice_value numeric(18, 2) NOT NULL,            -- as on commercial invoice
  declared_value numeric(18, 2) NULL,               -- as on LCAF / BE
  market_reference_value numeric(18, 2) NULL,       -- benchmark for the HS code (optional fill)
  settlement_amount numeric(18, 2) NULL,            -- amount actually paid
  currency text NOT NULL DEFAULT 'USD',
  bdt_equivalent numeric(18, 2) NULL,               -- snapshot conversion at booking

  -- Shipment / logistics
  bl_number text NULL,
  vessel text NULL,
  container_numbers text[] NOT NULL DEFAULT '{}'::text[],
  port_of_loading text NULL,
  port_of_discharge text NULL,
  transshipment_ports text[] NOT NULL DEFAULT '{}'::text[],

  -- Customs
  be_number text NULL,
  be_date date NULL,

  -- Insurance leg
  insurance_value numeric(18, 2) NULL,

  -- State + lifecycle
  status text NOT NULL DEFAULT 'open'
    CHECK (status IN ('open','in_progress','settled','overdue','cancelled','flagged')),
  shipment_date date NULL,
  settlement_date date NULL,

  -- Discrepancies surfaced during processing — free-text array, useful for
  -- the rule "documents have been re-used" / "essential docs missing".
  discrepancies text[] NOT NULL DEFAULT '{}'::text[],

  -- Optional links into the rest of the platform.
  linked_str_id uuid NULL REFERENCES str_reports(id) ON DELETE SET NULL,
  linked_case_id uuid NULL REFERENCES cases(id) ON DELETE SET NULL,

  -- Free-form metadata for fields not yet promoted to columns.
  metadata jsonb NOT NULL DEFAULT '{}'::jsonb,

  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

-- Lookups
CREATE INDEX idx_trade_org ON trade_transactions(org_id);
CREATE INDEX idx_trade_ref ON trade_transactions(trade_ref);
CREATE INDEX idx_trade_subject_account ON trade_transactions(subject_account);
CREATE INDEX idx_trade_hs_code ON trade_transactions(hs_code) WHERE hs_code IS NOT NULL;
CREATE INDEX idx_trade_counterparty_country ON trade_transactions(counterparty_country);
CREATE INDEX idx_trade_status ON trade_transactions(status);
CREATE INDEX idx_trade_shipment_date ON trade_transactions(shipment_date DESC NULLS LAST);

-- Multiple-invoicing rule lookup path: same B/L number across orgs.
CREATE INDEX idx_trade_bl_number ON trade_transactions(bl_number) WHERE bl_number IS NOT NULL;
-- LC reference too — same LC across multiple banks is a cross-bank TBML signal.
CREATE INDEX idx_trade_lc_reference ON trade_transactions(lc_reference) WHERE lc_reference IS NOT NULL;

-- Per-org RLS — bank sees only own trade transactions; regulator sees all.
ALTER TABLE trade_transactions ENABLE ROW LEVEL SECURITY;
CREATE POLICY trade_org ON trade_transactions FOR ALL
  USING (org_id = auth_org_id() OR is_regulator());

-- Per-row updated_at trigger using the existing helper.
CREATE TRIGGER trade_transactions_updated BEFORE UPDATE ON trade_transactions
  FOR EACH ROW EXECUTE FUNCTION update_timestamp();

-- Reference generator: TBT-YYMM-#####
CREATE SEQUENCE IF NOT EXISTS trade_ref_seq START 1;

CREATE OR REPLACE FUNCTION public.gen_trade_ref() RETURNS trigger
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = ''
AS $$
BEGIN
  IF NEW.trade_ref IS NULL OR NEW.trade_ref = '' THEN
    NEW.trade_ref := 'TBT-'
      || to_char(now(), 'YYMM') || '-'
      || lpad(nextval('public.trade_ref_seq')::text, 5, '0');
  END IF;
  RETURN NEW;
END;
$$;

CREATE TRIGGER trade_ref_trigger
  BEFORE INSERT ON trade_transactions
  FOR EACH ROW EXECUTE FUNCTION gen_trade_ref();
