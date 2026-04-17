"use client";

import { useEffect, useMemo, useRef, useState } from "react";

import type { STRDraftPayload, STRMutationResponse, STRReviewPayload } from "@/types/api";
import type { STRReportDetail, Viewer } from "@/types/domain";
import { Currency } from "@/components/common/currency";
import { StatusBadge } from "@/components/common/status-badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { detailFromPayload, readResponsePayload } from "@/lib/http";

function toDraftPayload(report: STRReportDetail): STRDraftPayload {
  return {
    reportType: report.reportType,
    subjectName: report.subjectName ?? "",
    subjectAccount: report.subjectAccount ?? "",
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
    supplementsReportId: report.supplementsReportId ?? undefined,
    mediaSource: report.mediaSource ?? "",
    mediaUrl: report.mediaUrl ?? "",
    mediaPublishedAt: report.mediaPublishedAt ?? "",
    ierDirection: report.ierDirection ?? undefined,
    ierCounterpartyFiu: report.ierCounterpartyFiu ?? "",
    ierCounterpartyCountry: report.ierCounterpartyCountry ?? "",
    ierEgmontRef: report.ierEgmontRef ?? "",
    ierRequestNarrative: report.ierRequestNarrative ?? "",
    ierResponseNarrative: report.ierResponseNarrative ?? "",
    ierDeadline: report.ierDeadline ?? "",
    tbmlInvoiceValue: report.tbmlInvoiceValue ?? undefined,
    tbmlDeclaredValue: report.tbmlDeclaredValue ?? undefined,
    tbmlLcReference: report.tbmlLcReference ?? "",
    tbmlHsCode: report.tbmlHsCode ?? "",
    tbmlCommodity: report.tbmlCommodity ?? "",
    tbmlCounterpartyCountry: report.tbmlCounterpartyCountry ?? "",
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
  const [notice, setNotice] = useState<string | null>(null);
  const [pendingAction, setPendingAction] = useState<string | null>(null);
  const [applyCount, setApplyCount] = useState(0);
  const narrativeRef = useRef<HTMLTextAreaElement | null>(null);

  useEffect(() => {
    void (async () => {
      try {
        const response = await fetch(`/api/str-reports/${reportId}`, { cache: "no-store" });
        const payload = (await readResponsePayload<STRReportDetail>(response)) as STRReportDetail | { detail?: string };
        if (!response.ok) {
          setError(detailFromPayload(payload, "Unable to load STR report."));
          return;
        }
        setReport(payload as STRReportDetail);
        setDraft(toDraftPayload(payload as STRReportDetail));
        setError(null);
      } catch (caughtError) {
        setError(caughtError instanceof Error ? caughtError.message : "Unable to load STR report.");
      }
    })();
  }, [reportId]);

  function updateDraft<K extends keyof STRDraftPayload>(field: K, value: STRDraftPayload[K]) {
    setNotice(null);
    setDraft((current) => (current ? { ...current, [field]: value } : current));
  }

  const canEdit = useMemo(() => {
    if (!report) {
      return false;
    }
    return report.orgId === viewer.orgId && report.status === "draft" && viewer.role !== "viewer";
  }, [report, viewer]);

  const canReview = useMemo(() => viewer.orgType === "regulator" && !!report, [viewer, report]);
  const enrichmentAlreadyApplied = useMemo(() => {
    if (!report?.enrichment) {
      return false;
    }
    return (draft?.narrative ?? "").trim() === report.enrichment.draftNarrative.trim();
  }, [draft?.narrative, report?.enrichment]);

  async function saveDraft() {
    if (!draft) {
      return;
    }
    setPendingAction("save");
    setError(null);
    setNotice("Saving draft...");
    try {
      const response = await fetch(`/api/str-reports/${reportId}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(draft),
      });
      const payload = (await readResponsePayload<STRMutationResponse>(response)) as STRMutationResponse | { detail?: string };
      if (!response.ok) {
        setError(detailFromPayload(payload, "Unable to save STR draft."));
        setNotice(null);
        return;
      }
      setReport((payload as STRMutationResponse).report);
      setDraft(toDraftPayload((payload as STRMutationResponse).report));
      setNotice("Draft saved.");
    } catch (caughtError) {
      setError(caughtError instanceof Error ? caughtError.message : "Unable to save STR draft.");
      setNotice(null);
    } finally {
      setPendingAction(null);
    }
  }

  async function submitDraft() {
    setPendingAction("submit");
    setError(null);
    setNotice("Submitting STR...");
    try {
      const response = await fetch(`/api/str-reports/${reportId}/submit`, {
        method: "POST",
      });
      const payload = (await readResponsePayload<STRMutationResponse>(response)) as STRMutationResponse | { detail?: string };
      if (!response.ok) {
        setError(detailFromPayload(payload, "Unable to submit STR."));
        setNotice(null);
        return;
      }
      setReport((payload as STRMutationResponse).report);
      setDraft(toDraftPayload((payload as STRMutationResponse).report));
      setNotice("STR submitted for regulator review.");
    } catch (caughtError) {
      setError(caughtError instanceof Error ? caughtError.message : "Unable to submit STR.");
      setNotice(null);
    } finally {
      setPendingAction(null);
    }
  }

  async function generateEnrichment() {
    setPendingAction("enrich");
    setError(null);
    setNotice("Generating AI enrichment...");
    try {
      const response = await fetch(`/api/str-reports/${reportId}/enrich`, {
        method: "POST",
      });
      const payload = (await readResponsePayload<{ report: STRReportDetail; detail?: string }>(response)) as {
        report: STRReportDetail;
        detail?: string;
      };
      if (!response.ok) {
        setError(detailFromPayload(payload, "Unable to generate enrichment."));
        setNotice(null);
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
      setNotice(
        payload.report.enrichment
          ? "AI enrichment is ready. Review the draft narrative below, then apply or edit it."
          : "AI enrichment completed.",
      );
    } catch (caughtError) {
      setError(caughtError instanceof Error ? caughtError.message : "Unable to generate enrichment.");
      setNotice(null);
    } finally {
      setPendingAction(null);
    }
  }

  async function runReview(action: STRReviewPayload["action"]) {
    setPendingAction(`review:${action}`);
    setError(null);
    setNotice(action === "assign" ? "Applying assignment..." : "Applying review action...");
    try {
      const response = await fetch(`/api/str-reports/${reportId}/review`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          action,
          note: reviewNote || undefined,
          assignedTo: assignee || undefined,
        }),
      });
      const payload = (await readResponsePayload<STRMutationResponse>(response)) as STRMutationResponse | { detail?: string };
      if (!response.ok) {
        setError(detailFromPayload(payload, "Unable to apply review action."));
        setNotice(null);
        return;
      }
      setReport((payload as STRMutationResponse).report);
      setDraft(toDraftPayload((payload as STRMutationResponse).report));
      setReviewNote("");
      setNotice(
        action === "start_review"
          ? "Review started."
          : action === "assign"
            ? "Assignment updated."
            : action === "flag"
              ? "STR flagged."
              : action === "confirm"
                ? "STR confirmed."
                : "STR dismissed.",
      );
    } catch (caughtError) {
      setError(caughtError instanceof Error ? caughtError.message : "Unable to apply review action.");
      setNotice(null);
    } finally {
      setPendingAction(null);
    }
  }

  function applyDraftNarrative() {
    if (!report?.enrichment) {
      return;
    }
    updateDraft("narrative", report.enrichment.draftNarrative);
    setApplyCount((current) => current + 1);
    setError(null);
    setNotice("AI draft copied into the narrative editor. Save draft to persist it.");

    requestAnimationFrame(() => {
      narrativeRef.current?.focus();
      narrativeRef.current?.setSelectionRange(0, report.enrichment?.draftNarrative.length ?? 0);
    });
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
                {report.orgName} · {report.subjectName || "Unnamed subject"} · {report.subjectAccount || "—"}
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
            {report.reportType !== "ier" ? (
              <div className="space-y-2">
                <label className="text-xs uppercase tracking-[0.18em] text-muted-foreground">Subject account</label>
                <Input
                  disabled={!canEdit}
                  value={draft.subjectAccount ?? ""}
                  onChange={(event) => updateDraft("subjectAccount", event.target.value)}
                />
              </div>
            ) : null}
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
              ref={narrativeRef}
              disabled={!canEdit}
              value={draft.narrative}
              onChange={(event) => updateDraft("narrative", event.target.value)}
            />
          </div>
          {error ? <p className="text-sm text-red-300">{error}</p> : null}
          {notice ? <p className="text-sm text-primary/80">{notice}</p> : null}
          <div className="flex flex-wrap gap-3">
            {canEdit ? (
              <>
                <Button type="button" disabled={pendingAction !== null} onClick={() => void saveDraft()}>
                  {pendingAction === "save" ? "Saving draft..." : "Save draft"}
                </Button>
                <Button
                  type="button"
                  disabled={pendingAction !== null}
                  variant="secondary"
                  onClick={() => void generateEnrichment()}
                >
                  {pendingAction === "enrich" ? "Generating..." : "Generate enrichment"}
                </Button>
                <Button type="button" disabled={pendingAction !== null} variant="outline" onClick={() => void submitDraft()}>
                  {pendingAction === "submit" ? "Submitting..." : "Submit STR"}
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

      {report.reportType === "ier" ? (
        <Card>
          <CardHeader>
            <CardTitle>Information Exchange Request</CardTitle>
            <CardDescription>
              Egmont Group cooperation with a foreign FIU. Direction and counterparty are required; attach request and response narratives as the exchange progresses.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
              <div className="space-y-2">
                <label className="text-xs uppercase tracking-[0.18em] text-muted-foreground">Direction</label>
                <select
                  disabled={!canEdit}
                  className="h-11 w-full rounded-xl border border-input bg-background/60 px-4 text-sm outline-none focus:border-primary disabled:opacity-60"
                  value={draft.ierDirection ?? ""}
                  onChange={(event) => updateDraft("ierDirection", (event.target.value || undefined) as STRDraftPayload["ierDirection"])}
                >
                  <option value="">Select direction</option>
                  <option value="outbound">Outbound (BFIU requesting)</option>
                  <option value="inbound">Inbound (foreign FIU requesting)</option>
                </select>
              </div>
              <div className="space-y-2">
                <label className="text-xs uppercase tracking-[0.18em] text-muted-foreground">Counterparty FIU</label>
                <Input
                  disabled={!canEdit}
                  value={draft.ierCounterpartyFiu ?? ""}
                  onChange={(event) => updateDraft("ierCounterpartyFiu", event.target.value)}
                  placeholder="FINTRAC (Canada)"
                />
              </div>
              <div className="space-y-2">
                <label className="text-xs uppercase tracking-[0.18em] text-muted-foreground">Counterparty country</label>
                <Input
                  disabled={!canEdit}
                  value={draft.ierCounterpartyCountry ?? ""}
                  onChange={(event) => updateDraft("ierCounterpartyCountry", event.target.value)}
                  placeholder="Canada"
                />
              </div>
              <div className="space-y-2">
                <label className="text-xs uppercase tracking-[0.18em] text-muted-foreground">Egmont reference</label>
                <Input
                  disabled={!canEdit}
                  value={draft.ierEgmontRef ?? ""}
                  onChange={(event) => updateDraft("ierEgmontRef", event.target.value)}
                  placeholder="EG-2026-0419"
                />
              </div>
              <div className="space-y-2">
                <label className="text-xs uppercase tracking-[0.18em] text-muted-foreground">Response deadline</label>
                <Input
                  disabled={!canEdit}
                  type="date"
                  value={draft.ierDeadline ?? ""}
                  onChange={(event) => updateDraft("ierDeadline", event.target.value)}
                />
              </div>
            </div>
            <div className="space-y-2">
              <label className="text-xs uppercase tracking-[0.18em] text-muted-foreground">Request narrative</label>
              <Textarea
                disabled={!canEdit}
                value={draft.ierRequestNarrative ?? ""}
                onChange={(event) => updateDraft("ierRequestNarrative", event.target.value)}
                placeholder="What information is being requested and why."
              />
            </div>
            <div className="space-y-2">
              <label className="text-xs uppercase tracking-[0.18em] text-muted-foreground">Response narrative</label>
              <Textarea
                disabled={!canEdit}
                value={draft.ierResponseNarrative ?? ""}
                onChange={(event) => updateDraft("ierResponseNarrative", event.target.value)}
                placeholder="Captured response from the counterparty FIU."
              />
            </div>
          </CardContent>
        </Card>
      ) : null}

      {report.reportType === "tbml" ? (
        <Card>
          <CardHeader>
            <CardTitle>Trade-based money laundering details</CardTitle>
            <CardDescription>
              LC reference, HS code, and the invoice-vs-declared variance drive the automated TBML risk indicators.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
              <div className="space-y-2">
                <label className="text-xs uppercase tracking-[0.18em] text-muted-foreground">LC reference</label>
                <Input
                  disabled={!canEdit}
                  value={draft.tbmlLcReference ?? ""}
                  onChange={(event) => updateDraft("tbmlLcReference", event.target.value)}
                  placeholder="LC-000-2026-045"
                />
              </div>
              <div className="space-y-2">
                <label className="text-xs uppercase tracking-[0.18em] text-muted-foreground">HS code</label>
                <Input
                  disabled={!canEdit}
                  value={draft.tbmlHsCode ?? ""}
                  onChange={(event) => updateDraft("tbmlHsCode", event.target.value)}
                  placeholder="6109.10"
                />
              </div>
              <div className="space-y-2">
                <label className="text-xs uppercase tracking-[0.18em] text-muted-foreground">Commodity</label>
                <Input
                  disabled={!canEdit}
                  value={draft.tbmlCommodity ?? ""}
                  onChange={(event) => updateDraft("tbmlCommodity", event.target.value)}
                  placeholder="Knit cotton T-shirts"
                />
              </div>
              <div className="space-y-2">
                <label className="text-xs uppercase tracking-[0.18em] text-muted-foreground">Counterparty country</label>
                <Input
                  disabled={!canEdit}
                  value={draft.tbmlCounterpartyCountry ?? ""}
                  onChange={(event) => updateDraft("tbmlCounterpartyCountry", event.target.value)}
                  placeholder="Hong Kong SAR"
                />
              </div>
              <div className="space-y-2">
                <label className="text-xs uppercase tracking-[0.18em] text-muted-foreground">Invoice value (BDT)</label>
                <Input
                  disabled={!canEdit}
                  type="number"
                  value={draft.tbmlInvoiceValue ?? ""}
                  onChange={(event) => updateDraft("tbmlInvoiceValue", Number(event.target.value) || undefined)}
                />
              </div>
              <div className="space-y-2">
                <label className="text-xs uppercase tracking-[0.18em] text-muted-foreground">Declared value (BDT)</label>
                <Input
                  disabled={!canEdit}
                  type="number"
                  value={draft.tbmlDeclaredValue ?? ""}
                  onChange={(event) => updateDraft("tbmlDeclaredValue", Number(event.target.value) || undefined)}
                />
              </div>
            </div>
          </CardContent>
        </Card>
      ) : null}

      {report.reportType === "adverse_media_str" || report.reportType === "adverse_media_sar" ? (
        <Card>
          <CardHeader>
            <CardTitle>Adverse media provenance</CardTitle>
            <CardDescription>Cite the publication that triggered this report so reviewers can verify the source.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid gap-4 md:grid-cols-3">
              <div className="space-y-2">
                <label className="text-xs uppercase tracking-[0.18em] text-muted-foreground">Source publication</label>
                <Input
                  disabled={!canEdit}
                  value={draft.mediaSource ?? ""}
                  onChange={(event) => updateDraft("mediaSource", event.target.value)}
                  placeholder="The Daily Star"
                />
              </div>
              <div className="space-y-2">
                <label className="text-xs uppercase tracking-[0.18em] text-muted-foreground">Source URL</label>
                <Input
                  disabled={!canEdit}
                  value={draft.mediaUrl ?? ""}
                  onChange={(event) => updateDraft("mediaUrl", event.target.value)}
                  placeholder="https://…"
                />
              </div>
              <div className="space-y-2">
                <label className="text-xs uppercase tracking-[0.18em] text-muted-foreground">Published date</label>
                <Input
                  disabled={!canEdit}
                  type="date"
                  value={draft.mediaPublishedAt ?? ""}
                  onChange={(event) => updateDraft("mediaPublishedAt", event.target.value)}
                />
              </div>
            </div>
          </CardContent>
        </Card>
      ) : null}

      {report.reportType === "additional_info" && report.supplementsReportId ? (
        <Card>
          <CardHeader>
            <CardTitle>Supplements an earlier report</CardTitle>
            <CardDescription>Additional Information Files inherit subject identity from their parent; edits here only affect the supplement.</CardDescription>
          </CardHeader>
          <CardContent>
            <a
              href={`/strs/${report.supplementsReportId}`}
              className="inline-flex items-center gap-2 rounded-xl border border-border/80 bg-background/60 px-4 py-2 text-sm font-medium text-primary hover:border-primary/60"
            >
              ← Open parent report
            </a>
          </CardContent>
        </Card>
      ) : null}

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
                type="button"
                variant="ghost"
                disabled={pendingAction !== null}
                onClick={applyDraftNarrative}
              >
                {enrichmentAlreadyApplied ? "AI narrative applied" : applyCount > 0 ? "Apply again" : "Apply draft narrative to editor"}
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
              <Button
                type="button"
                variant="secondary"
                disabled={pendingAction !== null}
                onClick={() => void runReview("start_review")}
              >
                {pendingAction === "review:start_review" ? "Starting..." : "Start review"}
              </Button>
              <Button type="button" variant="ghost" disabled={pendingAction !== null} onClick={() => void runReview("assign")}>
                {pendingAction === "review:assign" ? "Assigning..." : "Assign"}
              </Button>
              <Button type="button" variant="outline" disabled={pendingAction !== null} onClick={() => void runReview("flag")}>
                {pendingAction === "review:flag" ? "Flagging..." : "Flag"}
              </Button>
              <Button type="button" disabled={pendingAction !== null} onClick={() => void runReview("confirm")}>
                {pendingAction === "review:confirm" ? "Confirming..." : "Confirm"}
              </Button>
              <Button type="button" variant="destructive" disabled={pendingAction !== null} onClick={() => void runReview("dismiss")}>
                {pendingAction === "review:dismiss" ? "Dismissing..." : "Dismiss"}
              </Button>
            </div>
          </CardContent>
        </Card>
      ) : null}
    </div>
  );
}
