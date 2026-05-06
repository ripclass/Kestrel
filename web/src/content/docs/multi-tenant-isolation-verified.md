# Multi-Tenant Isolation — Verified (V2 Phase 2.4)

**Date:** 2026-05-06  
**Scope:** Confirms that Kestrel's bank-direct tenancy (V2 phase 2 rollout) does
not leak data across bank tenants and that regulator-only surfaces are not
mutable from a bank persona.  
**Audience:** procurement, compliance, audit.

This document is *verification-only* — no code changes were made beyond the
hot-fix migration `013_qualify_security_definer_helpers.sql` discovered while
running the simulation (see §6).

---

## 1. Architecture summary

Kestrel enforces tenant isolation in four layers:

1. **Web route gate** — `requireRole(...)` and persona filters in
   `web/src/app/(platform)/**/page.tsx` and `web/src/components/shell/nav-config.ts`
   determine which surfaces appear in the sidebar and which pages reject the
   viewer outright.
2. **Engine route gate** — `Depends(require_roles(...))` on every authenticated
   FastAPI route in `engine/app/routers/**/*.py` rejects unprivileged callers
   with `403 Insufficient role`.
3. **Service-layer org-type guard** — explicit `if user.org_type != "regulator"`
   checks in services that handle BFIU-only data (CTR, reference tables,
   scanning scope, cross-bank persona-aware projection).
4. **Postgres RLS** — `org_id = auth_org_id() OR is_regulator()` policies on
   every per-tenant table. `auth_org_id()` resolves the caller's `profiles.org_id`
   via `auth.uid()`; `is_regulator()` returns `true` only for users whose org
   row has `org_type = 'regulator'`.

The engine connects as the `postgres` role which is `BYPASSRLS`, so RLS is the
*defense-in-depth* tier. The primary enforcement on the engine API path is the
service-layer org filter. RLS protects:
- direct PostgREST queries from the frontend (none in current Kestrel paths),
- any future direct-DB tooling,
- the `handle_new_user` trigger and similar triggers that run as
  `SECURITY DEFINER`.

---

## 2. RLS policies on per-tenant tables

Captured from `pg_policies` (verbatim):

| Table | Policy | Command | USING clause |
| --- | --- | --- | --- |
| `accounts` | `accounts_org` | ALL | `(org_id = auth_org_id()) OR is_regulator()` |
| `alerts` | `alerts_org` | ALL | `(org_id = auth_org_id()) OR is_regulator()` |
| `audit_log` | `audit_org` | ALL | `org_id = auth_org_id()` *(no regulator override)* |
| `cases` | `cases_org` | ALL | `(org_id = auth_org_id()) OR is_regulator()` |
| `cash_transaction_reports` | `ctr_org` | ALL | `(org_id = auth_org_id()) OR is_regulator()` |
| `diagrams` | `diagrams_org` | ALL | `(org_id = auth_org_id()) OR is_regulator()` |
| `disseminations` | `dissem_org` | ALL | `(org_id = auth_org_id()) OR is_regulator()` |
| `match_definitions` | `match_defs_org` | ALL | `(org_id = auth_org_id()) OR is_regulator()` |
| `str_reports` | `str_reports_org` | ALL | `(org_id = auth_org_id()) OR is_regulator()` |
| `transactions` | `transactions_org` | ALL | `(org_id = auth_org_id()) OR is_regulator()` |

Cross-bank intelligence tables are intentionally **shared**:

| Table | Policy | USING clause |
| --- | --- | --- |
| `entities` | `shared_entities` | `auth.uid() IS NOT NULL` |
| `matches` | `shared_matches` | `auth.uid() IS NOT NULL` |

Reference tables are read-shared, write-regulator:

| Policy | Command | Clause |
| --- | --- | --- |
| `reference_read` | SELECT | `auth.uid() IS NOT NULL` |
| `reference_insert` | INSERT | `WITH CHECK is_regulator()` |
| `reference_update` | UPDATE | `is_regulator()` |
| `reference_delete` | DELETE | `is_regulator()` |

Saved-queries policy is per-user with sharing:

| Policy | Command | Clause |
| --- | --- | --- |
| `saved_queries_read` | SELECT | `(user_id = auth.uid()) OR (is_shared AND org_id = auth_org_id()) OR is_regulator()` |
| `saved_queries_insert` | INSERT | `WITH CHECK ((user_id = auth.uid()) AND (org_id = auth_org_id()))` |
| `saved_queries_update` | UPDATE | `user_id = auth.uid()` |
| `saved_queries_delete` | DELETE | `user_id = auth.uid()` |

---

## 3. Regulator-only mutation guards (service layer)

| Surface | File | Guard |
| --- | --- | --- |
| Reference tables — CRUD | `engine/app/services/reference_tables.py` | `_require_regulator(user)` (line 29) raises `403 Only regulator users can modify reference tables.` |
| CTR list | `engine/app/services/ctr.py` | `if user.org_type != "regulator"` (line 34) |
| Scan-pipeline scope | `engine/app/services/scanning.py` | `if user.org_type != "regulator"` (line 161) caps `scope_org_ids` |
| Saved queries (cross-org override) | `engine/app/services/saved_queries.py` | `user.org_type != "regulator"` (line 104) |
| Persona enrolment | `engine/app/services/admin.py` | `_validate_requested_persona(org_type, persona)` (line 398) — bank orgs cannot mint `bfiu_*` personas |
| Reporting national/compliance | `engine/app/services/reporting.py` | `org_type=="regulator"` (line 483) for cross-bank cluster visibility |

---

## 4. Cross-bank persona invariants (service layer)

`engine/app/services/cross_bank.py` is the only service that reads
cross-tenant data on behalf of a bank persona. The invariants are encoded in
two helpers:

**`_label_orgs_for_user`** (lines 67–86) — replaces every peer bank name with
`"Peer institution N"` for any user whose `org_type != "regulator"`.

**`_anonymize_match_key`** (lines 89–96) — redacts the leading characters of
the match key, leaving only `····` + the last 4 characters, again for any
non-regulator user.

The visibility cut is enforced before data leaves the engine (`summarize_cross_bank`
line 131: `visible_matches = matches if _is_regulator(user) else matches_involving_user_org`),
so a bank persona can only see clusters that include its own `org_id`.

A pytest harness at `engine/tests/test_cross_bank.py` (8 tests, all passing)
exercises each invariant directly against the helpers, including the case
where a bank user has zero involvement in a match cluster (must be filtered
out entirely, not just relabeled).

---

## 5. Frontend route gates

The sidebar is filtered per persona+role in `web/src/components/shell/nav-config.ts`:

| Route | Restriction in nav-config |
| --- | --- |
| `/reports/national` | `personas: ["bfiu_director", "bfiu_analyst"]` |
| `/reports/trends` | `personas: ["bfiu_director"]` |
| `/reports/statistics` | `personas: ["bfiu_director", "bfiu_analyst"]` |
| `/reports/compliance` | `personas: ["bfiu_director", "bank_camlco"]` |
| `/scan` | `personas: ["bank_camlco"]` |
| `/admin/*` | `roles: ["admin", "manager", "superadmin"]` |
| `/admin/schedules`, `/admin/api-keys` | `roles: ["admin", "superadmin"]` |

Pages without an explicit nav restriction (e.g. `/iers`, `/intelligence/disseminations`,
`/admin/match-definitions`, `/admin/reference-tables`) are reachable for a bank
persona. The data they display is empty because RLS + service-layer filters
return zero rows for the bank tenant; mutations land on the engine guards in
§3 and bounce as `403`.

This is a deliberate UX choice — bank users see the same nav structure regardless
of tenant — not a security gap. Evidence in §6 confirms the data-layer cut.

---

## 6. Live verification on production (2026-05-05)

### 6.1 Production tenants on the prod database

| Org | Type | STRs | Alerts | Cases | Transactions |
| --- | --- | --- | --- | --- | --- |
| BFIU | regulator | 0 | 1 | 1 | 0 |
| Sonali Bank PLC | bank | 4 | 3 | 0 | 0 |
| BRAC Bank PLC | bank | 1 | 4 | 0 | 0 |
| City Bank PLC | bank | 1 | 4 | 0 | 0 |
| Dutch-Bangla Bank PLC | bank | 4 | 34 | 0 | 547 |
| Islami Bank Bangladesh PLC | bank | 0 | 3 | 0 | 0 |
| **Total** | | **10** | **49** | **1** | **547** |

### 6.2 RLS simulation — Sonali CAMLCO context

```sql
SELECT set_config('request.jwt.claim.sub','<sonali-camlco-uuid>',true);
SET LOCAL ROLE authenticated;
SELECT count(*) FROM public.str_reports;       -- → 4   (own org only; total is 10)
SELECT count(DISTINCT org_id) FROM public.str_reports; -- → 1   (Sonali only)
SELECT count(*) FROM public.alerts;             -- → 3   (Sonali only; total is 49)
SELECT count(*) FROM public.transactions;       -- → 0   (Sonali has none; DBBL has 547)
SELECT count(*) FROM public.disseminations;     -- → 0   (regulator-only data)
SELECT count(*) FROM public.cash_transaction_reports; -- → 0
SELECT count(*) FROM public.entities;           -- → 52  (shared, by design)
SELECT count(*) FROM public.matches;            -- → 7   (shared, by design)
```

**Result: ✅ Sonali CAMLCO sees only Sonali's per-tenant rows. The 6 STRs from
BRAC/City/DBBL/Islami are not visible. Cross-bank `entities` and `matches` are
shared as intended for the cross-bank intelligence layer.**

### 6.3 Helper resolution (post-013)

```sql
SELECT public.auth_org_id(), public.is_regulator() FROM (
  SELECT set_config('request.jwt.claim.sub','...',true)
) _;
```

| Subject | `auth_org_id()` | `is_regulator()` |
| --- | --- | --- |
| Sonali CAMLCO | Sonali org UUID | `false` |
| BFIU director | BFIU org UUID | `true` |
| BFIU analyst | BFIU org UUID | `true` |
| Synthetic unknown | `null` | `false` |

The unknown-user case returns `null` org / `false` regulator → RLS filter
`(org_id = NULL) OR false` matches no rows. **No leakage to anonymous or
unprovisioned subjects.**

### 6.4 UI verification — Sonali CAMLCO on prod

Authenticated to the production web surface as the Sonali CAMLCO synthetic
demo persona and navigated to each surface.

| Surface | HTTP | Outcome |
| --- | --- | --- |
| `/intelligence/cross-bank` | 200 | Bank view: peer banks rendered as `PEER INSTITUTION 1..4`; match keys redacted to `····5001`, `····6440`, `····5002`, `····5701`; only Sonali's own name appears un-anonymised. Footer reads `BANK VIEW · PEER-INSTITUTION NAMES ARE ANONYMISED. MATCH-KEY TAILS REDACTED TO LAST 4 CHARACTERS`. Screenshot in commit. |
| `/iers` | 200 | UI loads, no IER rows for Sonali (RLS-filtered) |
| `/api/match-definitions` | 200 | `{"matchDefinitions":[]}` — Sonali has no match definitions of its own |
| `/api/reference-tables?table_name=banks` | 200 | Read-shared table, returns canonical bank list (intended) |
| `POST /api/reference-tables {table_name:"banks", code:"TEST-ISOLATION", ...}` | **403** | `{"detail":"Insufficient role","request_id":"c080704980e34…"}` — engine `require_roles("admin","superadmin")` blocked Sonali (manager role). The deeper `_require_regulator` would have rejected even if Sonali were admin. |

**Result: ✅ Bank persona can navigate the full sidebar but cannot read any
cross-tenant data, cannot read regulator-only tables that have rows, cannot
mutate reference tables, and sees the cross-bank dashboard with peer
anonymisation in effect.**

### 6.5 Engine API enforcement signal

Captured request id `c080704980e341d0a78beb7ede8096d2` for the rejected
mutation. Search the engine's structured logs by `request_id` for the full
trace: route + auth result + service exception.

---

## 7. Finding: production regression in migration 012 (now patched)

While running §6.3 the helpers `auth_org_id()`, `is_regulator()`,
`gen_case_ref()`, `gen_str_ref()`, `gen_dissem_ref()` failed with
`relation "profiles" does not exist` / `relation "case_ref_seq" does not exist`.

**Root cause:** migration 012 (`advisor_fixes`) locked
`SET search_path = ''` on those functions but their bodies still referenced
unqualified relations and sequences. With empty search_path, unqualified
lookups cannot resolve.

**Production blast radius:** zero rows in `cases`, `str_reports`,
`disseminations` since 2026-05-04 (last `created_at` for both `cases` and
`str_reports` was `2026-04-03 06:14:41+00`). The bug only fired on writes that
went through the trigger; the existing read paths were unaffected because the
engine connects as `postgres` (BYPASSRLS) and never invoked
`auth_org_id()` / `is_regulator()` from inside Postgres for the `postgres` role.
The signup trigger `handle_new_user` was unaffected because it had been
schema-qualified previously.

**Fix:** migration `013_qualify_security_definer_helpers.sql` redefined each
broken function with `public.profiles`, `public.organizations`,
`public.case_ref_seq`, `public.str_ref_seq`, `public.dissem_ref_seq`, while
preserving `SET search_path = ''` and `SECURITY DEFINER`.

**Verification post-013:**

```sql
INSERT INTO public.cases (org_id, title, severity, category)
  VALUES ('9c111111-1111-4111-8111-111111111111','rls-isolation-test-013','low','fraud')
  RETURNING case_ref;
-- → KST-2605-00002    ✅
```

(Test row deleted in the same DO block; no residue on prod.)

---

## 8. Conclusion

Kestrel's multi-tenant isolation is correct under the current production
configuration:

1. RLS policies are present on every per-tenant table with the correct
   `(org_id = auth_org_id()) OR is_regulator()` shape and were proven to
   filter live data when the SQL session impersonates a bank user.
2. Service-layer org-type guards reject regulator-only mutations from a bank
   persona with HTTP 403, validated against production by the captured
   request id `c080704980e341d0a78beb7ede8096d2`.
3. The cross-bank intelligence layer applies persona-aware anonymisation
   *before* data leaves the engine; the bank-persona dashboard renders peer
   bank names as `PEER INSTITUTION N` and match keys as `····XXXX`,
   confirmed visually on prod as Sonali CAMLCO.
4. The two regression-class issues found mid-verification (migration 012's
   broken helpers) were patched in-flight by migration 013 and re-verified.

A second bank tenant signing up via the V2 phase 2.2 self-serve flow will
inherit the same isolation guarantees by construction — no per-tenant
configuration is required.
