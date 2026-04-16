-- Migration 004: DB-backed typologies library
-- Applied: 2026-04-16

CREATE TABLE typologies (
  id text PRIMARY KEY,
  title text NOT NULL,
  category text NOT NULL CHECK (category IN ('fraud','money_laundering','terrorist_financing','tbml','cyber_crime','other')),
  channels text[] NOT NULL DEFAULT '{}',
  indicators text[] NOT NULL DEFAULT '{}',
  narrative text NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

ALTER TABLE typologies ENABLE ROW LEVEL SECURITY;

-- Read-only for every authenticated user (typologies are shared intelligence)
CREATE POLICY typologies_read ON typologies FOR SELECT USING (auth.uid() IS NOT NULL);

-- Write only by regulators
CREATE POLICY typologies_write ON typologies FOR INSERT WITH CHECK (is_regulator());
CREATE POLICY typologies_update ON typologies FOR UPDATE USING (is_regulator()) WITH CHECK (is_regulator());
CREATE POLICY typologies_delete ON typologies FOR DELETE USING (is_regulator());

CREATE TRIGGER typologies_updated BEFORE UPDATE ON typologies
  FOR EACH ROW EXECUTE FUNCTION update_timestamp();

-- Seed data: five representative Bangladesh financial crime typologies.
INSERT INTO typologies (id, title, category, channels, indicators, narrative) VALUES
  (
    'typology-merchant',
    'Merchant front with rapid MFS exit',
    'fraud',
    ARRAY['RTGS','MFS'],
    ARRAY[
      'Rapid outbound after inbound settlement',
      'Shared phone across multiple beneficiary wallets',
      'Narrative mismatch with business profile'
    ],
    'Commercial accounts receive high-value settlements and immediately disperse funds into consumer wallets and layered beneficiaries, breaking the link between the predicate offence and the ultimate recipients.'
  ),
  (
    'typology-layering',
    'Cross-bank layering ring',
    'money_laundering',
    ARRAY['NPSB','BEFTN','RTGS'],
    ARRAY[
      'Fan-out burst across peer banks',
      'Repeated peer-bank overlap in a 24h window',
      'Two-hop proximity to a previously flagged entity'
    ],
    'Funds are routed across several banks in rapid succession — typically via NPSB and BEFTN — to break attribution, avoid single-bank threshold monitoring, and frustrate manual review.'
  ),
  (
    'typology-hundi',
    'Hundi-style cross-border settlement',
    'money_laundering',
    ARRAY['Cash','MFS','bKash'],
    ARRAY[
      'Structured deposits under reporting threshold',
      'Matching outbound remittance requests',
      'Geographic clustering near border districts'
    ],
    'Informal value transfer where one leg of a cross-border settlement lands in Bangladesh as structured cash or MFS deposits while the counter-party is paid abroad, bypassing regulated remittance channels.'
  ),
  (
    'typology-tbml-underinvoicing',
    'Trade-based under-invoicing',
    'tbml',
    ARRAY['LC','Documentary Credit','RTGS'],
    ARRAY[
      'Import valuation significantly below market price',
      'Repeated supplier relationships with thin documentation',
      'High-frequency amendments to LC terms after issuance'
    ],
    'Importers understate invoice values to move capital out of Bangladesh under the guise of legitimate trade, paying the true value abroad through hawala or shell corporate layers.'
  ),
  (
    'typology-cyber-mule',
    'Cyber fraud mule network',
    'cyber_crime',
    ARRAY['MFS','NPSB','CARDS'],
    ARRAY[
      'Recent account with large first-time credit',
      'Immediate cash-out within minutes',
      'Device fingerprint shared across multiple accounts',
      'Reported as social engineering victim by beneficiary'
    ],
    'Victims of phishing, impersonation, or romance scams are instructed to move funds through a chain of mule accounts, each rapidly cashed out and often tied to shared device or SIM reuse.'
  );
