-- Migration 005: Expand report_type coverage to match goAML's report menu
-- Applied: 2026-04-17
--
-- Adds 8 new report_type variants (tbml, complaint, ier, internal,
-- adverse_media_str, adverse_media_sar, escalated, additional_info),
-- plus type-specific columns for IER, TBML, adverse-media provenance,
-- and the supplements link for Additional Information Files.

-- 1. Replace the CHECK constraint with the expanded enum.
ALTER TABLE str_reports DROP CONSTRAINT IF EXISTS str_reports_report_type_check;
ALTER TABLE str_reports ADD CONSTRAINT str_reports_report_type_check
  CHECK (report_type IN (
    'str', 'sar', 'ctr',
    'tbml',
    'complaint',
    'ier',
    'internal',
    'adverse_media_str',
    'adverse_media_sar',
    'escalated',
    'additional_info'
  ));

-- 2. Additional Information File — link to the parent report it supplements.
ALTER TABLE str_reports ADD COLUMN supplements_report_id uuid REFERENCES str_reports(id);

-- 3. Adverse media provenance.
ALTER TABLE str_reports ADD COLUMN media_source text;
ALTER TABLE str_reports ADD COLUMN media_url text;
ALTER TABLE str_reports ADD COLUMN media_published_at date;

-- 4. Information Exchange Request (IER) fields — Egmont Group cooperation.
ALTER TABLE str_reports ADD COLUMN ier_direction text
  CHECK (ier_direction IS NULL OR ier_direction IN ('inbound','outbound'));
ALTER TABLE str_reports ADD COLUMN ier_counterparty_fiu text;
ALTER TABLE str_reports ADD COLUMN ier_counterparty_country text;
ALTER TABLE str_reports ADD COLUMN ier_egmont_ref text;
ALTER TABLE str_reports ADD COLUMN ier_request_narrative text;
ALTER TABLE str_reports ADD COLUMN ier_response_narrative text;
ALTER TABLE str_reports ADD COLUMN ier_deadline date;

-- 5. Trade-Based Money Laundering (TBML) fields.
ALTER TABLE str_reports ADD COLUMN tbml_invoice_value numeric(18,2);
ALTER TABLE str_reports ADD COLUMN tbml_declared_value numeric(18,2);
ALTER TABLE str_reports ADD COLUMN tbml_lc_reference text;
ALTER TABLE str_reports ADD COLUMN tbml_hs_code text;
ALTER TABLE str_reports ADD COLUMN tbml_commodity text;
ALTER TABLE str_reports ADD COLUMN tbml_counterparty_country text;

-- 6. Ref prefix mapping. The existing gen_str_ref() trigger uses
--    upper(report_type) directly, which produces unwieldy prefixes like
--    ADDITIONAL_INFO-2604-000001. Replace with short codes matching
--    goAML / BFIU conventions so refs stay scannable.
CREATE OR REPLACE FUNCTION gen_str_ref() RETURNS trigger AS $$
DECLARE
  prefix text;
BEGIN
  IF NEW.report_ref IS NULL OR NEW.report_ref = '' THEN
    prefix := CASE coalesce(NEW.report_type, 'str')
      WHEN 'str'               THEN 'STR'
      WHEN 'sar'               THEN 'SAR'
      WHEN 'ctr'               THEN 'CTR'
      WHEN 'tbml'              THEN 'TBML'
      WHEN 'complaint'         THEN 'COMP'
      WHEN 'ier'               THEN 'IER'
      WHEN 'internal'          THEN 'INT'
      WHEN 'adverse_media_str' THEN 'AMSTR'
      WHEN 'adverse_media_sar' THEN 'AMSAR'
      WHEN 'escalated'         THEN 'ESC'
      WHEN 'additional_info'   THEN 'ADDL'
      ELSE upper(coalesce(NEW.report_type, 'str'))
    END;
    NEW.report_ref := prefix || '-'
      || to_char(now(), 'YYMM') || '-'
      || lpad(nextval('str_ref_seq')::text, 6, '0');
  END IF;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- 7. Indexes for the new filter + lookup paths.
CREATE INDEX IF NOT EXISTS idx_str_report_type ON str_reports(report_type);
CREATE INDEX IF NOT EXISTS idx_str_supplements ON str_reports(supplements_report_id)
  WHERE supplements_report_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_str_ier_direction ON str_reports(ier_direction)
  WHERE ier_direction IS NOT NULL;
