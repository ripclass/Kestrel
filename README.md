# Kestrel

Kestrel is a financial crime intelligence platform for Bangladesh. It sits on top of goAML and adds the intelligence layer that goAML does not provide: cross-entity resolution, cross-bank matching, network analysis, risk scoring, proactive alerting, and national command reporting.

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

## Current Scaffold Scope

This repository is a fresh Kestrel scaffold. The early differentiators are implemented with the most depth:

- role/persona-aware shell
- investigate search
- entity dossier
- reusable network graph
- cross-bank matches
- alert explainability

The remaining product areas are scaffolded with stable interfaces, representative UI, and demo data so they can be deepened without changing the public structure.
