-- Migration 014: Real-time transaction-scoring log (V2 phase 3.1 / 3.2)
-- Applied: 2026-05-05
--
-- Persists every call to POST /transactions/score so banks can audit
-- decisions, latency, and the eventual ML feedback loop has a corpus to
-- train on. RLS: own-org or regulator. INSERTs are funneled through the
-- engine's `postgres` (BYPASSRLS) connection like every other write path.

CREATE TABLE realtime_scoring_log (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  org_id uuid NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
  transaction_external_id text NOT NULL,
  request_payload jsonb NOT NULL,
  score integer NOT NULL,
  decision text NOT NULL CHECK (decision IN ('approve','review','hold','reject')),
  reasons jsonb NOT NULL DEFAULT '[]'::jsonb,
  cross_bank_flag boolean NOT NULL DEFAULT false,
  latency_ms integer NOT NULL,
  request_id text,
  feedback_received boolean NOT NULL DEFAULT false,
  feedback_outcome text CHECK (feedback_outcome IS NULL OR feedback_outcome IN ('legitimate','fraud','unsure')),
  feedback_at timestamptz,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX idx_realtime_scoring_org_created ON realtime_scoring_log (org_id, created_at DESC);
CREATE INDEX idx_realtime_scoring_external_id ON realtime_scoring_log (org_id, transaction_external_id);
CREATE INDEX idx_realtime_scoring_decision ON realtime_scoring_log (decision, created_at DESC);

ALTER TABLE realtime_scoring_log ENABLE ROW LEVEL SECURITY;

-- SELECT: own-org users + regulator (regulator gets the cross-system view in P3.4 dashboard).
CREATE POLICY realtime_scoring_select ON realtime_scoring_log
  FOR SELECT
  USING (org_id = public.auth_org_id() OR public.is_regulator());

-- UPDATE: own-org only (the feedback endpoint flips feedback_received + feedback_outcome).
-- Regulator does not edit a bank's feedback on its own decisions.
CREATE POLICY realtime_scoring_update ON realtime_scoring_log
  FOR UPDATE
  USING (org_id = public.auth_org_id())
  WITH CHECK (org_id = public.auth_org_id());

-- No INSERT policy: writes go through the engine's BYPASSRLS connection only.
-- No DELETE policy: the log is append-only by design.
