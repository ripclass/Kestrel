-- Migration 017: Public status surface (V2 phase 6.1)
-- Applied: 2026-05-05
--
-- Two tables back the public /status page:
--   * uptime_pings  - the raw observation log written by the 5-minute
--                     Beat task. The 30/90-day uptime % is computed by
--                     SQL aggregation over this table.
--   * status_incidents - manually-posted incident reports surfaced on
--                     the public page. Banks subscribed to the incident
--                     feed see new entries via polling.
--
-- RLS: SELECT is OPEN (no auth) on both tables — the status page is
-- public infrastructure. Writes are regulator-only (the engine's
-- BYPASSRLS path handles uptime_pings ingestion; admin UI handles
-- incidents).

CREATE TABLE uptime_pings (
  id bigserial PRIMARY KEY,
  observed_at timestamptz NOT NULL DEFAULT now(),
  component text NOT NULL CHECK (component IN ('overall','auth','database','redis','storage','worker','ai')),
  status text NOT NULL CHECK (status IN ('up','degraded','down','unknown')),
  latency_ms integer,
  detail text
);

CREATE INDEX idx_uptime_pings_component_observed
  ON uptime_pings (component, observed_at DESC);
-- Recency-only query (used by the status page's "last 5 min" indicator).
CREATE INDEX idx_uptime_pings_observed
  ON uptime_pings (observed_at DESC);

ALTER TABLE uptime_pings ENABLE ROW LEVEL SECURITY;

-- Public-read: the status page is anonymous. Writes happen via the
-- engine's `postgres` (BYPASSRLS) connection from the Beat task only.
CREATE POLICY uptime_pings_public_read ON uptime_pings
  FOR SELECT
  USING (true);


CREATE TABLE status_incidents (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  started_at timestamptz NOT NULL DEFAULT now(),
  ended_at timestamptz,
  severity text NOT NULL CHECK (severity IN ('minor','major','outage')),
  component text NOT NULL CHECK (component IN ('overall','auth','database','redis','storage','worker','ai','web','engine')),
  summary text NOT NULL,
  message text,
  posted_by uuid REFERENCES auth.users(id),
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX idx_status_incidents_started ON status_incidents (started_at DESC);
CREATE INDEX idx_status_incidents_active
  ON status_incidents (started_at DESC)
  WHERE ended_at IS NULL;

ALTER TABLE status_incidents ENABLE ROW LEVEL SECURITY;

CREATE POLICY status_incidents_public_read ON status_incidents
  FOR SELECT
  USING (true);

CREATE POLICY status_incidents_insert_regulator ON status_incidents
  FOR INSERT
  WITH CHECK (public.is_regulator());

CREATE POLICY status_incidents_update_regulator ON status_incidents
  FOR UPDATE
  USING (public.is_regulator())
  WITH CHECK (public.is_regulator());

CREATE TRIGGER trg_status_incidents_updated_at
  BEFORE UPDATE ON status_incidents
  FOR EACH ROW
  EXECUTE FUNCTION public.update_timestamp();
