-- Migration 019: AI outcome logging (V3 phase 1.1)
-- Applied: 2026-05-05
--
-- Foundation for the V3 sovereign-AI track. Every AI call writes one row
-- here with the (redacted) prompt, the structured output, the provider +
-- model, latency + token counts, and an optional analyst correction
-- captured later when the bank's CAMLCO edits the AI-drafted output.
--
-- This is the corpus the V3 phase 4 fine-tune harness will train on. The
-- schema is deliberately denormalised — keeping the redacted prompt + the
-- output JSON in this table means an offline trainer can run from
-- a single Supabase backup without joining audit_log.
--
-- The existing ``audit_log`` row with action='ai.invoke' continues to be
-- written alongside this — same dual-write pattern as realtime_scoring_log
-- vs audit_log from V2 P3.

CREATE TABLE ai_outcome_log (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  org_id uuid REFERENCES organizations(id) ON DELETE CASCADE,
  task_name text NOT NULL,
  provider text NOT NULL,
  model text NOT NULL,
  prompt_redacted text NOT NULL,
  prompt_digest text NOT NULL,
  output_json jsonb NOT NULL,
  confidence numeric,
  analyst_correction jsonb,
  outcome_label text CHECK (
    outcome_label IS NULL OR outcome_label IN (
      'true_positive','false_positive','accepted','rejected','edited'
    )
  ),
  latency_ms integer NOT NULL,
  prompt_tokens integer,
  completion_tokens integer,
  cost_usd numeric,
  fallback_from_provider text,
  fallback_from_model text,
  request_id text,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX idx_ai_outcome_task_created ON ai_outcome_log (task_name, created_at DESC);
CREATE INDEX idx_ai_outcome_org_created ON ai_outcome_log (org_id, created_at DESC);
-- Partial index on rows with corrections — the training-corpus export
-- query is "give me corrections from the last N days" and this is the
-- index that serves it.
CREATE INDEX idx_ai_outcome_with_correction
  ON ai_outcome_log (task_name, created_at DESC)
  WHERE analyst_correction IS NOT NULL;

ALTER TABLE ai_outcome_log ENABLE ROW LEVEL SECURITY;

-- SELECT: own-org or regulator. The regulator-cross-org read is what
-- powers the platform-wide accuracy dashboard at /admin/ai-outcomes.
CREATE POLICY ai_outcome_select ON ai_outcome_log
  FOR SELECT
  USING (org_id = public.auth_org_id() OR public.is_regulator());

-- UPDATE: own-org only. The correction-capture endpoint flips
-- analyst_correction + outcome_label; nothing else is mutable.
CREATE POLICY ai_outcome_update ON ai_outcome_log
  FOR UPDATE
  USING (org_id = public.auth_org_id())
  WITH CHECK (org_id = public.auth_org_id());

-- No INSERT policy: writes go through the engine's BYPASSRLS connection.
-- No DELETE policy: the corpus is append-only.

CREATE TRIGGER trg_ai_outcome_log_updated_at
  BEFORE UPDATE ON ai_outcome_log
  FOR EACH ROW
  EXECUTE FUNCTION public.update_timestamp();
