-- 012_advisor_fixes.sql
-- Resolves Supabase advisor warnings surfaced by the 2026-04 production audit.
-- See docs/production-audit-2026-04.md §9 risk flag #3.
--
-- WHAT THIS MIGRATION FIXES (6 of 13 original advisor warnings):
--   * function_search_path_mutable on 6 helpers + the 1 dissem-ref trigger.
--     Locks search_path = '' so a malicious schema cannot shadow built-ins
--     during execution. Highest-priority fix because all 6 funcs are
--     SECURITY DEFINER.
--
-- WHAT THIS MIGRATION DOES NOT FIX (7 remaining warnings, all WARN-level):
--
-- 1. extension_in_public on pg_trgm.
--    The resolver (engine/app/core/resolver.py) calls similarity()
--    unqualified. Moving the extension to `extensions` would require either
--    qualifying every call site or altering the database role's search_path.
--    Net risk of the move outweighs the warning.
--
-- 2/3. anon_security_definer_function_executable +
--      authenticated_security_definer_function_executable on auth_org_id(),
--      is_regulator(), handle_new_user().
--    These are granted EXECUTE to PUBLIC by default. Revoking from PUBLIC
--    would also block the `authenticated` role, breaking every RLS policy
--    that invokes auth_org_id() during request evaluation. The advisors
--    flag the /rest/v1/rpc/* exposure as procedural, not as data risk:
--      - auth_org_id() called by anon returns NULL (auth.uid() is null →
--        WHERE id = null matches nothing → returns NULL).
--      - is_regulator() called by anon returns false for the same reason.
--      - handle_new_user() is a trigger function; calling it via RPC fails
--        with a wrong-argument-count error before any side effect.
--    Zero data leakage in all three cases.
--
--    The proper fix (move helpers to a non-PostgREST-exposed schema +
--    qualify every RLS policy reference) is multi-hour work for cosmetic
--    audit silence. Accept and document.

ALTER FUNCTION public.auth_org_id() SET search_path = '';
ALTER FUNCTION public.is_regulator() SET search_path = '';
ALTER FUNCTION public.handle_new_user() SET search_path = '';
ALTER FUNCTION public.update_timestamp() SET search_path = '';
ALTER FUNCTION public.gen_case_ref() SET search_path = '';
ALTER FUNCTION public.gen_str_ref() SET search_path = '';
ALTER FUNCTION public.gen_dissem_ref() SET search_path = '';
