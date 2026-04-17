# Sovereign Ledger — continuity prompt

Use this to resume the Kestrel UI rebrand in a fresh conversation. It carries only the context the next session actually needs; everything else is in memory files and CLAUDE.md.

---

## Where we are

Kestrel's full UI rebrand — **Sovereign Ledger** (institutional brutalism, regulator-grade posture, originally directed by Gemini 3.1) — is 9 commits in on `feature/sovereign-ledger`, ahead of `main`. Every public + platform surface has been converted. Production (`main` / `kestrel-nine.vercel.app`) still renders the previous teal/navy design; the rebrand is live only on the preview URL.

**Preview (Vercel SSO-protected, user-only):**
`https://kestrel-git-feature-sovereign-ledger-enso-intelligence.vercel.app`

**Branch:** `feature/sovereign-ledger`
**Base:** `main`
**Commits ahead:** 9 (run `git log feature/sovereign-ledger ^main --oneline` to list)

## What's converted

Everything. Auth (login/register/forgot), shell (sidebar + topbar + `KestrelMark`), overview (all 3 personas), investigate (omnisearch, catalogue grid, entity dossier, React Flow network), alerts (queue, card, detail, AI explanation, rule-trace), cases (board, workspace, kanban, proposal decision, notes, export, RFI), STRs (list, workspace for all 11 report types, supplement flow, XML import/export), intelligence (matches, typologies, saved queries, new subject, match-definitions, diagram builder with React Flow), disseminations (ledger + workspace + modal), IERs (list, new, workspace with respond/close), scan (workbench, upload, config, progress, results, flagged-account card, history), reports (national, compliance, trends, statistics — Recharts retheming complete), admin (team, rules, synthetic backfill, 7-tab reference tables, schedules).

## Design system

Canonical doc: `.claude/skills/kestrel-design/SKILL.md` — read first.

- Tokens scoped under `.platform-surface` in `web/src/app/globals.css`: bg `#0F1115`, foreground `#EAE6DA`, accent/destructive `#FF3823` (alarm only), card `#15171C`, border at 10% bone, `--radius: 0`.
- Fonts: IBM Plex Sans (humanist body) + IBM Plex Mono (data signature) via `next/font/google` in root layout.
- Signature glyph: registration crosshair `┼` in vermillion, present on every eyebrow and active nav row.
- Patterns: `<section className="border border-border">` frames with `font-mono text-[10px] uppercase tracking-[0.28em] text-muted-foreground` eyebrows. Three-tone status (muted / foreground / accent) everywhere. Inverted-on-active mono tab strips replace rounded pills. Mono tabular-nums for amounts, mono uppercase for timestamps, `··` middle ellipsis for IDs.
- `KestrelMark` component (`web/src/components/common/kestrel-mark.tsx`) is the single source of truth for the brand mark — placeholder is `┼ KESTREL`, swap the glyph span for the real SVG when it lands.

## What blocks shipping to production

Merging `feature/sovereign-ledger` into `main` triggers a Vercel production rebuild. Before merging:

1. **Apply `supabase/migrations/010_access_requests.sql` to prod Supabase** (`bmlyqlkzeuoglyvfythg`). The landing's intake form writes here via a service-role client. Migration is committed on the branch.
2. **Set `SUPABASE_SERVICE_ROLE_KEY` on the Vercel web project env** (it already exists on the Render engine, but not on the web project). Without it, the form falls through to "Clearance channel offline. Contact the platform operator directly." — which renders clean but doesn't write.

Once both are done, merge to main. Vercel pushes to production in ~60s. Main persists on `kestrel-nine.vercel.app`; the preview alias on `kestrel-git-feature-sovereign-ledger-enso-intelligence.vercel.app` can be dropped.

## Phase 6 — pending polish (opportunistic, not blocking)

1. Lighthouse pass: ≥ 95 public, ≥ 90 in-app.
2. a11y audit — keyboard focus, contrast, `prefers-reduced-motion`, icon-only button `aria-label`s.
3. Mobile breakpoint pass (currently desktop-optimised; tablet + phone touch-ups likely needed).
4. Real Sovereign Ledger screenshots against prod engine data — replace the SVG mocks in `web/src/components/public/product-mocks.tsx` and refresh shots in `docs/goaml-coverage.md`.
5. Update `.claude/skills/kestrel-design/SKILL.md` with the final Section / Field / Meta helper patterns and the locked Recharts palette.

## Known minor issues not worth fixing mid-stream

- Sidebar operator footer can crop on very short viewports (it's outside the scroll area). Fixable with a proper overflow-y layout on the sidebar. Low priority.
- Some scan / statistics pages in dev hit engine errors because localhost isn't signed into Supabase — behaviour is graceful (EmptyState renders). Doesn't affect the preview deploy, which talks to prod engine.

## Commands you'll want

```bash
# Verify branch state
cd "J:/Enso Intelligence/Kestrel"
git log feature/sovereign-ledger ^main --oneline
git status

# Run the web build locally (catches type regressions fast)
cd web
npm run build

# Vercel preview URL (auto-updates on push)
# https://kestrel-git-feature-sovereign-ledger-enso-intelligence.vercel.app
```

## If asked to add new UI work on the branch

Follow the brutalist pattern already established across all 56 components:
- Section frame with `┼` vermillion eyebrow in mono + uppercase + tracking-[0.28em] muted-foreground.
- Humanist title in Plex Sans + muted-foreground description underneath.
- Hairline border dividers replace Card shadows.
- Mono tabular-nums for data, mono uppercase for codes/timestamps, humanist for narrative.
- No rounded corners, no gradients, no colored badges beyond muted/foreground/accent.
- Error rows are the `<span>┼</span> ERROR · {detail}` mono pattern.
- Every page-level component uses `Section` / `Field` / `Meta` shaped helpers (already local to most files — follow the existing conventions per folder).

The kestrel-design skill has the full rule set.

## If asked to continue any specific phase

Phase 1 → 5 are complete. Phase 6 polish is the next natural work.

If the user wants to merge the rebrand to production now, the exact sequence is:
1. In Supabase dashboard, open SQL editor for project `bmlyqlkzeuoglyvfythg` and run the contents of `supabase/migrations/010_access_requests.sql`.
2. In Vercel web project settings (`prj_8eh14cqX1GAOQVnY00PDznEh3Afo`), add env var `SUPABASE_SERVICE_ROLE_KEY` (value matches the Render engine's copy). Redeploy triggered automatically.
3. Locally: `git checkout main && git merge --no-ff feature/sovereign-ledger` (preserve the phase history) and `git push origin main`.
4. Watch Vercel deploy on `kestrel-nine.vercel.app` — ~60s build.
5. Verify by browsing the landing + signing in as a demo persona and walking `/overview` → `/alerts/[id]` → `/cases/[id]` → `/reports/statistics`.
