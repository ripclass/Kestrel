-- 013_qualify_security_definer_helpers.sql
--
-- Hot-fix for a regression introduced by migration 012_advisor_fixes.sql
-- (locked search_path = '' on 7 helpers/triggers).
--
-- The lock-down was correct in spirit but the function bodies still
-- reference unqualified relation names (`profiles`, `organizations`,
-- sequences `case_ref_seq` / `str_ref_seq` / `dissem_ref_seq`). With
-- search_path = '' those names cannot resolve, so:
--
--   * gen_case_ref()       — fails on every cases INSERT
--                             (`relation "case_ref_seq" does not exist`)
--   * gen_str_ref()        — fails on every str_reports INSERT
--   * gen_dissem_ref()     — fails on every disseminations INSERT
--   * auth_org_id()        — fails inside RLS evaluation
--                             (`relation "profiles" does not exist`)
--   * is_regulator()       — same failure mode
--
-- Discovered while running RLS isolation simulation on 2026-05-05 as part
-- of V2 phase 2.4 (multi-tenant isolation verification). Reproducer:
--
--   INSERT INTO public.cases (org_id, title, severity, category)
--     VALUES ('9c111111-1111-4111-8111-111111111111','rls-test','low','fraud');
--   -- ERROR:  relation "case_ref_seq" does not exist
--
-- Production blast radius (zero rows created since migration 012 applied
-- on 2026-05-04 because nothing has been written through these triggers):
--   * cases: max(created_at) = 2026-04-03 (pre-fix)
--   * str_reports: max(created_at) = 2026-04-03 (pre-fix)
--   * disseminations: 0 rows
--
-- Engine paths that bypass this regression: writes initiated through the
-- engine API connect as the `postgres` role which has BYPASSRLS, but the
-- gen_*_ref triggers fire regardless of role and fail. The signup flow
-- shipped in V2 phase 2.2 happens to work because handle_new_user() was
-- already schema-qualified at the time migration 012 ran.
--
-- Fix: redefine each broken function with schema-qualified references and
-- the SECURITY DEFINER + search_path = '' guarantees preserved. After
-- apply, verify by inserting and rolling back a test case row.

CREATE OR REPLACE FUNCTION public.auth_org_id()
RETURNS uuid
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = ''
AS $$
  SELECT org_id FROM public.profiles WHERE id = auth.uid()
$$;

CREATE OR REPLACE FUNCTION public.is_regulator()
RETURNS boolean
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = ''
AS $$
  SELECT EXISTS (
    SELECT 1
    FROM public.profiles p
    JOIN public.organizations o ON o.id = p.org_id
    WHERE p.id = auth.uid() AND o.org_type = 'regulator'
  )
$$;

CREATE OR REPLACE FUNCTION public.gen_case_ref()
RETURNS trigger
LANGUAGE plpgsql
SET search_path = ''
AS $$
BEGIN
  IF NEW.case_ref IS NULL OR NEW.case_ref = '' THEN
    NEW.case_ref := 'KST-'
      || to_char(now(), 'YYMM') || '-'
      || lpad(nextval('public.case_ref_seq')::text, 5, '0');
  END IF;
  RETURN NEW;
END;
$$;

CREATE OR REPLACE FUNCTION public.gen_str_ref()
RETURNS trigger
LANGUAGE plpgsql
SET search_path = ''
AS $$
DECLARE
  prefix text;
BEGIN
  IF NEW.report_ref IS NULL OR NEW.report_ref = '' THEN
    prefix := CASE coalesce(NEW.report_type, 'str')
      WHEN 'str'               THEN 'STR'
      WHEN 'sar'               THEN 'SAR'
      WHEN 'ctr'               THEN 'CTR'
      WHEN 'tbml'              THEN 'TBML'
      WHEN 'complaint'         THEN 'COMP'
      WHEN 'ier'               THEN 'IER'
      WHEN 'internal'          THEN 'INT'
      WHEN 'adverse_media_str' THEN 'AMSTR'
      WHEN 'adverse_media_sar' THEN 'AMSAR'
      WHEN 'escalated'         THEN 'ESC'
      WHEN 'additional_info'   THEN 'ADDL'
      ELSE upper(coalesce(NEW.report_type, 'str'))
    END;
    NEW.report_ref := prefix || '-'
      || to_char(now(), 'YYMM') || '-'
      || lpad(nextval('public.str_ref_seq')::text, 6, '0');
  END IF;
  RETURN NEW;
END;
$$;

CREATE OR REPLACE FUNCTION public.gen_dissem_ref()
RETURNS trigger
LANGUAGE plpgsql
SET search_path = ''
AS $$
BEGIN
  IF NEW.dissemination_ref IS NULL OR NEW.dissemination_ref = '' THEN
    NEW.dissemination_ref := 'DISS-'
      || to_char(now(), 'YYMM') || '-'
      || lpad(nextval('public.dissem_ref_seq')::text, 5, '0');
  END IF;
  RETURN NEW;
END;
$$;
