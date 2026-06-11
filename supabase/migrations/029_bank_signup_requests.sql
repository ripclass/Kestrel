-- Migration 029: Bank signup vetting queue
-- Applied: 2026-06-11
--
-- /signup/bank no longer provisions a tenant instantly. The form
-- (web/src/app/actions/bank-signup.ts) inserts a pending row here via the
-- service-role client; platform operators review in the operator console
-- (/platform/signups) and approve -> provisionTenant() creates the org +
-- admin invite, stamping org_id back onto the request. Rejections keep the
-- row for the audit trail.
--
-- source_ip + created_at support the form's per-IP rate limit (3/hour).
-- Service role bypasses RLS for all writes; SELECT is superadmin-only,
-- mirroring access_requests (migration 010).

CREATE TABLE bank_signup_requests (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  bank_name text NOT NULL,
  full_name text NOT NULL,
  designation text NOT NULL,
  email text NOT NULL,
  phone text,
  demo_narrative text NOT NULL CHECK (length(demo_narrative) >= 30),
  status text NOT NULL DEFAULT 'pending'
    CHECK (status IN ('pending', 'approved', 'rejected')),
  source_ip text,
  user_agent text,
  decided_by text,
  decided_at timestamptz,
  decision_note text,
  org_id uuid REFERENCES organizations(id) ON DELETE SET NULL,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX idx_bank_signup_requests_created_at
  ON bank_signup_requests (created_at DESC);
CREATE INDEX idx_bank_signup_requests_pending
  ON bank_signup_requests (created_at DESC) WHERE status = 'pending';
CREATE INDEX idx_bank_signup_requests_email
  ON bank_signup_requests (email);
CREATE INDEX idx_bank_signup_requests_source_ip
  ON bank_signup_requests (source_ip, created_at DESC);

ALTER TABLE bank_signup_requests ENABLE ROW LEVEL SECURITY;

-- SELECT: superadmin only — operator staff triage via the service-role
-- actions; nobody else (including regulators) reads the queue.
CREATE POLICY bank_signup_requests_select_superadmin ON bank_signup_requests
  FOR SELECT
  USING (
    EXISTS (
      SELECT 1 FROM profiles
      WHERE profiles.id = auth.uid()
        AND profiles.role = 'superadmin'
    )
  );

-- No INSERT / UPDATE / DELETE policies: all writes go through the
-- service role (signup action + operator review actions).
