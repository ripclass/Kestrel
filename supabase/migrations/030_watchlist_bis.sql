-- Migration 030: add BIS to the watchlist source allow-list
-- Applied: 2026-06-12
--
-- Pilot-driven (Sonali / Ramprosad): incorporate US Bureau of Industry and
-- Security denied-party / entity-list screening for trade-finance
-- (proliferation-financing) controls. Source data is the free trade.gov
-- Consolidated Screening List, filtered to BIS sublists (DPL / EL / UVL)
-- by engine/app/screening/sources/bis.py.
--
-- The watchlist_entries.list_source CHECK from migration 015 enumerates the
-- allowed sources; add 'BIS'. Same drop-and-readd pattern used by 011 / 016
-- for relaxing CHECK constraints.

ALTER TABLE watchlist_entries
  DROP CONSTRAINT IF EXISTS watchlist_entries_list_source_check;

ALTER TABLE watchlist_entries
  ADD CONSTRAINT watchlist_entries_list_source_check
  CHECK (list_source IN ('OFAC','EU','UN','UK_OFSI','BB_DOMESTIC','PEP','ADVERSE_MEDIA','BIS'));
