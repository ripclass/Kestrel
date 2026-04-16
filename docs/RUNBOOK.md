# Kestrel Runbook

Operational guide for diagnosing and fixing common incidents. Production URLs:

- Web: `https://kestrel-nine.vercel.app`
- Engine: `https://kestrel-engine.onrender.com` — unauthenticated `/health` + `/ready`
- Render services: engine `srv-d7757oidbo4c73e98tlg` (Singapore), worker `srv-d7760cuuk2gs73as3oeg`
- Supabase project: `bmlyqlkzeuoglyvfythg` (ap-southeast-1)

## Table of contents

1. [Engine returns 500 / Render deploy failed](#engine-returns-500--render-deploy-failed)
2. [Engine up but `/ready` says `not_ready`](#engine-up-but-ready-says-not_ready)
3. [Web returns 401 on every request](#web-returns-401-on-every-request)
4. [Web SSR crashes during engine restart](#web-ssr-crashes-during-engine-restart)
5. [DB migration failed mid-way](#db-migration-failed-mid-way)
6. [Scan upload hangs or 504s](#scan-upload-hangs-or-504s)
7. [AI endpoint returns 502](#ai-endpoint-returns-502)
8. [PDF export returns 503](#pdf-export-returns-503)
9. [A single request needs to be traced](#a-single-request-needs-to-be-traced)

---

## Engine returns 500 / Render deploy failed

**Symptoms:** `/health` or `/ready` returns 5xx. Playwright flows fail immediately.

**Diagnose:**

```bash
render deploys list srv-d7757oidbo4c73e98tlg 2>&1 | head -5
render logs --resources srv-d7757oidbo4c73e98tlg --limit 80 -o text | tail -60
```

**Common causes:**

- `ModuleNotFoundError` — a package in an `import` statement isn't declared in `engine/pyproject.toml`. Fix by adding it and pushing. (See memory: `feedback_python_import_verification.md`.)
- `Update Failed` status on a deploy but no traceback — the start command failed its health check. The container started but never bound to `$PORT`.
- Previous deploy is still `Live` — that's fine, rollback is automatic on boot failure.

**Fix:** push a new commit that corrects the import/config. Render auto-deploys. To manually retry the last push, use the Render dashboard (no CLI retry command exists).

---

## Engine up but `/ready` says `not_ready`

Each check in the readiness probe surfaces a `status` and `detail`. Map to action:

- **`auth = error`** → Supabase env vars missing or wrong project. Check `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_ROLE_KEY` in Render env.
- **`database = error`** → `DATABASE_URL` misconfigured or Supabase pool exhausted. Check Supabase dashboard for connection count.
- **`redis = error`** → `REDIS_URL` wrong. Celery worker cannot process tasks (though we rarely use it).
- **`storage = error`** → buckets missing. Create `kestrel-uploads` and `kestrel-exports` in Supabase Storage.
- **`worker = error`** → Celery worker not running on Render. Restart the `kestrel-worker` service. Low priority — nothing in prod currently dispatches Celery tasks.
- **`ai:openai = missing_config`** or **`ai:anthropic = missing_config`** → expected in some environments. The heuristic fallback covers it if `AI_FALLBACK_ENABLED=true`.

---

## Web returns 401 on every request

**Symptoms:** All `/api/*` calls return 401. Sometimes shows as silent fall-back to demo mode.

**Diagnose:** visit `/login` — if Supabase widget renders and accepts creds but then the platform pages still 401, the JWT isn't reaching the engine.

**Fix path:**

1. Check browser devtools: is the request to `/api/alerts` sending an `Authorization: Bearer ...` header? If not, the web-side session is stale. Clear the `sb-bmlyqlkzeuoglyvfythg-auth-token.*` cookies and log in again.
2. Check engine logs: if requests hit the engine with no `Authorization` header, Vercel env is missing `ENGINE_URL` or `NEXT_PUBLIC_ENGINE_URL`.
3. Check that engine's `SUPABASE_JWT_SECRET` matches the Supabase project's JWT secret (rotations will break this silently).

---

## Web SSR crashes during engine restart

**Symptoms:** After pushing to `main`, the web app returns 500 on SSR pages for ~1–2 minutes, even though Vercel shows the build as successful.

**Cause:** Render is draining the old engine and booting the new one. SSR pages call the engine at request time; some of those calls fail during the drain.

**Fix:** wait. After `render logs` shows `Detected service running on port 10000` the new engine is up. Reload the page.

This is not a code bug. Document it in release notes if it's user-visible.

---

## DB migration failed mid-way

**Symptoms:** After pushing a new migration, the engine starts failing queries because the schema is partially applied.

**Context:** Kestrel does NOT run migrations automatically on deploy. Migrations in `supabase/migrations/` are applied manually via the Supabase MCP (`apply_migration`) or Supabase SQL editor.

**Fix path:**

1. Read the current schema state:
   ```sql
   SELECT migration_name FROM supabase_migrations.schema_migrations ORDER BY version DESC LIMIT 10;
   ```
2. Compare to `supabase/migrations/` — find the gap.
3. Re-apply the missing migration via MCP or the SQL editor. Most migrations are idempotent (`CREATE TABLE IF NOT EXISTS`, etc.), but check before running.
4. If a partial migration left the DB in a broken state, write a fix-forward migration rather than trying to roll back. The production DB has live data you cannot drop.

---

## Scan upload hangs or 504s

**Symptoms:** `POST /scan/runs/upload` times out or returns 504. The UI shows a stuck "Running scan..." state.

**Diagnose:**

```bash
render logs --resources srv-d7757oidbo4c73e98tlg --limit 40 -o text | grep -i "pipeline.scan"
```

Look for `pipeline.scan.start` without a matching `pipeline.scan.complete`.

**Common causes:**

- **CSV too large** — parses synchronously. The pipeline evaluates every account with every rule. Above ~10k transactions you'll start hitting Render's default 30-second HTTP timeout. Fix: chunk the upload, or move execution to a Celery task (Task 3 follow-up — not yet done).
- **Malformed row** — pipeline raises `HTTPException(400)`. The response should include the row number. If it doesn't, check engine logs for the full traceback.
- **Storage outage** — the upload helper swallows `StorageError` so the scan still runs, but expect `file_url=null` on that run.

---

## AI endpoint returns 502

**Symptoms:** `POST /ai/alerts/{id}/explanation` or similar returns 502 Bad Gateway with `{"detail": "..."}`.

**Cause:** The AI orchestrator tried every configured provider and all failed. If only OpenAI is configured and it's down, the request fails. If `AI_FALLBACK_ENABLED=true`, the heuristic fallback returns structured output so the endpoint should not 502 — if it does, the fallback is disabled or the prompt schema validation is failing.

**Fix path:**

1. Check `AI_FALLBACK_ENABLED` env on Render. Set to `true` if missing.
2. Check the request_id in the error response. Grep engine logs:
   ```bash
   render logs --resources srv-d7757oidbo4c73e98tlg --limit 200 -o text | grep <request_id>
   ```
3. If the provider is genuinely down (OpenAI 503), the heuristic fallback should kick in. If it doesn't, look for `AIInvocationError` in the logs.

---

## PDF export returns 503

**Symptoms:** `GET /cases/{id}/export.pdf` returns 503 with `"PDF generation is unavailable on this host — WeasyPrint could not be imported."`

**Cause:** WeasyPrint's native deps (Cairo, Pango, GDK-PixBuf) aren't on the container.

**Fix:** Render's default Python image has these deps — if they've disappeared after a platform update, set a custom `buildCommand` in `engine/render.yaml` that apt-installs them:

```yaml
buildCommand: apt-get update && apt-get install -y libcairo2 libpango-1.0-0 libpangoft2-1.0-0 libgdk-pixbuf2.0-0 && pip install -e .
```

Push and redeploy.

---

## A single request needs to be traced

Every response carries an `X-Request-ID` header. Every engine log line includes the same `request_id`.

**From a failed UI request:**

1. Browser devtools → Network tab → click the failed request → Response Headers → copy `X-Request-ID`.
2. Grep engine logs:
   ```bash
   render logs --resources srv-d7757oidbo4c73e98tlg --limit 500 -o text | grep <request_id>
   ```

You'll see every line the request produced: the `request` access log line, any service-level log points (`pipeline.scan.start`, `pipeline.str.complete`, etc.), and the error line if it failed.

**From an error response body:** the JSON body includes `"request_id"` and `"timestamp"` alongside `"detail"`. Same grep.

If the web surface returned a 500 but the engine has no logs for that request_id, the error is in Next.js (Vercel), not the engine — check Vercel deployment logs.
