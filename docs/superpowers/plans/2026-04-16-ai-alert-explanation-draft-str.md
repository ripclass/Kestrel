# AI Alert Explanation Auto-Call + Draft STR from Alert

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** When a user opens an alert detail page, automatically fetch and display an AI-generated explanation. Add a "Draft STR" button that generates a narrative via AI and creates a draft STR in one click.

**Architecture:** All engine endpoints already exist (`POST /ai/alerts/{id}/explanation`, `POST /ai/str-narrative`, `POST /str-reports`). This plan is 100% web-side: two new proxy routes, one new component, and modifications to the existing `AlertDetail` component. The AI explanation fires as a side-effect on page load and degrades gracefully when the AI provider is unavailable. The Draft STR flow chains two API calls (generate narrative → create STR) behind a single button click.

**Tech Stack:** Next.js 16 App Router, React 19, TypeScript 5, existing shadcn UI components, existing `proxyEngineRequest` pattern.

---

## File Map

| Action | Path | Responsibility |
|--------|------|----------------|
| Create | `web/src/app/api/ai/alerts/[id]/explanation/route.ts` | Proxy `POST` to engine `/ai/alerts/{id}/explanation` |
| Create | `web/src/app/api/ai/str-narrative/route.ts` | Proxy `POST` to engine `/ai/str-narrative`, camelCase→snake_case |
| Create | `web/src/components/alerts/ai-explanation.tsx` | Renders AI explanation result (summary, why_it_matters, actions) |
| Modify | `web/src/types/domain.ts` | Add `AiExplanation` interface |
| Modify | `web/src/types/api.ts` | Add `AiExplanationResponse`, `AiStrNarrativePayload`, `AiStrNarrativeResponse` |
| Modify | `web/src/components/alerts/alert-detail.tsx` | Auto-fetch AI explanation on load; add Draft STR button + flow |

No engine changes. No schema migrations. No new dependencies.

---

### Task 1: Add AI types to the web type system

**Files:**
- Modify: `web/src/types/domain.ts`
- Modify: `web/src/types/api.ts`

- [ ] **Step 1: Add `AiExplanation` to `domain.ts`**

Add after the `AlertDetail` interface (line ~163):

```typescript
export interface AiExplanation {
  summary: string;
  whyItMatters: string;
  recommendedActions: string[];
}
```

- [ ] **Step 2: Add API types to `api.ts`**

Add at the end of the file:

```typescript
export interface AiExplanationResponse {
  meta: {
    task: string;
    provider: string;
    model: string;
    fallbackUsed: boolean;
  };
  result: {
    summary: string;
    whyItMatters: string;
    recommendedActions: string[];
  };
}

export interface AiStrNarrativePayload {
  subjectName?: string;
  subjectAccount?: string;
  totalAmount?: number;
  category?: string;
  triggerFacts: string[];
}

export interface AiStrNarrativeResponse {
  meta: {
    task: string;
    provider: string;
    model: string;
    fallbackUsed: boolean;
  };
  result: {
    narrative: string;
    missingFields: string[];
    categorySuggestion: string;
    severitySuggestion: string;
  };
}
```

- [ ] **Step 3: Commit**

```bash
git add web/src/types/domain.ts web/src/types/api.ts
git commit -m "feat(web): add AI explanation and STR narrative types"
```

---

### Task 2: Create AI alert explanation proxy route

**Files:**
- Create: `web/src/app/api/ai/alerts/[id]/explanation/route.ts`

- [ ] **Step 1: Create the proxy route**

```typescript
import { NextResponse } from "next/server";

import { proxyEngineRequest } from "@/lib/engine-server";
import { readResponsePayload } from "@/lib/http";

type RouteContext = {
  params: Promise<{ id: string }>;
};

export async function POST(_request: Request, { params }: RouteContext) {
  const { id } = await params;
  const response = await proxyEngineRequest(`/ai/alerts/${id}/explanation`, {
    method: "POST",
  });
  const payload = await readResponsePayload<unknown>(response);

  if (!response.ok) {
    return NextResponse.json(payload, { status: response.status });
  }

  const envelope = payload as {
    meta: Record<string, unknown>;
    result: { summary: string; why_it_matters: string; recommended_actions: string[] };
  };

  return NextResponse.json({
    meta: {
      task: envelope.meta.task,
      provider: envelope.meta.provider,
      model: envelope.meta.model,
      fallbackUsed: envelope.meta.fallback_used,
    },
    result: {
      summary: envelope.result.summary,
      whyItMatters: envelope.result.why_it_matters,
      recommendedActions: envelope.result.recommended_actions,
    },
  });
}
```

Key decisions:
- `POST` not `GET` — the engine endpoint is POST (it may trigger AI provider calls and audit logging).
- No request body needed — the engine fetches the alert internally by `alert_id`.
- Normalizes `snake_case` response fields to `camelCase` inline (follows codebase pattern — each proxy route normalizes its own response).
- Only surfaces the `meta` fields the UI needs (task, provider, model, fallbackUsed), not the full audit chain.

- [ ] **Step 2: Commit**

```bash
git add web/src/app/api/ai/alerts/[id]/explanation/route.ts
git commit -m "feat(web): add AI alert explanation proxy route"
```

---

### Task 3: Create AI STR narrative proxy route

**Files:**
- Create: `web/src/app/api/ai/str-narrative/route.ts`

- [ ] **Step 1: Create the proxy route**

```typescript
import { NextRequest, NextResponse } from "next/server";

import { proxyEngineRequest } from "@/lib/engine-server";
import { readResponsePayload } from "@/lib/http";

export async function POST(request: NextRequest) {
  const body = await request.json();

  const response = await proxyEngineRequest("/ai/str-narrative", {
    method: "POST",
    body: JSON.stringify({
      subject_name: body.subjectName ?? null,
      subject_account: body.subjectAccount ?? null,
      total_amount: body.totalAmount ?? null,
      category: body.category ?? null,
      trigger_facts: body.triggerFacts ?? [],
    }),
  });
  const payload = await readResponsePayload<unknown>(response);

  if (!response.ok) {
    return NextResponse.json(payload, { status: response.status });
  }

  const envelope = payload as {
    meta: Record<string, unknown>;
    result: {
      narrative: string;
      missing_fields: string[];
      category_suggestion: string;
      severity_suggestion: string;
    };
  };

  return NextResponse.json({
    meta: {
      task: envelope.meta.task,
      provider: envelope.meta.provider,
      model: envelope.meta.model,
      fallbackUsed: envelope.meta.fallback_used,
    },
    result: {
      narrative: envelope.result.narrative,
      missingFields: envelope.result.missing_fields,
      categorySuggestion: envelope.result.category_suggestion,
      severitySuggestion: envelope.result.severity_suggestion,
    },
  });
}
```

- [ ] **Step 2: Commit**

```bash
git add web/src/app/api/ai/str-narrative/route.ts
git commit -m "feat(web): add AI STR narrative proxy route"
```

---

### Task 4: Create the AiExplanation component

**Files:**
- Create: `web/src/components/alerts/ai-explanation.tsx`

- [ ] **Step 1: Create the component**

```tsx
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { AiExplanation as AiExplanationModel } from "@/types/domain";

export function AiExplanation({
  explanation,
  isLoading,
  error,
}: {
  explanation: AiExplanationModel | null;
  isLoading: boolean;
  error: string | null;
}) {
  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>AI Analysis</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            <span className="inline-block h-4 w-4 animate-spin rounded-full border-2 border-current border-t-transparent" />
            Generating explanation...
          </div>
        </CardContent>
      </Card>
    );
  }

  if (error || !explanation) {
    return null;
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>AI Analysis</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <div>
          <p className="text-sm font-medium">Summary</p>
          <p className="mt-1 text-sm text-muted-foreground">{explanation.summary}</p>
        </div>
        <div>
          <p className="text-sm font-medium">Why it matters</p>
          <p className="mt-1 text-sm text-muted-foreground">{explanation.whyItMatters}</p>
        </div>
        {explanation.recommendedActions.length > 0 ? (
          <div>
            <p className="text-sm font-medium">Recommended actions</p>
            <ul className="mt-1 list-disc pl-5 text-sm text-muted-foreground">
              {explanation.recommendedActions.map((action) => (
                <li key={action}>{action}</li>
              ))}
            </ul>
          </div>
        ) : null}
      </CardContent>
    </Card>
  );
}
```

Design decisions:
- Returns `null` when the AI is unavailable (error or no data) — the rule-based `Explainability` card below it is always visible, so the page degrades gracefully.
- Shows a spinner while loading — the AI call can take 2-5 seconds.
- No retry button — the page reload re-triggers the fetch. Keeps the component simple.
- Follows the existing component conventions: `Card`/`CardHeader`/`CardTitle`/`CardContent`, `text-sm text-muted-foreground`.

- [ ] **Step 2: Commit**

```bash
git add web/src/components/alerts/ai-explanation.tsx
git commit -m "feat(web): add AiExplanation display component"
```

---

### Task 5: Wire AI explanation auto-fetch and Draft STR into AlertDetail

**Files:**
- Modify: `web/src/components/alerts/alert-detail.tsx`

This is the integration task. Two additions:
1. A second `useEffect` that fetches the AI explanation when the alert loads.
2. A "Draft STR" button that chains AI narrative generation → STR creation → navigation.

- [ ] **Step 1: Add imports**

Add these imports at the top of `alert-detail.tsx`:

```typescript
import { AiExplanation } from "@/components/alerts/ai-explanation";
import type { AiExplanation as AiExplanationModel } from "@/types/domain";
import type {
  AiExplanationResponse,
  AiStrNarrativeResponse,
  STRMutationResponse,
} from "@/types/api";
```

- [ ] **Step 2: Add AI explanation state and fetch**

Inside the `AlertDetail` component function, after the existing `isLoading` state declaration (line 42), add:

```typescript
const [aiExplanation, setAiExplanation] = useState<AiExplanationModel | null>(null);
const [aiLoading, setAiLoading] = useState(false);
const [aiError, setAiError] = useState<string | null>(null);
const [strDrafting, setStrDrafting] = useState(false);
```

After the existing `useEffect` that fetches the alert (after line 63), add a second `useEffect`:

```typescript
useEffect(() => {
  if (!alert) return;
  setAiLoading(true);
  void (async () => {
    try {
      const response = await fetch(`/api/ai/alerts/${alertId}/explanation`, {
        method: "POST",
      });
      if (!response.ok) {
        setAiError("AI analysis unavailable.");
        return;
      }
      const payload = (await readResponsePayload<AiExplanationResponse>(response)) as AiExplanationResponse;
      setAiExplanation(payload.result);
    } catch {
      setAiError("AI analysis unavailable.");
    } finally {
      setAiLoading(false);
    }
  })();
  // eslint-disable-next-line react-hooks/exhaustive-deps
}, [alertId, isLoading]);
```

Key: the `useEffect` depends on `alertId` and `isLoading` (not `alert` — that's an object ref that would re-fire every render). The `if (!alert) return` guard prevents a call before the alert data loads. Once `isLoading` flips to `false` and `alert` is populated, the AI fetch fires exactly once.

- [ ] **Step 3: Add the Draft STR handler**

After the `runAction` function, add:

```typescript
async function draftStr() {
  if (!alert?.entity) return;
  setStrDrafting(true);
  setError(null);
  try {
    // Step 1: Generate narrative via AI
    const narrativeRes = await fetch("/api/ai/str-narrative", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        subjectName: alert.entity.displayName ?? alert.entity.displayValue,
        subjectAccount: alert.entity.entityType === "account" ? alert.entity.canonicalValue : undefined,
        category: alert.alertType,
        triggerFacts: alert.reasons.map((r) => r.explanation),
      }),
    });
    let narrative = "";
    let category = alert.alertType || "fraud";
    if (narrativeRes.ok) {
      const narrativePayload = (await readResponsePayload<AiStrNarrativeResponse>(
        narrativeRes,
      )) as AiStrNarrativeResponse;
      narrative = narrativePayload.result.narrative;
      category = narrativePayload.result.categorySuggestion || category;
    }

    // Step 2: Create STR draft
    const strRes = await fetch("/api/str-reports", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        subjectName: alert.entity.displayName ?? alert.entity.displayValue,
        subjectAccount: alert.entity.entityType === "account"
          ? alert.entity.canonicalValue
          : alert.entity.displayValue,
        totalAmount: alert.entity.totalExposure ?? 0,
        currency: "BDT",
        transactionCount: 0,
        category,
        channels: [],
        narrative,
        metadata: { source_alert_id: alert.id, ai_generated: true },
      }),
    });
    if (!strRes.ok) {
      const strPayload = await readResponsePayload<{ detail?: string }>(strRes);
      setError(detailFromPayload(strPayload, "Failed to create STR draft."));
      return;
    }
    const strPayload = (await readResponsePayload<STRMutationResponse>(strRes)) as STRMutationResponse;
    router.push(`/strs/${strPayload.report.id}`);
  } catch (caughtError) {
    setError(caughtError instanceof Error ? caughtError.message : "Failed to draft STR.");
  } finally {
    setStrDrafting(false);
  }
}
```

Design decisions:
- If AI narrative generation fails, the STR is still created with an empty narrative — the user can fill it in manually. This is intentional: "Draft STR" should never fail silently.
- `subjectAccount` is required by the engine. For non-account entities, we fall back to `displayValue` — the STR is a draft that the analyst will refine.
- `metadata.source_alert_id` links the STR back to the originating alert for traceability.
- `category` uses the AI suggestion if available, else falls back to the alert's `alertType`.

- [ ] **Step 4: Add the AiExplanation component and Draft STR button to the JSX**

Replace the return JSX (lines 108-144) with:

```tsx
return (
  <div className="space-y-6">
    <Card>
      <CardHeader>
        <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
          <div className="space-y-2">
            <CardTitle>{alert.title}</CardTitle>
            <p className="text-sm text-muted-foreground">{alert.description}</p>
          </div>
          <RiskScore score={alert.riskScore} severity={alert.severity} />
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="flex flex-wrap items-center gap-3 text-sm text-muted-foreground">
          <StatusBadge status={alert.status} />
          <span>{alert.orgName}</span>
          {alert.assignedTo ? <span>Assigned: {alert.assignedTo}</span> : null}
          {alert.caseId ? <Link href={`/cases/${alert.caseId}`} className="text-primary">Linked case</Link> : null}
          {alert.entity ? (
            <Link href={`/investigate/entity/${alert.entity.id}`} className="text-primary">
              Open entity dossier
            </Link>
          ) : null}
        </div>
        <AlertActions
          alert={alert}
          pendingAction={pendingAction}
          notice={notice}
          error={error}
          onAction={runAction}
        />
        {alert.entity && !alert.caseId ? (
          <Button
            type="button"
            variant="outline"
            disabled={strDrafting || pendingAction !== null}
            onClick={() => void draftStr()}
          >
            {strDrafting ? "Drafting STR..." : "Draft STR from alert"}
          </Button>
        ) : null}
      </CardContent>
    </Card>
    <AiExplanation explanation={aiExplanation} isLoading={aiLoading} error={aiError} />
    <Explainability reasons={alert.reasons} />
    <NetworkCanvas graph={alert.graph} />
  </div>
);
```

Changes from original:
- `AiExplanation` card is inserted between the header card and the rule-based `Explainability` card.
- "Draft STR from alert" button appears below `AlertActions` when the alert has a linked entity and hasn't already been promoted to a case.
- The `Button` import is already used by `AlertActions` in the same tree, but `alert-detail.tsx` doesn't import it directly. Add the import.

- [ ] **Step 5: Add the Button import**

Add to the import block:

```typescript
import { Button } from "@/components/ui/button";
```

- [ ] **Step 6: Verify the build compiles**

Run:
```bash
cd web && npm run build
```

Expected: Build succeeds with no type errors.

- [ ] **Step 7: Commit**

```bash
git add web/src/components/alerts/alert-detail.tsx
git commit -m "feat(web): auto-fetch AI explanation on alert open + Draft STR button"
```

---

### Task 6: Manual verification

This task is browser-based verification via Playwright or dev server.

- [ ] **Step 1: Start the dev server (or verify on prod after deploy)**

If testing locally:
```bash
cd web && npm run dev
```

If testing on prod: push the feature branch to main after review, then verify on `https://kestrel-nine.vercel.app`.

- [ ] **Step 2: Navigate to an alert detail page**

Open `/alerts/{id}` for one of the existing scan alerts. The page should:
1. Show the alert header card with status, risk score, actions.
2. Show the "AI Analysis" card with a spinner → then the explanation (or nothing if AI providers aren't configured and heuristic fallback isn't wired for this task).
3. Show the "Why Kestrel flagged this" card with rule-based reasons.
4. Show the network graph.

- [ ] **Step 3: Verify the Draft STR button**

On an alert that has a linked entity and no linked case:
1. Click "Draft STR from alert".
2. Button should show "Drafting STR..." while loading.
3. On success, the browser should navigate to `/strs/{new_id}`.
4. The STR detail page should show a draft with the AI-generated narrative pre-filled.

- [ ] **Step 4: Verify graceful degradation**

If AI providers are not configured:
1. The "AI Analysis" card should disappear (returns `null` on error).
2. The "Draft STR from alert" button should still work — creates the STR with an empty narrative.
3. Rule-based "Why Kestrel flagged this" card should still render normally.

---

## Notes

- **No engine changes required.** All three engine endpoints (`POST /ai/alerts/{id}/explanation`, `POST /ai/str-narrative`, `POST /str-reports`) are already implemented and tested.
- **AI provider availability.** On prod, AI providers may or may not be configured. The heuristic fallback provider generates structured responses when `AI_FALLBACK_ENABLED=true`. If neither is available, the AI endpoints return 502 and the UI degrades gracefully.
- **No caching of AI results.** The explanation is fetched fresh each time the page opens. A future enhancement could cache the result in the alert's metadata via an engine endpoint, but that's out of scope for this plan.
- **STR draft metadata.** The `source_alert_id` in the STR's metadata creates a traceable link back to the originating alert, useful for audit and the investigation graph.
