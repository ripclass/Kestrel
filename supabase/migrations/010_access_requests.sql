-- Migration 010: Public access-request intake
-- Applied: 2026-04-18
--
-- Landing-page intake form (web/src/components/public/intake-form.tsx) POSTs
-- to submitAccessRequest (web/src/app/actions/access.ts) which uses a service-
-- role Supabase client to insert into this table. The service role bypasses
-- RLS for writes. SELECT is locked to superadmins only so operator staff can
-- triage requests but nobody else — including regulators — can read them.
--
-- No UPDATE / DELETE policies: the table is append-only by design.

CREATE TABLE access_requests (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  institution text NOT NULL,
  institution_type text NOT NULL
    CHECK (institution_type IN ('BFIU','Commercial Bank','MFS','NBFI','Peer Regulator','Press')),
  designation text NOT NULL,
  email text NOT NULL,
  use_case text NOT NULL CHECK (length(use_case) >= 50),
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX idx_access_requests_created_at ON access_requests (created_at DESC);
CREATE INDEX idx_access_requests_institution_type ON access_requests (institution_type);

ALTER TABLE access_requests ENABLE ROW LEVEL SECURITY;

-- SELECT: superadmin only. Everyone else — including regulators — gets nothing.
CREATE POLICY access_requests_select_superadmin ON access_requests
  FOR SELECT
  USING (
    EXISTS (
      SELECT 1 FROM profiles
      WHERE profiles.id = auth.uid()
        AND profiles.role = 'superadmin'
    )
  );

-- No INSERT policy: writes go through the service role only.
-- No UPDATE / DELETE policies: append-only audit surface.
