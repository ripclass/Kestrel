-- Migration 008: Intel menu tables (goAML Task 9)
-- Applied: 2026-04-17
--
-- Adds three goAML Intel-menu capabilities as first-class tables:
-- - saved_queries: analyst-authored reusable filters / searches
--   ("Profiles" in goAML parlance). Per-user by default, optionally
--   shared across the owning org.
-- - diagrams: manual network graph canvases saved from the Investigate
--   diagram builder. JSONB stores nodes, edges, annotations, and
--   layout — the React Flow canvas rehydrates from this blob.
-- - match_definitions + match_executions: bespoke BFIU-defined matching
--   rules. Kestrel ships 8 system rules in YAML; this table lets an
--   admin add ad-hoc definitions without a code deploy. Executions log
--   the outcome of each run for audit.
--
-- The Message Board surface from goAML is deliberately excluded — see
-- docs/goaml-coverage.md (authored in Task 12) for the rationale.

-- ============================================================
-- 1. Saved Queries (goAML "Profiles")
-- ============================================================

CREATE TABLE saved_queries (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  org_id uuid NOT NULL REFERENCES organizations(id),
  user_id uuid NOT NULL REFERENCES auth.users(id),
  name text NOT NULL,
  description text,
  query_type text NOT NULL
    CHECK (query_type IN ('entity_search','transaction_search','str_filter','alert_filter','case_filter','custom')),
  query_definition jsonb NOT NULL DEFAULT '{}'::jsonb,
  is_shared boolean NOT NULL DEFAULT false,
  last_run_at timestamptz,
  run_count integer NOT NULL DEFAULT 0,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX idx_saved_queries_user ON saved_queries(user_id);
CREATE INDEX idx_saved_queries_org_shared
  ON saved_queries(org_id) WHERE is_shared = true;
CREATE INDEX idx_saved_queries_type ON saved_queries(query_type);

ALTER TABLE saved_queries ENABLE ROW LEVEL SECURITY;

CREATE POLICY saved_queries_read ON saved_queries FOR SELECT
  USING (
    user_id = auth.uid()
    OR (is_shared = true AND org_id = auth_org_id())
    OR is_regulator()
  );

-- Writes are always per-user; regulator impersonation is out of scope.
CREATE POLICY saved_queries_insert ON saved_queries FOR INSERT
  WITH CHECK (user_id = auth.uid() AND org_id = auth_org_id());

CREATE POLICY saved_queries_update ON saved_queries FOR UPDATE
  USING (user_id = auth.uid())
  WITH CHECK (user_id = auth.uid());

CREATE POLICY saved_queries_delete ON saved_queries FOR DELETE
  USING (user_id = auth.uid());

-- ============================================================
-- 2. Diagrams (manual network graph canvases)
-- ============================================================

CREATE TABLE diagrams (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  org_id uuid NOT NULL REFERENCES organizations(id),
  created_by uuid REFERENCES auth.users(id),
  title text NOT NULL,
  description text,
  graph_definition jsonb NOT NULL DEFAULT '{}'::jsonb,
  linked_case_id uuid REFERENCES cases(id),
  linked_str_id uuid REFERENCES str_reports(id),
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX idx_diagrams_org ON diagrams(org_id);
CREATE INDEX idx_diagrams_case
  ON diagrams(linked_case_id) WHERE linked_case_id IS NOT NULL;
CREATE INDEX idx_diagrams_str
  ON diagrams(linked_str_id) WHERE linked_str_id IS NOT NULL;

ALTER TABLE diagrams ENABLE ROW LEVEL SECURITY;
CREATE POLICY diagrams_org ON diagrams FOR ALL
  USING (org_id = auth_org_id() OR is_regulator())
  WITH CHECK (org_id = auth_org_id() OR is_regulator());

-- ============================================================
-- 3. Match Definitions + Executions (custom matching rules)
-- ============================================================

CREATE TABLE match_definitions (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  org_id uuid NOT NULL REFERENCES organizations(id),
  name text NOT NULL,
  description text,
  definition jsonb NOT NULL DEFAULT '{}'::jsonb,
  is_active boolean NOT NULL DEFAULT true,
  created_by uuid REFERENCES auth.users(id),
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  last_execution_at timestamptz,
  total_hits integer NOT NULL DEFAULT 0,
  UNIQUE(org_id, name)
);

CREATE INDEX idx_match_defs_org ON match_definitions(org_id);
CREATE INDEX idx_match_defs_active
  ON match_definitions(org_id, is_active) WHERE is_active = true;

ALTER TABLE match_definitions ENABLE ROW LEVEL SECURITY;
CREATE POLICY match_defs_org ON match_definitions FOR ALL
  USING (org_id = auth_org_id() OR is_regulator())
  WITH CHECK (org_id = auth_org_id() OR is_regulator());

CREATE TABLE match_executions (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  definition_id uuid NOT NULL REFERENCES match_definitions(id) ON DELETE CASCADE,
  executed_at timestamptz NOT NULL DEFAULT now(),
  executed_by uuid REFERENCES auth.users(id),
  hit_count integer NOT NULL DEFAULT 0,
  execution_status text NOT NULL DEFAULT 'completed'
    CHECK (execution_status IN ('pending','running','completed','failed')),
  results_summary jsonb NOT NULL DEFAULT '{}'::jsonb
);

CREATE INDEX idx_match_executions_definition
  ON match_executions(definition_id, executed_at DESC);

ALTER TABLE match_executions ENABLE ROW LEVEL SECURITY;
CREATE POLICY match_executions_read ON match_executions FOR ALL
  USING (EXISTS (
    SELECT 1 FROM match_definitions md
    WHERE md.id = definition_id
      AND (md.org_id = auth_org_id() OR is_regulator())
  ))
  WITH CHECK (EXISTS (
    SELECT 1 FROM match_definitions md
    WHERE md.id = definition_id
      AND (md.org_id = auth_org_id() OR is_regulator())
  ));
