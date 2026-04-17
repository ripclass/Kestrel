-- Migration 009: Reference tables / Lookup Master (goAML Task 10)
-- Applied: 2026-04-17
--
-- Centralized reference data: bank codes, branch codes, country codes,
-- currency codes, channel codes, category codes. Populated with the
-- most-used values so BFIU operators see meaningful dropdowns on day 1;
-- admins can extend any table via /admin/reference-tables.
--
-- Anyone authenticated reads (reference data is not sensitive); only
-- regulator users can mutate — per goAML's model where lookup masters
-- are owned by the FIU.

CREATE TABLE reference_tables (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  table_name text NOT NULL
    CHECK (table_name IN ('banks','branches','countries','channels','categories','currencies','agencies')),
  code text NOT NULL,
  value text NOT NULL,
  description text,
  parent_code text,
  metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
  is_active boolean NOT NULL DEFAULT true,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE(table_name, code)
);

CREATE INDEX idx_reference_table_name ON reference_tables(table_name) WHERE is_active = true;
CREATE INDEX idx_reference_parent
  ON reference_tables(table_name, parent_code)
  WHERE parent_code IS NOT NULL;

ALTER TABLE reference_tables ENABLE ROW LEVEL SECURITY;

CREATE POLICY reference_read ON reference_tables FOR SELECT
  USING (auth.uid() IS NOT NULL);

CREATE POLICY reference_insert ON reference_tables FOR INSERT
  WITH CHECK (is_regulator());

CREATE POLICY reference_update ON reference_tables FOR UPDATE
  USING (is_regulator())
  WITH CHECK (is_regulator());

CREATE POLICY reference_delete ON reference_tables FOR DELETE
  USING (is_regulator());

-- ============================================================
-- Seed: Channels (payment + reporting channels BFIU tracks)
-- ============================================================

INSERT INTO reference_tables (table_name, code, value, description) VALUES
  ('channels', 'RTGS',      'Real-Time Gross Settlement',   'High-value same-day interbank settlement.'),
  ('channels', 'BEFTN',     'Bangladesh EFT Network',       'Batched retail ACH-style transfers.'),
  ('channels', 'NPSB',      'National Payment Switch Bangladesh', 'Card and account-to-account routing.'),
  ('channels', 'MFS',       'Mobile Financial Services',    'bKash, Nagad, Rocket, and peers.'),
  ('channels', 'CASH',      'Cash deposit / withdrawal',    'Over-the-counter cash movement.'),
  ('channels', 'CHEQUE',    'Cheque / BACH',                'Paper cheque and BACH clearing.'),
  ('channels', 'CARD',      'Card rails',                   'Domestic and international card networks.'),
  ('channels', 'WIRE',      'Correspondent wire',           'SWIFT-routed cross-border wire.'),
  ('channels', 'LC',        'Letter of credit',             'Trade finance LC flows.'),
  ('channels', 'DRAFT',     'Bank draft',                   'Payee-specific drafts issued by bank.')
ON CONFLICT (table_name, code) DO NOTHING;

-- ============================================================
-- Seed: Categories (aligned with str_reports.category enum)
-- ============================================================

INSERT INTO reference_tables (table_name, code, value, description) VALUES
  ('categories', 'fraud',               'Fraud',                        'General fraud / deception.'),
  ('categories', 'money_laundering',    'Money laundering',             'Placement, layering, integration.'),
  ('categories', 'terrorist_financing', 'Terrorist financing',          'Funds linked to terrorism financing.'),
  ('categories', 'tbml',                'Trade-based money laundering', 'Over/under invoicing, LC abuse.'),
  ('categories', 'cyber_crime',         'Cyber crime',                  'Online fraud, account takeovers, crypto scams.'),
  ('categories', 'corruption',          'Corruption',                   'Graft, bribes, PEP-linked flows.'),
  ('categories', 'sanctions',           'Sanctions evasion',            'OFAC/UN/EU sanctions circumvention.'),
  ('categories', 'tax_evasion',         'Tax evasion',                  'Capital flight, undeclared accounts.'),
  ('categories', 'drug_trafficking',    'Drug trafficking',             'Narcotics-linked proceeds.'),
  ('categories', 'human_trafficking',   'Human trafficking',            'Trafficking and smuggling proceeds.'),
  ('categories', 'wildlife_crime',      'Wildlife crime',               'Wildlife trafficking proceeds.'),
  ('categories', 'other',               'Other',                        'Uncategorized suspicious activity.')
ON CONFLICT (table_name, code) DO NOTHING;

-- ============================================================
-- Seed: Banks (Bangladesh scheduled banks — representative set)
-- ============================================================

INSERT INTO reference_tables (table_name, code, value, description, metadata) VALUES
  -- State-owned commercial banks
  ('banks', 'SONA', 'Sonali Bank PLC',           'State-owned commercial bank.', '{"category":"state_owned_commercial"}'::jsonb),
  ('banks', 'JANA', 'Janata Bank PLC',           'State-owned commercial bank.', '{"category":"state_owned_commercial"}'::jsonb),
  ('banks', 'AGRA', 'Agrani Bank PLC',           'State-owned commercial bank.', '{"category":"state_owned_commercial"}'::jsonb),
  ('banks', 'RUPA', 'Rupali Bank PLC',           'State-owned commercial bank.', '{"category":"state_owned_commercial"}'::jsonb),
  ('banks', 'BASI', 'BASIC Bank PLC',            'State-owned commercial bank.', '{"category":"state_owned_commercial"}'::jsonb),
  ('banks', 'BDBL', 'Bangladesh Development Bank PLC', 'State-owned development bank.', '{"category":"state_owned_development"}'::jsonb),
  -- Specialized
  ('banks', 'BKBL', 'Bangladesh Krishi Bank',    'Agricultural specialized bank.', '{"category":"specialized"}'::jsonb),
  ('banks', 'RAKU', 'Rajshahi Krishi Unnayan Bank','Regional agricultural bank.',  '{"category":"specialized"}'::jsonb),
  ('banks', 'PKBL', 'Probashi Kallyan Bank',     'Migrant workers welfare bank.',  '{"category":"specialized"}'::jsonb),
  -- Private commercial banks
  ('banks', 'ABBL', 'AB Bank PLC',               'Private commercial bank.',       '{"category":"private_commercial"}'::jsonb),
  ('banks', 'AAIB', 'Al-Arafah Islami Bank PLC', 'Private Islamic bank.',          '{"category":"private_islamic"}'::jsonb),
  ('banks', 'BASB', 'Bank Asia PLC',             'Private commercial bank.',       '{"category":"private_commercial"}'::jsonb),
  ('banks', 'BRAC', 'BRAC Bank PLC',             'Private commercial bank.',       '{"category":"private_commercial"}'::jsonb),
  ('banks', 'CITY', 'City Bank PLC',             'Private commercial bank.',       '{"category":"private_commercial"}'::jsonb),
  ('banks', 'COMB', 'Commercial Bank of Ceylon', 'Foreign commercial bank.',       '{"category":"foreign_commercial"}'::jsonb),
  ('banks', 'DBBL', 'Dutch-Bangla Bank PLC',     'Private commercial bank.',       '{"category":"private_commercial"}'::jsonb),
  ('banks', 'DHAK', 'Dhaka Bank PLC',            'Private commercial bank.',       '{"category":"private_commercial"}'::jsonb),
  ('banks', 'EBLB', 'Eastern Bank PLC',          'Private commercial bank.',       '{"category":"private_commercial"}'::jsonb),
  ('banks', 'EXIM', 'EXIM Bank PLC',             'Private Islamic bank.',          '{"category":"private_islamic"}'::jsonb),
  ('banks', 'FSIB', 'First Security Islami Bank PLC', 'Private Islamic bank.',    '{"category":"private_islamic"}'::jsonb),
  ('banks', 'GIBL', 'Global Islami Bank PLC',    'Private Islamic bank.',          '{"category":"private_islamic"}'::jsonb),
  ('banks', 'HSBC', 'HSBC Bangladesh',           'Foreign commercial bank.',       '{"category":"foreign_commercial"}'::jsonb),
  ('banks', 'IBBL', 'Islami Bank Bangladesh PLC','Private Islamic bank.',          '{"category":"private_islamic"}'::jsonb),
  ('banks', 'ICBI', 'ICB Islamic Bank PLC',      'Private Islamic bank.',          '{"category":"private_islamic"}'::jsonb),
  ('banks', 'IFIC', 'IFIC Bank PLC',             'Private commercial bank.',       '{"category":"private_commercial"}'::jsonb),
  ('banks', 'JAMU', 'Jamuna Bank PLC',           'Private commercial bank.',       '{"category":"private_commercial"}'::jsonb),
  ('banks', 'MERC', 'Mercantile Bank PLC',       'Private commercial bank.',       '{"category":"private_commercial"}'::jsonb),
  ('banks', 'MEGH', 'Meghna Bank PLC',           'Private commercial bank.',       '{"category":"private_commercial"}'::jsonb),
  ('banks', 'MIDL', 'Midland Bank PLC',          'Private commercial bank.',       '{"category":"private_commercial"}'::jsonb),
  ('banks', 'MODH', 'Modhumoti Bank PLC',        'Private commercial bank.',       '{"category":"private_commercial"}'::jsonb),
  ('banks', 'MTBL', 'Mutual Trust Bank PLC',     'Private commercial bank.',       '{"category":"private_commercial"}'::jsonb),
  ('banks', 'NBLB', 'National Bank PLC',         'Private commercial bank.',       '{"category":"private_commercial"}'::jsonb),
  ('banks', 'NCCB', 'NCC Bank PLC',              'Private commercial bank.',       '{"category":"private_commercial"}'::jsonb),
  ('banks', 'NRBB', 'NRB Bank PLC',              'Private commercial bank.',       '{"category":"private_commercial"}'::jsonb),
  ('banks', 'NRBC', 'NRB Commercial Bank PLC',   'Private commercial bank.',       '{"category":"private_commercial"}'::jsonb),
  ('banks', 'ONEB', 'ONE Bank PLC',              'Private commercial bank.',       '{"category":"private_commercial"}'::jsonb),
  ('banks', 'PADM', 'Padma Bank PLC',            'Private commercial bank.',       '{"category":"private_commercial"}'::jsonb),
  ('banks', 'PREM', 'Premier Bank PLC',          'Private commercial bank.',       '{"category":"private_commercial"}'::jsonb),
  ('banks', 'PRIM', 'Prime Bank PLC',            'Private commercial bank.',       '{"category":"private_commercial"}'::jsonb),
  ('banks', 'PUBA', 'Pubali Bank PLC',           'Private commercial bank.',       '{"category":"private_commercial"}'::jsonb),
  ('banks', 'SBAC', 'South Bangla Agriculture and Commerce Bank PLC', 'Private commercial bank.', '{"category":"private_commercial"}'::jsonb),
  ('banks', 'SEBL', 'Southeast Bank PLC',        'Private commercial bank.',       '{"category":"private_commercial"}'::jsonb),
  ('banks', 'SHAH', 'Shahjalal Islami Bank PLC', 'Private Islamic bank.',          '{"category":"private_islamic"}'::jsonb),
  ('banks', 'SIBL', 'Social Islami Bank PLC',    'Private Islamic bank.',          '{"category":"private_islamic"}'::jsonb),
  ('banks', 'STAN', 'Standard Bank PLC',         'Private commercial bank.',       '{"category":"private_commercial"}'::jsonb),
  ('banks', 'SCBL', 'Standard Chartered Bangladesh','Foreign commercial bank.',    '{"category":"foreign_commercial"}'::jsonb),
  ('banks', 'TRUS', 'Trust Bank PLC',            'Private commercial bank.',       '{"category":"private_commercial"}'::jsonb),
  ('banks', 'UCBL', 'United Commercial Bank PLC','Private commercial bank.',       '{"category":"private_commercial"}'::jsonb),
  ('banks', 'UNON', 'Union Bank PLC',            'Private Islamic bank.',          '{"category":"private_islamic"}'::jsonb),
  ('banks', 'UTRA', 'Uttara Bank PLC',           'Private commercial bank.',       '{"category":"private_commercial"}'::jsonb),
  ('banks', 'COML', 'Community Bank Bangladesh PLC', 'Private commercial bank.',   '{"category":"private_commercial"}'::jsonb),
  ('banks', 'SHIM', 'Bengal Commercial Bank PLC','Private commercial bank.',       '{"category":"private_commercial"}'::jsonb),
  -- Foreign banks
  ('banks', 'BALF', 'Bank Al-Falah',             'Foreign commercial bank.',       '{"category":"foreign_commercial"}'::jsonb),
  ('banks', 'CITI', 'Citibank N.A.',             'Foreign commercial bank.',       '{"category":"foreign_commercial"}'::jsonb),
  ('banks', 'HABI', 'Habib Bank Limited',        'Foreign commercial bank.',       '{"category":"foreign_commercial"}'::jsonb),
  ('banks', 'NBPK', 'National Bank of Pakistan', 'Foreign commercial bank.',       '{"category":"foreign_commercial"}'::jsonb),
  ('banks', 'SBIN', 'State Bank of India',       'Foreign commercial bank.',       '{"category":"foreign_commercial"}'::jsonb),
  ('banks', 'WOOR', 'Woori Bank',                'Foreign commercial bank.',       '{"category":"foreign_commercial"}'::jsonb),
  -- MFS providers (not banks but reported under BFIU supervision)
  ('banks', 'BKSH', 'bKash Limited',             'Mobile Financial Service (BRAC Bank subsidiary).', '{"category":"mfs"}'::jsonb),
  ('banks', 'NAGD', 'Nagad Limited',             'MFS (Bangladesh Post Office).',  '{"category":"mfs"}'::jsonb),
  ('banks', 'ROCK', 'Rocket (DBBL Mobile Banking)', 'MFS (Dutch-Bangla Bank).',    '{"category":"mfs"}'::jsonb),
  ('banks', 'UPAY', 'Upay',                      'MFS (UCB subsidiary).',          '{"category":"mfs"}'::jsonb),
  ('banks', 'MCAS', 'MyCash',                    'MFS (Mercantile Bank).',         '{"category":"mfs"}'::jsonb),
  ('banks', 'TCPT', 'T-Cash',                    'MFS (Trust Bank).',              '{"category":"mfs"}'::jsonb)
ON CONFLICT (table_name, code) DO NOTHING;

-- ============================================================
-- Seed: Countries (ISO 3166-1 alpha-2) — focus on BFIU workflows
--   South Asia + ASEAN + Gulf + Egmont Group peers + major remittance
--   corridors. Full ISO list can be added by operators as needed.
-- ============================================================

INSERT INTO reference_tables (table_name, code, value, description) VALUES
  ('countries','BD','Bangladesh',''),
  ('countries','IN','India',''),
  ('countries','PK','Pakistan',''),
  ('countries','NP','Nepal',''),
  ('countries','BT','Bhutan',''),
  ('countries','LK','Sri Lanka',''),
  ('countries','MM','Myanmar',''),
  ('countries','MV','Maldives',''),
  ('countries','AF','Afghanistan',''),
  ('countries','CN','China',''),
  ('countries','HK','Hong Kong SAR',''),
  ('countries','JP','Japan',''),
  ('countries','KR','South Korea',''),
  ('countries','SG','Singapore',''),
  ('countries','MY','Malaysia',''),
  ('countries','ID','Indonesia',''),
  ('countries','TH','Thailand',''),
  ('countries','PH','Philippines',''),
  ('countries','VN','Vietnam',''),
  ('countries','AE','United Arab Emirates',''),
  ('countries','SA','Saudi Arabia',''),
  ('countries','QA','Qatar',''),
  ('countries','KW','Kuwait',''),
  ('countries','OM','Oman',''),
  ('countries','BH','Bahrain',''),
  ('countries','JO','Jordan',''),
  ('countries','IR','Iran','FATF high-risk jurisdiction.'),
  ('countries','IQ','Iraq',''),
  ('countries','YE','Yemen',''),
  ('countries','SY','Syria',''),
  ('countries','TR','Türkiye',''),
  ('countries','US','United States',''),
  ('countries','CA','Canada',''),
  ('countries','GB','United Kingdom',''),
  ('countries','IE','Ireland',''),
  ('countries','DE','Germany',''),
  ('countries','FR','France',''),
  ('countries','IT','Italy',''),
  ('countries','ES','Spain',''),
  ('countries','NL','Netherlands',''),
  ('countries','BE','Belgium',''),
  ('countries','LU','Luxembourg',''),
  ('countries','CH','Switzerland',''),
  ('countries','AT','Austria',''),
  ('countries','SE','Sweden',''),
  ('countries','NO','Norway',''),
  ('countries','DK','Denmark',''),
  ('countries','FI','Finland',''),
  ('countries','PL','Poland',''),
  ('countries','RU','Russia',''),
  ('countries','BY','Belarus',''),
  ('countries','UA','Ukraine',''),
  ('countries','AU','Australia',''),
  ('countries','NZ','New Zealand',''),
  ('countries','ZA','South Africa',''),
  ('countries','NG','Nigeria',''),
  ('countries','KE','Kenya',''),
  ('countries','EG','Egypt',''),
  ('countries','MA','Morocco',''),
  ('countries','BR','Brazil',''),
  ('countries','MX','Mexico',''),
  ('countries','PA','Panama',''),
  ('countries','VG','British Virgin Islands','Listed on FATF monitoring watchlists historically.'),
  ('countries','KY','Cayman Islands','')
ON CONFLICT (table_name, code) DO NOTHING;

-- ============================================================
-- Seed: Currencies (ISO 4217) — BFIU-relevant subset
-- ============================================================

INSERT INTO reference_tables (table_name, code, value, description) VALUES
  ('currencies','BDT','Bangladeshi Taka','Domestic currency.'),
  ('currencies','USD','US Dollar',''),
  ('currencies','EUR','Euro',''),
  ('currencies','GBP','British Pound Sterling',''),
  ('currencies','JPY','Japanese Yen',''),
  ('currencies','CNY','Chinese Yuan Renminbi',''),
  ('currencies','HKD','Hong Kong Dollar',''),
  ('currencies','SGD','Singapore Dollar',''),
  ('currencies','AUD','Australian Dollar',''),
  ('currencies','CAD','Canadian Dollar',''),
  ('currencies','CHF','Swiss Franc',''),
  ('currencies','INR','Indian Rupee',''),
  ('currencies','PKR','Pakistani Rupee',''),
  ('currencies','LKR','Sri Lankan Rupee',''),
  ('currencies','NPR','Nepalese Rupee',''),
  ('currencies','MYR','Malaysian Ringgit',''),
  ('currencies','IDR','Indonesian Rupiah',''),
  ('currencies','THB','Thai Baht',''),
  ('currencies','KRW','South Korean Won',''),
  ('currencies','AED','UAE Dirham',''),
  ('currencies','SAR','Saudi Riyal',''),
  ('currencies','QAR','Qatari Riyal',''),
  ('currencies','KWD','Kuwaiti Dinar',''),
  ('currencies','OMR','Omani Rial',''),
  ('currencies','BHD','Bahraini Dinar',''),
  ('currencies','JOD','Jordanian Dinar',''),
  ('currencies','TRY','Turkish Lira',''),
  ('currencies','RUB','Russian Ruble',''),
  ('currencies','BRL','Brazilian Real',''),
  ('currencies','ZAR','South African Rand','')
ON CONFLICT (table_name, code) DO NOTHING;

-- ============================================================
-- Seed: Recipient agencies (dissemination recipients)
-- ============================================================

INSERT INTO reference_tables (table_name, code, value, description, metadata) VALUES
  ('agencies','POLICE',   'Bangladesh Police',                  'Ministry of Home Affairs.',    '{"recipient_type":"law_enforcement"}'::jsonb),
  ('agencies','CID',      'Criminal Investigation Department',  'Bangladesh Police CID.',       '{"recipient_type":"law_enforcement"}'::jsonb),
  ('agencies','DB',       'Detective Branch',                   'Dhaka Metropolitan Police DB.','{"recipient_type":"law_enforcement"}'::jsonb),
  ('agencies','ACC',      'Anti-Corruption Commission',         'Statutory corruption body.',   '{"recipient_type":"regulator"}'::jsonb),
  ('agencies','NBR',      'National Board of Revenue',          'Tax and customs.',              '{"recipient_type":"regulator"}'::jsonb),
  ('agencies','DGFI',     'Directorate General of Forces Intelligence','Military intelligence.','{"recipient_type":"law_enforcement"}'::jsonb),
  ('agencies','RAB',      'Rapid Action Battalion',             'Elite police unit.',            '{"recipient_type":"law_enforcement"}'::jsonb),
  ('agencies','CTTC',     'Counter Terrorism and Transnational Crime Unit', 'DMP specialized unit.', '{"recipient_type":"law_enforcement"}'::jsonb),
  ('agencies','BB',       'Bangladesh Bank',                    'Central bank.',                 '{"recipient_type":"regulator"}'::jsonb),
  ('agencies','BSEC',     'Bangladesh Securities and Exchange Commission', 'Capital markets regulator.', '{"recipient_type":"regulator"}'::jsonb),
  ('agencies','CRF',      'Court / Referrals',                  'Criminal court referrals.',     '{"recipient_type":"prosecutor"}'::jsonb),
  ('agencies','FINTRAC',  'FINTRAC (Canada)',                   'Canadian FIU — Egmont Group.',  '{"recipient_type":"foreign_fiu"}'::jsonb),
  ('agencies','AUSTRAC',  'AUSTRAC (Australia)',                'Australian FIU.',               '{"recipient_type":"foreign_fiu"}'::jsonb),
  ('agencies','FIU_IND',  'FIU India',                          'Indian FIU.',                   '{"recipient_type":"foreign_fiu"}'::jsonb),
  ('agencies','FMU_PAK',  'Financial Monitoring Unit (Pakistan)','Pakistani FIU.',               '{"recipient_type":"foreign_fiu"}'::jsonb),
  ('agencies','FINCEN',   'FinCEN (United States)',             'US FIU.',                       '{"recipient_type":"foreign_fiu"}'::jsonb),
  ('agencies','STRO',     'STRO (Singapore)',                   'Singapore FIU.',                '{"recipient_type":"foreign_fiu"}'::jsonb)
ON CONFLICT (table_name, code) DO NOTHING;
