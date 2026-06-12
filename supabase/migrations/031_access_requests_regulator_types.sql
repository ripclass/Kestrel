-- Migration 031: widen access_requests.institution_type for regulator intake
-- Applied: 2026-06-12
--
-- The public contact form (web/src/components/public/intake-form.tsx) shows a
-- DIFFERENT institution_type option set when audience="regulator"
-- ('Financial Intelligence Unit','Central Bank','Supervisory Authority',
-- 'Other regulator') — none of which were in the migration-010 CHECK. A
-- regulator visitor (reached via /contact?audience=regulator) selecting any
-- option hit a CHECK violation, surfaced to them as a generic
-- "System error logging request" — the regulator-intake path was silently
-- broken end-to-end. Widen the CHECK to the union of both option arrays.

ALTER TABLE access_requests
  DROP CONSTRAINT IF EXISTS access_requests_institution_type_check;

ALTER TABLE access_requests
  ADD CONSTRAINT access_requests_institution_type_check
  CHECK (institution_type IN (
    'BFIU', 'Commercial Bank', 'MFS', 'NBFI', 'Peer Regulator', 'Press',
    'Financial Intelligence Unit', 'Central Bank', 'Supervisory Authority', 'Other regulator'
  ));
