# Command View Polish Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Polish the BFIU director's CommandView with three additions: a cross-bank match ticker, typology signal badges, and a lagging-banks highlight in the compliance card.

**Architecture:** All data comes from existing endpoints. One new component (`MatchTicker`), the rest are modifications to `CommandView` JSX. No engine changes.

**Tech Stack:** React 19, existing shadcn UI components, existing proxy routes.

---

## File Map

| Action | Path | Responsibility |
|--------|------|----------------|
| Create | `web/src/components/overview/match-ticker.tsx` | Fetch `/intelligence/matches`, display recent cross-bank matches as a ticker strip |
| Modify | `web/src/components/overview/command-view.tsx` | Add MatchTicker, typology spark badges, lagging banks highlight |

---

### Task 1: Create MatchTicker component

**Files:**
- Create: `web/src/components/overview/match-ticker.tsx`

Fetches `/api/intelligence/matches`, shows the most recent matches with severity badges.
Follows the same pattern as `AlertTicker`.

### Task 2: Add typology spark badges + lagging banks highlight + MatchTicker to CommandView

**Files:**
- Modify: `web/src/components/overview/command-view.tsx`

Three changes:
1. Add `<MatchTicker />` after `<AlertTicker />`
2. Add typology spark badges row after the KPI cards, derived from `dashboard.threatMap`
3. Replace the compliance card contents: top section shows lagging banks (score < 70) with warning treatment, bottom section shows top performers

### Task 3: Build verification

Run `npm run build` + `npm run lint`.
