-- Migration 006: Dissemination tracking (goAML Task 7)
-- Applied: 2026-04-17
--
-- BFIU disseminates intelligence to law enforcement, regulators, and
-- foreign FIUs. This is an audit-critical workflow — every hand-off is
-- recorded with recipient, classification, subject summary, and the
-- underlying reports/entities/cases that travelled with the packet.

CREATE TABLE disseminations (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  org_id uuid NOT NULL REFERENCES organizations(id),
  dissemination_ref text NOT NULL,
  recipient_agency text NOT NULL,
  recipient_type text NOT NULL
    CHECK (recipient_type IN ('law_enforcement','regulator','foreign_fiu','prosecutor','other')),
  subject_summary text NOT NULL,
  linked_report_ids uuid[] NOT NULL DEFAULT '{}',
  linked_entity_ids uuid[] NOT NULL DEFAULT '{}',
  linked_case_ids uuid[] NOT NULL DEFAULT '{}',
  disseminated_by uuid REFERENCES auth.users(id),
  disseminated_at timestamptz NOT NULL DEFAULT now(),
  classification text NOT NULL DEFAULT 'confidential'
    CHECK (classification IN ('public','internal','confidential','restricted','secret')),
  metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX idx_dissem_org ON disseminations(org_id);
CREATE INDEX idx_dissem_recipient ON disseminations(recipient_agency);
CREATE INDEX idx_dissem_date ON disseminations(disseminated_at DESC);
CREATE INDEX idx_dissem_type ON disseminations(recipient_type);

ALTER TABLE disseminations ENABLE ROW LEVEL SECURITY;
CREATE POLICY dissem_org ON disseminations FOR ALL
  USING (org_id = auth_org_id() OR is_regulator());

-- Ref generation: DISS-YYMM-#####
CREATE SEQUENCE IF NOT EXISTS dissem_ref_seq START 1;

CREATE OR REPLACE FUNCTION gen_dissem_ref() RETURNS trigger AS $$
BEGIN
  IF NEW.dissemination_ref IS NULL OR NEW.dissemination_ref = '' THEN
    NEW.dissemination_ref := 'DISS-'
      || to_char(now(), 'YYMM') || '-'
      || lpad(nextval('dissem_ref_seq')::text, 5, '0');
  END IF;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER dissem_ref_trigger
  BEFORE INSERT ON disseminations
  FOR EACH ROW EXECUTE FUNCTION gen_dissem_ref();
