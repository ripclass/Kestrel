-- Migration 020: Agent investigation log (V3 phase 3.2)
-- Applied: 2026-05-05
--
-- Persists every multi-step agentic investigation kicked off via
-- POST /agents/investigate. The agent's bounded execution (max 8 hops,
-- 60-second wall-clock cap) writes one row per investigation with the
-- prompt, hypothesis, full evidence trail (JSON list of tool/args/result
-- triples), suggested next actions, and the per-hop AI calls captured
-- separately in ai_outcome_log via the existing dual-write hook.
--
-- RLS: own-org or regulator on SELECT, own-org INSERT/UPDATE.

CREATE TABLE agent_investigations (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  org_id uuid NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
  entity_id uuid REFERENCES entities(id),
  initiated_by uuid REFERENCES auth.users(id),
  prompt text NOT NULL,
  status text NOT NULL DEFAULT 'completed'
    CHECK (status IN ('running','completed','failed','cancelled','exhausted')),
  hypothesis text,
  evidence jsonb NOT NULL DEFAULT '[]'::jsonb,
  suggested_actions text[] NOT NULL DEFAULT '{}',
  confidence numeric,
  hops_used integer NOT NULL DEFAULT 0,
  latency_ms integer NOT NULL DEFAULT 0,
  error text,
  created_at timestamptz NOT NULL DEFAULT now(),
  completed_at timestamptz
);

CREATE INDEX idx_agent_investigations_org_created
  ON agent_investigations (org_id, created_at DESC);
CREATE INDEX idx_agent_investigations_entity
  ON agent_investigations (entity_id, created_at DESC);

ALTER TABLE agent_investigations ENABLE ROW LEVEL SECURITY;

CREATE POLICY agent_investigations_select ON agent_investigations
  FOR SELECT
  USING (org_id = public.auth_org_id() OR public.is_regulator());

CREATE POLICY agent_investigations_insert ON agent_investigations
  FOR INSERT
  WITH CHECK (org_id = public.auth_org_id());

CREATE POLICY agent_investigations_update ON agent_investigations
  FOR UPDATE
  USING (org_id = public.auth_org_id())
  WITH CHECK (org_id = public.auth_org_id());
