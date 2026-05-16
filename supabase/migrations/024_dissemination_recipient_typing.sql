-- Migration 024: Typed recipient authority + MLPA enabling clause + Circular-22 exchange flag on disseminations (2026-05-16)
--
-- BFIU dissemination is not a single "law enforcement" hand-off. Under MLPA 2012
-- §23(1) + §24(3) + §24(4) BFIU disseminates to a dozen named recipient
-- authority categories, each with its own format / cadence / legal basis. A
-- procurement-grade ledger must capture WHO + WHICH CLAUSE rather than free
-- text. Circular 22 also creates a parallel bank-to-bank exchange channel
-- (under §23(1)(d) + ATA §15(1)(d)) distinct from BFIU outbound dissemination
-- — flagged separately for audit.
--
-- Three additive columns. All nullable for back-compat with existing rows;
-- application code keeps writing the legacy `recipient_type` + `recipient_agency`
-- alongside the typed fields until the next data backfill.
--
-- recipient_authority enum (13 values) drawn from MLPA + the BFIU dissemination
-- catalogue:
--   bangladesh_police_cid                   - LEA hub for ML predicate offences
--   anti_corruption_commission              - ACC, public-sector corruption
--   national_board_of_revenue               - NBR, customs + tax (incl TBML)
--   dept_narcotics_control                  - DNC, drug-trafficking ML
--   bangladesh_securities_exchange_commission - BSEC, securities fraud
--   insurance_dev_regulatory_authority      - IDRA, insurance fraud
--   microcredit_regulatory_authority        - MRA, NGO/MFI sector
--   dgfi                                    - Directorate General of Forces Intel
--   nsi                                     - National Security Intelligence
--   court_or_investigating_officer          - MLPA §12 investigating officer / court
--   foreign_fiu_egmont                      - Egmont group peer FIU
--   bb_internal_dept                        - BB's own depts (FE Policy, BRPD, ...)
--   peer_reporting_org_circular_22          - bank-to-bank exchange under Circular 22
--
-- mlpa_section enum captures the enabling clause cited on each dissemination.
-- Covers MLPA §23(1)(a-g) + §24(3) + §24(4), plus ATA §15(1)(a-g) mirrors.

ALTER TABLE public.disseminations
  ADD COLUMN recipient_authority text NULL
    CHECK (recipient_authority IS NULL OR recipient_authority IN (
      'bangladesh_police_cid',
      'anti_corruption_commission',
      'national_board_of_revenue',
      'dept_narcotics_control',
      'bangladesh_securities_exchange_commission',
      'insurance_dev_regulatory_authority',
      'microcredit_regulatory_authority',
      'dgfi',
      'nsi',
      'court_or_investigating_officer',
      'foreign_fiu_egmont',
      'bb_internal_dept',
      'peer_reporting_org_circular_22'
    )),
  ADD COLUMN mlpa_section text NULL
    CHECK (mlpa_section IS NULL OR mlpa_section IN (
      'mlpa_23_1_a',
      'mlpa_23_1_b',
      'mlpa_23_1_c',
      'mlpa_23_1_d',
      'mlpa_23_1_e',
      'mlpa_23_1_f',
      'mlpa_23_1_g',
      'mlpa_24_3',
      'mlpa_24_4',
      'ata_15_1_a',
      'ata_15_1_b',
      'ata_15_1_c',
      'ata_15_1_d',
      'ata_15_1_e',
      'ata_15_1_f',
      'ata_15_1_g'
    )),
  ADD COLUMN circular_22_exchange boolean NOT NULL DEFAULT false;

-- Index by typed authority so the procurement-grade "year-end stats by recipient
-- authority" report is fast.
CREATE INDEX idx_dissem_recipient_authority ON public.disseminations(recipient_authority)
  WHERE recipient_authority IS NOT NULL;

-- Partial index for the bank-to-bank exchange channel — likely to be queried
-- in isolation when BFIU asks "how many Circular-22 exchanges did Sonali make
-- in Q2?".
CREATE INDEX idx_dissem_circular_22 ON public.disseminations(org_id, disseminated_at DESC)
  WHERE circular_22_exchange = true;
