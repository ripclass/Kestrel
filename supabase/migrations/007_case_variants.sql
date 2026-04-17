-- Migration 007: Case variants (goAML Task 8)
-- Applied: 2026-04-17
--
-- Closes the goAML gap that distinguishes Cases / Case Proposals / RFI /
-- Operations / Projects / FIU Escalated Case / Complaint Case /
-- Adverse Media Case. The existing `cases.category` column is kept as the
-- *subject* category (fraud / money_laundering / tbml / etc., mirroring
-- `str_reports.category`), so the new goAML-style classification lives in
-- a new `variant` column. That avoids clobbering the existing 'fraud'
-- value already present in prod.

ALTER TABLE cases ADD COLUMN variant text NOT NULL DEFAULT 'standard'
  CHECK (variant IN (
    'standard',       -- general-purpose case
    'proposal',       -- pre-opened case awaiting manager decision
    'rfi',            -- Request For Information (analyst → analyst)
    'operation',      -- larger multi-case operation
    'project',        -- long-running thematic project
    'escalated',      -- FIU Escalated Case
    'complaint',      -- Complaint Case
    'adverse_media'   -- Adverse Media Case
  ));

-- Hierarchy (operations reference parent cases; RFIs can reference the
-- case that spawned them).
ALTER TABLE cases ADD COLUMN parent_case_id uuid REFERENCES cases(id);

-- RFI wiring: who asked, who was asked.
ALTER TABLE cases ADD COLUMN requested_by uuid REFERENCES auth.users(id);
ALTER TABLE cases ADD COLUMN requested_from uuid REFERENCES auth.users(id);

-- Proposal decision state (only meaningful when variant = 'proposal').
ALTER TABLE cases ADD COLUMN proposal_decision text
  CHECK (proposal_decision IS NULL OR proposal_decision IN ('approved','rejected','pending'));
ALTER TABLE cases ADD COLUMN proposal_decided_by uuid REFERENCES auth.users(id);
ALTER TABLE cases ADD COLUMN proposal_decided_at timestamptz;

CREATE INDEX IF NOT EXISTS idx_cases_variant ON cases(variant);
CREATE INDEX IF NOT EXISTS idx_cases_parent
  ON cases(parent_case_id) WHERE parent_case_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_cases_rfi_from
  ON cases(requested_from) WHERE requested_from IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_cases_rfi_by
  ON cases(requested_by) WHERE requested_by IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_cases_proposal_pending
  ON cases(proposal_decision) WHERE proposal_decision = 'pending';
