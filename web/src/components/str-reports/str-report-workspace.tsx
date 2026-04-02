"use client";

import { useEffect, useMemo, useState, useTransition } from "react";

import type { STRDraftPayload, STRMutationResponse, STRReviewPayload } from "@/types/api";
import type { STRReportDetail, Viewer } from "@/types/domain";
import { Currency } from "@/components/common/currency";
import { StatusBadge } from "@/components/common/status-badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";

function toDraftPayload(report: STRReportDetail): STRDraftPayload {
  return {
    subjectName: report.subjectName ?? "",
    subjectAccount: report.subjectAccount,
    subjectBank: report.subjectBank ?? "",
    subjectPhone: report.subjectPhone ?? "",
    subjectWallet: report.subjectWallet ?? "",
    subjectNid: report.subjectNid ?? "",
    totalAmount: report.totalAmount,
    currency: report.currency,
    transactionCount: report.transactionCount,
    primaryChannel: report.primaryChannel ?? "",
    category: report.category,
    channels: report.channels,
    dateRangeStart: report.dateRangeStart ?? "",
    dateRangeEnd: report.dateRangeEnd ?? "",
    narrative: report.narrative ?? "",
    metadata: report.metadata,
  };
}

export function STRReportWorkspace({
  reportId,
  viewer,
}: {
  reportId: string;
  viewer: Viewer;
}) {
  const [report, setReport] = useState<STRReportDetail | null>(null);
  const [draft, setDraft] = useState<STRDraftPayload | null>(null);
  const [reviewNote, setReviewNote] = useState("");
  const [assignee, setAssignee] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isPending, startTransition] = useTransition();

  useEffect(() => {
    void (async () => {
      const response = await fetch(`/api/str-reports/${reportId}`, { cache: "no-store" });
      const payload = (await response.json()) as STRReportDetail | { detail?: string };
      if (!response.ok) {
        setError("detail" in payload ? (payload.detail ?? "Unable to load STR report.") : "Unable to load STR report.");
        return;
      }
      setReport(payload as STRReportDetail);
      setDraft(toDraftPayload(payload as STRReportDetail));
    })();
  }, [reportId]);

  function updateDraft<K extends keyof STRDraftPayload>(field: K, value: STRDraftPayload[K]) {
    setDraft((current) => (current ? { ...current, [field]: value } : current));
  }

  const canEdit = useMemo(() => {
    if (!report) {
      return false;
    }
    return report.orgId === viewer.orgId && report.status === "draft" && viewer.role !== "viewer";
  }, [report, viewer]);

  const canReview = useMemo(() => viewer.orgType === "regulator" && !!report, [viewer, report]);

  async function saveDraft() {
    if (!draft) {
      return;
    }
    const response = await fetch(`/api/str-reports/${reportId}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(draft),
    });
    const payload = (await response.json()) as STRMutationResponse | { detail?: string };
    if (!response.ok) {
      setError("detail" in payload ? (payload.detail ?? "Unable to save STR draft.") : "Unable to save STR draft.");
      return;
    }
    setReport((payload as STRMutationResponse).report);
    setDraft(toDraftPayload((payload as STRMutationResponse).report));
    setError(null);
  }

  async function submitDraft() {
    const response = await fetch(`/api/str-reports/${reportId}/submit`, {
      method: "POST",
    });
    const payload = (await response.json()) as STRMutationResponse | { detail?: string };
    if (!response.ok) {
      setError("detail" in payload ? (payload.detail ?? "Unable to submit STR.") : "Unable to submit STR.");
      return;
    }
    setReport((payload as STRMutationResponse).report);
    setDraft(toDraftPayload((payload as STRMutationResponse).report));
    setError(null);
  }

  async function generateEnrichment() {
    const response = await fetch(`/api/str-reports/${reportId}/enrich`, {
      method: "POST",
    });
    const payload = (await response.json()) as { report: STRReportDetail; detail?: string };
    if (!response.ok) {
      setError(payload.detail ?? "Unable to generate enrichment.");
      return;
    }
    setReport(payload.report);
    setDraft((current) => {
      if (!current || !payload.report.enrichment) {
        return current;
      }
      return {
        ...current,
        narrative: current.narrative || payload.report.enrichment.draftNarrative,
      };
    });
    setError(null);
  }

  async function runReview(action: STRReviewPayload["action"]) {
    const response = await fetch(`/api/str-reports/${reportId}/review`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        action,
        note: reviewNote || undefined,
        assignedTo: assignee || undefined,
      }),
    });
    const payload = (await response.json()) as STRMutationResponse | { detail?: string };
    if (!response.ok) {
      setError("detail" in payload ? (payload.detail ?? "Unable to apply review action.") : "Unable to apply review action.");
      return;
    }
    setReport((payload as STRMutationResponse).report);
    setDraft(toDraftPayload((payload as STRMutationResponse).report));
    setReviewNote("");
    setError(null);
  }

  if (!report || !draft) {
    return (
      <Card>
        <CardContent className="py-10 text-sm text-muted-foreground">Loading STR workspace…</CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
            <div className="space-y-2">
              <CardTitle>{report.reportRef}</CardTitle>
              <CardDescription>
                {report.orgName} · {report.subjectName || "Unnamed subject"} · {report.subjectAccount}
              </CardDescription>
            </div>
            <div className="flex flex-wrap items-center gap-3">
              <StatusBadge status={report.status} />
              <span className="text-sm text-muted-foreground">{report.category.replaceAll("_", " ")}</span>
            </div>
          </div>
        </CardHeader>
        <CardContent className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          <div>
            <p className="text-xs uppercase tracking-[0.18em] text-muted-foreground">Exposure</p>
            <p className="mt-1 text-sm font-medium">
              <Currency amount={report.totalAmount} />
            </p>
          </div>
          <div>
            <p className="text-xs uppercase tracking-[0.18em] text-muted-foreground">Transactions</p>
            <p className="mt-1 text-sm font-medium">{report.transactionCount}</p>
          </div>
          <div>
            <p className="text-xs uppercase tracking-[0.18em] text-muted-foreground">Primary channel</p>
            <p className="mt-1 text-sm font-medium">{report.primaryChannel || "Not set"}</p>
          </div>
          <div>
            <p className="text-xs uppercase tracking-[0.18em] text-muted-foreground">Last updated</p>
            <p className="mt-1 text-sm font-medium">
              {new Date(report.updatedAt || report.createdAt).toLocaleString()}
            </p>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Draft content</CardTitle>
          <CardDescription>Edit the STR, generate AI enrichment, and submit when the narrative is complete.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
            <div className="space-y-2">
              <label className="text-xs uppercase tracking-[0.18em] text-muted-foreground">Subject account</label>
              <Input
                disabled={!canEdit}
                value={draft.subjectAccount}
                onChange={(event) => updateDraft("subjectAccount", event.target.value)}
              />
            </div>
            <div className="space-y-2">
              <label className="text-xs uppercase tracking-[0.18em] text-muted-foreground">Subject name</label>
              <Input
                disabled={!canEdit}
                value={draft.subjectName}
                onChange={(event) => updateDraft("subjectName", event.target.value)}
              />
            </div>
            <div className="space-y-2">
              <label className="text-xs uppercase tracking-[0.18em] text-muted-foreground">Subject phone</label>
              <Input
                disabled={!canEdit}
                value={draft.subjectPhone}
                onChange={(event) => updateDraft("subjectPhone", event.target.value)}
              />
            </div>
            <div className="space-y-2">
              <label className="text-xs uppercase tracking-[0.18em] text-muted-foreground">Subject wallet</label>
              <Input
                disabled={!canEdit}
                value={draft.subjectWallet}
                onChange={(event) => updateDraft("subjectWallet", event.target.value)}
              />
            </div>
          </div>
          <div className="grid gap-4 md:grid-cols-3">
            <div className="space-y-2">
              <label className="text-xs uppercase tracking-[0.18em] text-muted-foreground">Category</label>
              <select
                disabled={!canEdit}
                className="h-11 w-full rounded-xl border border-input bg-background/60 px-4 text-sm outline-none focus:border-primary disabled:opacity-60"
                value={draft.category}
                onChange={(event) => updateDraft("category", event.target.value)}
              >
                <option value="fraud">Fraud</option>
                <option value="money_laundering">Money laundering</option>
                <option value="terrorist_financing">Terrorist financing</option>
                <option value="tbml">TBML</option>
                <option value="cyber_crime">Cyber crime</option>
                <option value="other">Other</option>
              </select>
            </div>
            <div className="space-y-2">
              <label className="text-xs uppercase tracking-[0.18em] text-muted-foreground">Exposure</label>
              <Input
                disabled={!canEdit}
                type="number"
                value={draft.totalAmount}
                onChange={(event) => updateDraft("totalAmount", Number(event.target.value))}
              />
            </div>
            <div className="space-y-2">
              <label className="text-xs uppercase tracking-[0.18em] text-muted-foreground">Transactions</label>
              <Input
                disabled={!canEdit}
                type="number"
                value={draft.transactionCount}
                onChange={(event) => updateDraft("transactionCount", Number(event.target.value))}
              />
            </div>
          </div>
          <div className="space-y-2">
            <label className="text-xs uppercase tracking-[0.18em] text-muted-foreground">Narrative</label>
            <Textarea
              disabled={!canEdit}
              value={draft.narrative}
              onChange={(event) => updateDraft("narrative", event.target.value)}
            />
          </div>
          {error ? <p className="text-sm text-red-300">{error}</p> : null}
          <div className="flex flex-wrap gap-3">
            {canEdit ? (
              <>
                <Button disabled={isPending} onClick={() => startTransition(() => void saveDraft())}>
                  Save draft
                </Button>
                <Button
                  disabled={isPending}
                  variant="secondary"
                  onClick={() => startTransition(() => void generateEnrichment())}
                >
                  Generate enrichment
                </Button>
                <Button disabled={isPending} variant="outline" onClick={() => startTransition(() => void submitDraft())}>
                  Submit STR
                </Button>
              </>
            ) : (
              <p className="text-sm text-muted-foreground">
                This STR is no longer editable by {viewer.orgName}. Review actions continue below if your role allows it.
              </p>
            )}
          </div>
        </CardContent>
      </Card>

      {report.enrichment ? (
        <Card>
          <CardHeader>
            <CardTitle>AI enrichment snapshot</CardTitle>
            <CardDescription>
              Stored assistance remains advisory. Analysts must still approve the narrative and category before submission.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <p className="text-sm font-medium">Draft narrative</p>
              <p className="text-sm text-muted-foreground">{report.enrichment.draftNarrative}</p>
            </div>
            <div className="grid gap-4 md:grid-cols-2">
              <div className="space-y-2">
                <p className="text-sm font-medium">Suggested classification</p>
                <p className="text-sm text-muted-foreground">
                  {report.enrichment.categorySuggestion.replaceAll("_", " ")} · {report.enrichment.severitySuggestion}
                </p>
              </div>
              <div className="space-y-2">
                <p className="text-sm font-medium">Missing fields</p>
                <p className="text-sm text-muted-foreground">
                  {report.enrichment.missingFields.length
                    ? report.enrichment.missingFields.join(", ")
                    : "No critical gaps detected."}
                </p>
              </div>
            </div>
            <div className="space-y-2">
              <p className="text-sm font-medium">Trigger facts</p>
              <ul className="space-y-1 text-sm text-muted-foreground">
                {report.enrichment.triggerFacts.map((fact) => (
                  <li key={fact}>{fact}</li>
                ))}
              </ul>
            </div>
            <div className="space-y-2">
              <p className="text-sm font-medium">Extracted entities</p>
              <div className="flex flex-wrap gap-2">
                {report.enrichment.extractedEntities.map((entity) => (
                  <span
                    key={`${entity.entityType}-${entity.value}`}
                    className="rounded-full border border-border/80 bg-background/60 px-3 py-1 text-xs text-muted-foreground"
                  >
                    {entity.entityType}: {entity.value} ({Math.round(entity.confidence * 100)}%)
                  </span>
                ))}
              </div>
            </div>
            {canEdit ? (
              <Button
                variant="ghost"
                onClick={() => updateDraft("narrative", report.enrichment?.draftNarrative ?? draft.narrative)}
              >
                Apply draft narrative to editor
              </Button>
            ) : null}
          </CardContent>
        </Card>
      ) : null}

      <Card>
        <CardHeader>
          <CardTitle>Review trail</CardTitle>
          <CardDescription>Every transition is stored on the STR itself and mirrored to the audit log.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {report.review.statusHistory.length ? (
            report.review.statusHistory
              .slice()
              .reverse()
              .map((event) => (
                <div key={`${event.occurredAt}-${event.action}`} className="rounded-xl border border-border/80 bg-background/50 p-4">
                  <div className="flex flex-wrap items-center gap-2 text-sm">
                    <span className="font-medium">{event.action.replaceAll("_", " ")}</span>
                    {event.toStatus ? <StatusBadge status={event.toStatus} /> : null}
                    <span className="text-muted-foreground">{new Date(event.occurredAt).toLocaleString()}</span>
                  </div>
                  {event.note ? <p className="mt-2 text-sm text-muted-foreground">{event.note}</p> : null}
                </div>
              ))
          ) : (
            <p className="text-sm text-muted-foreground">No review actions recorded yet.</p>
          )}
        </CardContent>
      </Card>

      {canReview ? (
        <Card>
          <CardHeader>
            <CardTitle>Regulator review actions</CardTitle>
            <CardDescription>Start review, assign, and disposition the filing without leaving the STR workspace.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid gap-4 md:grid-cols-2">
              <div className="space-y-2">
                <label className="text-xs uppercase tracking-[0.18em] text-muted-foreground">Assignment user id</label>
                <Input value={assignee} onChange={(event) => setAssignee(event.target.value)} placeholder="UUID or leave blank" />
              </div>
              <div className="space-y-2">
                <label className="text-xs uppercase tracking-[0.18em] text-muted-foreground">Review note</label>
                <Textarea value={reviewNote} onChange={(event) => setReviewNote(event.target.value)} />
              </div>
            </div>
            <div className="flex flex-wrap gap-3">
              <Button variant="secondary" disabled={isPending} onClick={() => startTransition(() => void runReview("start_review"))}>
                Start review
              </Button>
              <Button variant="ghost" disabled={isPending} onClick={() => startTransition(() => void runReview("assign"))}>
                Assign
              </Button>
              <Button variant="outline" disabled={isPending} onClick={() => startTransition(() => void runReview("flag"))}>
                Flag
              </Button>
              <Button disabled={isPending} onClick={() => startTransition(() => void runReview("confirm"))}>
                Confirm
              </Button>
              <Button variant="destructive" disabled={isPending} onClick={() => startTransition(() => void runReview("dismiss"))}>
                Dismiss
              </Button>
            </div>
          </CardContent>
        </Card>
      ) : null}
    </div>
  );
}
