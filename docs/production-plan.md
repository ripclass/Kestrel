# Kestrel Production Master Plan

## Summary

Kestrel will be built as a standalone financial-crime intelligence platform, not as a goAML-dependent extension. The current `Vercel + Render + Supabase` stack remains the production stack for now, and AI is a first-class subsystem across every core workflow.

Locked decisions:

- First production milestone: `dual-core`
  Bank and regulator workflows must both be real in the first shippable version so cross-bank intelligence is proven end to end.
- AI provider strategy: `task-routed`
  Kestrel will use an internal provider abstraction and route tasks between OpenAI and Claude by task type, with fallback rules and evaluation per task.
- External AI data policy: `redact by default`
  Production AI calls send masked or minimized content unless a specific task is explicitly approved for full-text provider access.
- goAML: `optional interoperability only`
  Native STR lifecycle is core product scope. goAML support is a later adapter, not a dependency.

## Implementation Plan

### Phase 1: Infrastructure Baseline

- Finish production wiring for `web`, `engine`, worker, Redis, and Supabase.
- Apply `supabase/migrations/001_schema.sql`, provision buckets, confirm RLS behavior, and complete env/secrets for Vercel, Render, and GitHub Actions.
- Add explicit health/readiness endpoints for API, worker heartbeat, storage access, and provider reachability.
- Remove any production path that silently falls back to demo mode once real envs present.
- Exit criteria:
  Live Vercel frontend, live Render API, live Render worker, live Redis, live Supabase, green CI, and environment parity documented.

### Phase 2: AI Platform Baseline

- Add an internal AI subsystem in `engine` with:
  - provider interface
  - OpenAI adapter
  - Anthropic adapter
  - model routing policy
  - prompt registry with versioning
  - structured output contracts
  - invocation audit log
  - evaluation harness
- All AI calls go through backend-only services. No direct provider calls from `web`.
- Implement redaction/minimization before provider submission for default production tasks.
- Add AI task classes for:
  - entity extraction
  - STR narrative drafting
  - alert explanation expansion
  - case summarization
  - typology suggestion
  - executive briefing generation

### Phase 3: Real Auth and Tenancy

- Replace demo fallback with real Supabase Auth sessions, profile lookup, role/persona resolution, and org-aware gating in both `web` and `engine`.
- Keep demo mode only as an explicit non-production feature flag, not an implicit “missing env” fallback once real auth configuration is introduced.
- Ensure backend JWT parsing matches Supabase token shape and applies RLS context consistently per request.

### Phase 4: Native STR Intake and Lifecycle

- Build real STR creation, draft editing, enrichment, review, assignment, submission, status changes, and audit history.
- Treat `str_reports` as a first-class product module with native Kestrel workflows.
- Add AI assistance for missing-field prompts, narrative drafting, subject/entity extraction, and suggested category/severity.

### Phase 5: Investigation Core

- Replace fixture-backed investigate flows with real DB-backed services for universal search, entity dossier, reporting history, linked STRs, linked cases/alerts, graph export, and cross-bank matches.
- Implement resolver, matcher, and graph services against live data instead of seeded fixtures.

### Phase 6: Alerts and Cases

- Replace demo alerts/cases with persisted workflows for triage, assignment, escalation, resolution, and case linkage.
- Implement case notes, case timeline, evidence linking, and alert-to-case transitions.

### Phase 7: Scan Pipeline and Draft Generation

- Implement file upload to Supabase Storage, run creation, queueing in Redis/Celery, parsing, scoring, alert creation, and persisted results.
- Build real scan history, run detail, and flagged account result pages.

### Phase 8: Reports and Command View

- Replace demo command dashboards and reports with live metrics, compliance scoring, trend analysis, export generation, and AI-generated briefings.

### Phase 9: Admin and Optional External Integrations

- Implement real team management, role/persona assignment, rule configuration, API key management, and integration settings.
- Implement goAML as an optional adapter boundary only.

### Phase 10: Production Hardening

- Add observability, structured logs, failure classification, runbooks, backup checks, security review, AI evaluation, red-team cases, release controls, and rollback documentation.

## Important Interfaces and Public Contract Changes

- Add an internal `LLMProvider` interface in `engine` with provider-agnostic request/response contracts.
- Add `AITask` services for extraction, drafting, summarization, explanation, typology, and briefing flows.
- Expand backend APIs to support real STR workflows while keeping the existing route surface stable where possible.
- Add provider configuration and policy surfaces in admin for enabled providers, task routing, and full-text approval policy.

## Test Plan

- Infrastructure tests for env completeness, health endpoints, storage connectivity, Redis connectivity, worker heartbeat, and deploy success.
- Auth/RLS tests for bank isolation, regulator scope, and role/persona enforcement.
- Workflow tests for STRs, investigation, alerts/cases, scans, reports, and AI output validation.
- Integration tests for end-to-end bank flow, regulator flow, and dual-core cross-bank scenarios.

## Assumptions and Defaults

- The current stack stays in place for production now: Vercel, Render, Supabase, Redis, OpenAI, and Claude.
- AI is mandatory in the product, but always mediated by Kestrel’s backend and internal abstractions.
- Default external AI policy is redaction/minimization first.
- Demo mode remains available only as an explicit environment-controlled mode for demos and as a fallback only when no real auth envs exist at all.
