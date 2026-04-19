-- Migration 011: Allow `match_definition` as an alerts.source_type
--
-- The existing CHECK on `alerts.source_type` only permits the four
-- system source types (scan, cross_bank, str_enrichment, manual).
-- The custom-match executor (Task 4 of the post-launch priority stack)
-- emits alerts whose source is a BFIU-defined match_definition row,
-- so the constraint needs the new value.
--
-- Pattern follows migration 002 (CHECK relaxation): drop + re-add by
-- the auto-generated constraint name. Idempotent via the IF EXISTS
-- guard in case the constraint was dropped manually.

ALTER TABLE alerts DROP CONSTRAINT IF EXISTS alerts_source_type_check;

ALTER TABLE alerts
  ADD CONSTRAINT alerts_source_type_check
  CHECK (source_type IN (
    'scan',
    'cross_bank',
    'str_enrichment',
    'manual',
    'match_definition'
  ));
