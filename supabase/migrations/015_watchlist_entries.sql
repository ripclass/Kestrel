-- Migration 015: Watchlist entries (V2 phase 4.1)
-- Applied: 2026-05-05
--
-- Backs the sanctions / PEP / adverse-media screening surface. Sources are
-- public lists (OFAC SDN, EU consolidated, UN Security Council, UK OFSI)
-- + Bangladesh Bank's domestic watchlist (manual upload). Each row carries
-- the raw upstream record under `raw_record` so future re-parses don't lose
-- fidelity, plus normalised columns for fast fuzzy matching.
--
-- RLS:
--   * SELECT — any authenticated user (banks need to screen against the pool;
--     it's a shared-intelligence resource by design).
--   * INSERT / UPDATE / DELETE — regulators only (writes go through the
--     scheduled ingestion tasks running as `postgres` BYPASSRLS, plus the
--     manual-upload admin path which is regulator-only at the router layer).
--   * No tenant scoping — watchlists are global by nature.

CREATE TABLE watchlist_entries (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  list_source text NOT NULL CHECK (list_source IN ('OFAC','EU','UN','UK_OFSI','BB_DOMESTIC','PEP','ADVERSE_MEDIA')),
  list_version text NOT NULL,
  entry_type text NOT NULL CHECK (entry_type IN ('individual','entity','vessel','aircraft')),
  primary_name text NOT NULL,
  aliases text[] NOT NULL DEFAULT '{}',
  date_of_birth date,
  nationality text,
  identifiers jsonb NOT NULL DEFAULT '{}'::jsonb,
  addresses jsonb NOT NULL DEFAULT '[]'::jsonb,
  reason text,
  raw_record jsonb NOT NULL DEFAULT '{}'::jsonb,
  ingested_at timestamptz NOT NULL DEFAULT now(),
  removed_at timestamptz
);

-- Trigram index on primary_name for fuzzy similarity matching.
CREATE INDEX idx_watchlist_name_trgm ON watchlist_entries USING gin (primary_name gin_trgm_ops);
-- GIN index on the aliases array — supports `WHERE aliases && ARRAY['...']` and
-- contains-style lookups for alias-first searches.
CREATE INDEX idx_watchlist_aliases ON watchlist_entries USING gin (aliases);
-- Partial index on active entries by source (most queries filter to active).
CREATE INDEX idx_watchlist_active ON watchlist_entries (list_source) WHERE removed_at IS NULL;
-- Soft delete + recency support.
CREATE INDEX idx_watchlist_ingested_at ON watchlist_entries (ingested_at DESC);

-- Uniqueness: same list + same primary_name + same DOB shouldn't be ingested
-- twice from the same upstream version. We deliberately allow the same name
-- on different lists (e.g. same person appears on both OFAC and EU).
CREATE UNIQUE INDEX uq_watchlist_source_name_dob_version
  ON watchlist_entries (list_source, primary_name, list_version, COALESCE(date_of_birth, '1900-01-01'::date));

ALTER TABLE watchlist_entries ENABLE ROW LEVEL SECURITY;

-- Anyone authed can read. The screening service is the consumer; bank
-- tenants need this to call POST /screening/entity.
CREATE POLICY watchlist_select_authenticated ON watchlist_entries
  FOR SELECT
  USING (auth.uid() IS NOT NULL);

-- Regulators can mutate. Engine ingestion runs as `postgres` (BYPASSRLS).
CREATE POLICY watchlist_insert_regulator ON watchlist_entries
  FOR INSERT
  WITH CHECK (public.is_regulator());

CREATE POLICY watchlist_update_regulator ON watchlist_entries
  FOR UPDATE
  USING (public.is_regulator())
  WITH CHECK (public.is_regulator());

CREATE POLICY watchlist_delete_regulator ON watchlist_entries
  FOR DELETE
  USING (public.is_regulator());
