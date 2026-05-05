-- Migration 021: Sovereign rollout config + promotion log (V3 phase 5)
-- Applied: 2026-05-05
--
-- Two tables:
--
--  * sovereign_rollout — runtime-mutable per-task threshold + rollout_pct.
--    The static defaults live in `engine/app/ai/thresholds.py`; this
--    table overrides them so the V3 P5 rollback Beat task can shrink
--    a task's rollout without a redeploy. `app.services.sovereign_rollout`
--    reads with a 60-second in-process cache.
--
--  * sovereign_promotion_log — audit trail for every promotion attempt
--    against a candidate adapter. Rows are append-only. Used by the V3
--    P5 promotion harness in infra/training/promote_sovereign_adapter.py.
--
-- RLS: any-authed read on both. Writes are regulator-only — promotion
-- decisions and rollout flips are operator-level events. Engine writes
-- via the postgres BYPASSRLS connection from the Beat task and the
-- promotion script.

CREATE TABLE sovereign_rollout (
  task_name text PRIMARY KEY,
  threshold numeric NOT NULL DEFAULT 1.01,
  rollout_pct integer NOT NULL DEFAULT 0
    CHECK (rollout_pct >= 0 AND rollout_pct <= 100),
  reason text,
  updated_by text,
  updated_at timestamptz NOT NULL DEFAULT now()
);

ALTER TABLE sovereign_rollout ENABLE ROW LEVEL SECURITY;

CREATE POLICY sovereign_rollout_read ON sovereign_rollout
  FOR SELECT
  USING (auth.uid() IS NOT NULL);

CREATE POLICY sovereign_rollout_insert_regulator ON sovereign_rollout
  FOR INSERT
  WITH CHECK (public.is_regulator());

CREATE POLICY sovereign_rollout_update_regulator ON sovereign_rollout
  FOR UPDATE
  USING (public.is_regulator())
  WITH CHECK (public.is_regulator());


CREATE TABLE sovereign_promotion_log (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  adapter_path text NOT NULL,
  base_model text NOT NULL,
  candidate_metrics jsonb NOT NULL DEFAULT '{}'::jsonb,
  gate_results jsonb NOT NULL DEFAULT '[]'::jsonb,
  all_passed boolean NOT NULL DEFAULT false,
  ran_at timestamptz NOT NULL DEFAULT now(),
  ran_by text,
  notes text
);

CREATE INDEX idx_sovereign_promotion_ran_at ON sovereign_promotion_log (ran_at DESC);
CREATE INDEX idx_sovereign_promotion_passed ON sovereign_promotion_log (all_passed, ran_at DESC);

ALTER TABLE sovereign_promotion_log ENABLE ROW LEVEL SECURITY;

CREATE POLICY sovereign_promotion_read ON sovereign_promotion_log
  FOR SELECT
  USING (auth.uid() IS NOT NULL);

CREATE POLICY sovereign_promotion_insert_regulator ON sovereign_promotion_log
  FOR INSERT
  WITH CHECK (public.is_regulator());
