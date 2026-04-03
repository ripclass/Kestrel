# Kestrel

Kestrel is a standalone financial crime intelligence platform for Bangladesh. It can interoperate with goAML where required, but it does not depend on goAML for its core product workflows.

## Repository Layout

```text
kestrel/
|-- web/         # Next.js 16 App Router application for public, auth, and platform UX
|-- engine/      # FastAPI intelligence engine + worker scaffolding for Render
`-- supabase/    # Schema, RLS policies, and migration assets
```

## Runtime Targets

- `web/` -> Vercel
- `engine/` -> Render web service + Render worker + Render Redis
- `supabase/` -> Supabase Postgres, Auth, and Storage

## Local Setup

1. Copy `.env.example` to `.env` and fill the required values.
2. Install frontend dependencies in `web/` and Python dependencies in `engine/`.
3. Apply `supabase/migrations/001_schema.sql` to the target Supabase project.
4. Run the web app with `npm run dev` and the API with `uvicorn app.main:app --reload`.

## Production Plan

- The saved execution roadmap lives in [`docs/production-plan.md`](docs/production-plan.md).
- Phase 1 establishes production-baseline wiring, readiness checks, and explicit demo-mode semantics.

## GitHub Actions

- `.github/workflows/ci.yml` runs the branch-protection-safe checks for every PR and every push to `main`.
- `.github/workflows/vercel-prebuilt-check.yml` is a manual Vercel CLI build check for the `web/` app. It only runs when the repo secrets are configured.
- `.github/workflows/deploy-web-production.yml` deploys `web/` to Vercel on pushes to `main` that touch the frontend.
- `.github/workflows/deploy-engine-production.yml` triggers Render production deploys for the API and worker on pushes to `main` that touch `engine/` or `supabase/`.

### Optional GitHub Secrets

- `VERCEL_TOKEN`
- `VERCEL_ORG_ID`
- `VERCEL_PROJECT_ID`
- `RENDER_ENGINE_DEPLOY_HOOK_URL`
- `RENDER_WORKER_DEPLOY_HOOK_URL`

### Deployment Notes

- The Vercel production workflow uses `vercel pull`, `vercel build --prod`, and `vercel deploy --prebuilt --prod`.
- The Render production workflow expects per-service deploy hooks from the Render dashboard for the web service and worker declared in [`engine/render.yaml`](engine/render.yaml).
- If the required secrets are missing, the deployment workflows skip cleanly and leave a summary in the Actions run instead of failing.
- Demo mode should be enabled explicitly in demo-only environments with `KESTREL_ENABLE_DEMO_MODE=true` and `NEXT_PUBLIC_ENABLE_DEMO_MODE=true`.

## Current Scaffold Scope

This repository is a fresh Kestrel scaffold. The early differentiators are implemented with the most depth:

- role/persona-aware shell
- investigate search
- entity dossier
- reusable network graph
- cross-bank matches
- alert explainability

The remaining product areas are scaffolded with stable interfaces, representative UI, and demo data so they can be deepened without changing the public structure.

## Synthetic Statement Seeds

Raw bank statements should stay outside the repo. To derive sanitized synthetic fixtures from local DBBL scam statements, run:

```bash
cd engine
python -m seed.dbbl_synthetic
```

The generator reads a curated subset from `F:\New Download\Scammers' Bank statement DBBL` by default and writes only synthetic JSON outputs under [`engine/seed/generated/dbbl_synthetic`](engine/seed/generated/dbbl_synthetic).

To load those generated synthetic records into the configured Kestrel database:

```bash
cd engine
python -m seed.load_dbbl_synthetic
python -m seed.load_dbbl_synthetic --apply
```

The first command prints the load plan. The second performs the idempotent backfill into `organizations`, `accounts`, `transactions`, `entities`, `connections`, `str_reports`, `matches`, `alerts`, and lightweight `cases`.
