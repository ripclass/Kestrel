# Kestrel — resume prompt

Start the next session with this. Everything else is in `CLAUDE.md` and auto-memory.

---

Kestrel is fully shipped. Sovereign Ledger rebrand is live on `kestrel-nine.vercel.app` (merged to `main` on 2026-04-18). Engine on Render, web on Vercel, Supabase prod `bmlyqlkzeuoglyvfythg`. Full state in `CLAUDE.md`.

Check `git log main --oneline -5` and `git status` first, then ask what I want to work on. Likely candidates:

1. **Demo film production** — most important next step before first BFIU meeting.
2. **Phase 6 polish** — Lighthouse, a11y, mobile breakpoints, refresh pre-rebrand screenshots in `docs/goaml-coverage.md` with real Sovereign Ledger captures.
3. **Scheduled rule execution** — wire `run_scan_pipeline` into Celery Beat so `/admin/schedules` flips declared jobs from `not_configured` to `scheduled`.
4. **Remaining 4 `False` modifiers** in the detection evaluator (graph-lookup conditions).
5. **Real AI provider keys** on Render — prod still runs on heuristic fallback.

Ready when you are.
