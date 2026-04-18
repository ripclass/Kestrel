"use client";

import { useEffect, useMemo, useRef, useState } from "react";

import type { STRDraftPayload, STRMutationResponse, STRReviewPayload } from "@/types/api";
import type { STRReportDetail, Viewer } from "@/types/domain";
import { Currency } from "@/components/common/currency";
import { DisseminateAction } from "@/components/disseminations/disseminate-action";
import { StatusBadge } from "@/components/common/status-badge";
import { ExportDropdown } from "@/components/str-reports/export-dropdown";
import { SupplementAction } from "@/components/str-reports/supplement-action";
import { SupplementList } from "@/components/str-reports/supplement-list";
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

const selectClass =
  "h-11 w-full rounded-none border border-input bg-card px-4 text-sm outline-none focus:border-foreground disabled:opacity-60";

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label className="flex flex-col gap-2">
      <span className="font-mono text-[10px] uppercase tracking-[0.28em] text-muted-foreground">
        {label}
      </span>
      {children}
    </label>
  );
}

function Section({
  label,
  description,
  children,
}: {
  label: string;
  description?: string;
  children: React.ReactNode;
}) {
  return (
    <section className="border border-border">
      <div className="border-b border-border px-6 py-5">
        <p className="font-mono text-[10px] uppercase tracking-[0.28em] text-muted-foreground">
          <span aria-hidden className="mr-2 text-accent">┼</span>
          Section · {label}
        </p>
        {description ? (
          <p className="mt-2 text-sm leading-relaxed text-muted-foreground">{description}</p>
        ) : null}
      </div>
      <div className="space-y-5 p-6">{children}</div>
    </section>
  );
}

function Meta({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex flex-col gap-3 p-5">
      <span className="font-mono text-[10px] uppercase tracking-[0.28em] text-muted-foreground">
        {label}
      </span>
      {children}
    </div>
  );
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
        const payload = (await readResponsePayload<STRReportDetail>(response)) as
          | STRReportDetail
          | { detail?: string };
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
    if (!report) return false;
    return report.orgId === viewer.orgId && report.status === "draft" && viewer.role !== "viewer";
  }, [report, viewer]);

  const canReview = useMemo(() => viewer.orgType === "regulator" && !!report, [viewer, report]);
  const enrichmentAlreadyApplied = useMemo(() => {
    if (!report?.enrichment) return false;
    return (draft?.narrative ?? "").trim() === report.enrichment.draftNarrative.trim();
  }, [draft?.narrative, report?.enrichment]);

  async function saveDraft() {
    if (!draft) return;
    setPendingAction("save");
    setError(null);
    setNotice("Saving draft…");
    try {
      const response = await fetch(`/api/str-reports/${reportId}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(draft),
      });
      const payload = (await readResponsePayload<STRMutationResponse>(response)) as
        | STRMutationResponse
        | { detail?: string };
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
    setNotice("Submitting STR…");
    try {
      const response = await fetch(`/api/str-reports/${reportId}/submit`, { method: "POST" });
      const payload = (await readResponsePayload<STRMutationResponse>(response)) as
        | STRMutationResponse
        | { detail?: string };
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
    setNotice("Generating AI enrichment…");
    try {
      const response = await fetch(`/api/str-reports/${reportId}/enrich`, { method: "POST" });
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
        if (!current || !payload.report.enrichment) return current;
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
    setNotice(action === "assign" ? "Applying assignment…" : "Applying review action…");
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
      const payload = (await readResponsePayload<STRMutationResponse>(response)) as
        | STRMutationResponse
        | { detail?: string };
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
    if (!report?.enrichment) return;
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
      <section className="border border-border bg-card">
        <p className="px-6 py-10 font-mono text-xs uppercase tracking-[0.22em] text-muted-foreground">
          <span aria-hidden className="mr-2 text-accent">┼</span>Loading STR workspace…
        </p>
      </section>
    );
  }

  return (
    <div className="space-y-6">
      <section className="border border-border">
        <div className="flex flex-col gap-6 border-b border-border px-6 py-6 lg:flex-row lg:items-start lg:justify-between">
          <div className="space-y-3">
            <p className="flex items-center gap-2 font-mono text-[10px] uppercase tracking-[0.28em] text-muted-foreground">
              <span aria-hidden className="leading-none text-accent">┼</span>
              Report · {report.reportRef} · {report.reportType.toUpperCase()}
            </p>
            <h2 className="font-mono text-2xl text-foreground">{report.reportRef}</h2>
            <p className="max-w-3xl text-sm leading-relaxed text-muted-foreground">
              {report.orgName} · {report.subjectName || "Unnamed subject"} ·{" "}
              <span className="font-mono">{report.subjectAccount || "—"}</span>
            </p>
          </div>
          <div className="flex flex-col items-start gap-2 lg:items-end">
            <StatusBadge status={report.status} />
            <span className="border border-border px-3 py-1 font-mono text-[10px] uppercase tracking-[0.22em] text-muted-foreground">
              {report.category.replaceAll("_", " ")}
            </span>
          </div>
        </div>
        <div className="grid grid-cols-2 divide-x divide-y divide-border lg:grid-cols-4 lg:divide-y-0">
          <Meta label="Exposure">
            <span className="font-mono text-lg tabular-nums text-foreground">
              <Currency amount={report.totalAmount} />
            </span>
          </Meta>
          <Meta label="Transactions">
            <span className="font-mono text-lg tabular-nums text-foreground">
              {report.transactionCount}
            </span>
          </Meta>
          <Meta label="Primary channel">
            <span className="text-sm text-foreground">{report.primaryChannel || "—"}</span>
          </Meta>
          <Meta label="Last updated">
            <span className="font-mono text-[11px] uppercase tracking-[0.18em] text-foreground">
              {new Date(report.updatedAt || report.createdAt).toLocaleString()}
            </span>
          </Meta>
        </div>
        <div className="flex flex-wrap items-center gap-2 border-t border-border px-6 py-4">
          <DisseminateAction
            linkedReportId={report.id}
            defaultSubject={`Report ${report.reportRef}: ${report.subjectName ?? "subject"}\n${report.narrative ?? ""}`}
            variant="outline"
          />
          {report.reportType !== "additional_info" ? <SupplementAction parent={report} /> : null}
          <ExportDropdown
            options={[
              {
                label: "Export as goAML XML",
                href: `/api/str-reports/${report.id}/export-xml`,
                hint: "Inverse of the goAML XML import — hands off to peer FIUs.",
              },
              {
                label: "Export reports list (Excel)",
                href: "/api/str-reports/export",
                hint: "Every report visible in the current scope.",
              },
            ]}
          />
        </div>
      </section>

      <Section
        label="Draft content"
        description="Edit the STR, generate AI enrichment, and submit when the narrative is complete."
      >
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          {report.reportType !== "ier" ? (
            <Field label="Subject account">
              <Input
                disabled={!canEdit}
                value={draft.subjectAccount ?? ""}
                onChange={(event) => updateDraft("subjectAccount", event.target.value)}
              />
            </Field>
          ) : null}
          <Field label="Subject name">
            <Input
              disabled={!canEdit}
              value={draft.subjectName}
              onChange={(event) => updateDraft("subjectName", event.target.value)}
            />
          </Field>
          <Field label="Subject phone">
            <Input
              disabled={!canEdit}
              value={draft.subjectPhone}
              onChange={(event) => updateDraft("subjectPhone", event.target.value)}
            />
          </Field>
          <Field label="Subject wallet">
            <Input
              disabled={!canEdit}
              value={draft.subjectWallet}
              onChange={(event) => updateDraft("subjectWallet", event.target.value)}
            />
          </Field>
        </div>
        <div className="grid gap-4 md:grid-cols-3">
          <Field label="Category">
            <select
              disabled={!canEdit}
              className={selectClass}
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
          </Field>
          <Field label="Exposure">
            <Input
              disabled={!canEdit}
              type="number"
              value={draft.totalAmount}
              onChange={(event) => updateDraft("totalAmount", Number(event.target.value))}
            />
          </Field>
          <Field label="Transactions">
            <Input
              disabled={!canEdit}
              type="number"
              value={draft.transactionCount}
              onChange={(event) => updateDraft("transactionCount", Number(event.target.value))}
            />
          </Field>
        </div>
        <Field label="Narrative">
          <Textarea
            ref={narrativeRef}
            disabled={!canEdit}
            value={draft.narrative}
            onChange={(event) => updateDraft("narrative", event.target.value)}
          />
        </Field>

        {error ? (
          <p className="font-mono text-xs uppercase tracking-[0.18em] text-destructive">
            <span aria-hidden className="mr-2">┼</span>ERROR · {error}
          </p>
        ) : null}
        {notice ? (
          <p className="font-mono text-xs uppercase tracking-[0.18em] text-accent">
            <span aria-hidden className="mr-2">┼</span>
            {notice}
          </p>
        ) : null}

        <div className="flex flex-wrap gap-2 border-t border-border pt-4">
          {canEdit ? (
            <>
              <Button type="button" disabled={pendingAction !== null} onClick={() => void saveDraft()}>
                {pendingAction === "save" ? "Saving draft…" : "Save draft"}
              </Button>
              <Button
                type="button"
                disabled={pendingAction !== null}
                variant="secondary"
                onClick={() => void generateEnrichment()}
              >
                {pendingAction === "enrich" ? "Generating…" : "Generate enrichment"}
              </Button>
              <Button
                type="button"
                disabled={pendingAction !== null}
                variant="outline"
                onClick={() => void submitDraft()}
              >
                {pendingAction === "submit" ? "Submitting…" : "Submit STR"}
              </Button>
            </>
          ) : (
            <p className="font-mono text-[11px] uppercase tracking-[0.22em] text-muted-foreground">
              This STR is no longer editable by {viewer.orgName}. Review actions continue below if your role allows it.
            </p>
          )}
        </div>
      </Section>

      {report.reportType === "ier" ? (
        <Section
          label="Information Exchange Request"
          description="Egmont Group cooperation with a foreign FIU. Direction and counterparty are required; attach request and response narratives as the exchange progresses."
        >
          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
            <Field label="Direction">
              <select
                disabled={!canEdit}
                className={selectClass}
                value={draft.ierDirection ?? ""}
                onChange={(event) =>
                  updateDraft(
                    "ierDirection",
                    (event.target.value || undefined) as STRDraftPayload["ierDirection"],
                  )
                }
              >
                <option value="">Select direction</option>
                <option value="outbound">Outbound (BFIU requesting)</option>
                <option value="inbound">Inbound (foreign FIU requesting)</option>
              </select>
            </Field>
            <Field label="Counterparty FIU">
              <Input
                disabled={!canEdit}
                value={draft.ierCounterpartyFiu ?? ""}
                onChange={(event) => updateDraft("ierCounterpartyFiu", event.target.value)}
                placeholder="FINTRAC (Canada)"
              />
            </Field>
            <Field label="Counterparty country">
              <Input
                disabled={!canEdit}
                value={draft.ierCounterpartyCountry ?? ""}
                onChange={(event) => updateDraft("ierCounterpartyCountry", event.target.value)}
                placeholder="Canada"
              />
            </Field>
            <Field label="Egmont reference">
              <Input
                disabled={!canEdit}
                value={draft.ierEgmontRef ?? ""}
                onChange={(event) => updateDraft("ierEgmontRef", event.target.value)}
                placeholder="EG-2026-0419"
              />
            </Field>
            <Field label="Response deadline">
              <Input
                disabled={!canEdit}
                type="date"
                value={draft.ierDeadline ?? ""}
                onChange={(event) => updateDraft("ierDeadline", event.target.value)}
              />
            </Field>
          </div>
          <Field label="Request narrative">
            <Textarea
              disabled={!canEdit}
              value={draft.ierRequestNarrative ?? ""}
              onChange={(event) => updateDraft("ierRequestNarrative", event.target.value)}
              placeholder="What information is being requested and why."
            />
          </Field>
          <Field label="Response narrative">
            <Textarea
              disabled={!canEdit}
              value={draft.ierResponseNarrative ?? ""}
              onChange={(event) => updateDraft("ierResponseNarrative", event.target.value)}
              placeholder="Captured response from the counterparty FIU."
            />
          </Field>
        </Section>
      ) : null}

      {report.reportType === "tbml" ? (
        <Section
          label="Trade-based money laundering details"
          description="LC reference, HS code, and the invoice-vs-declared variance drive the automated TBML risk indicators."
        >
          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
            <Field label="LC reference">
              <Input
                disabled={!canEdit}
                value={draft.tbmlLcReference ?? ""}
                onChange={(event) => updateDraft("tbmlLcReference", event.target.value)}
                placeholder="LC-000-2026-045"
              />
            </Field>
            <Field label="HS code">
              <Input
                disabled={!canEdit}
                value={draft.tbmlHsCode ?? ""}
                onChange={(event) => updateDraft("tbmlHsCode", event.target.value)}
                placeholder="6109.10"
              />
            </Field>
            <Field label="Commodity">
              <Input
                disabled={!canEdit}
                value={draft.tbmlCommodity ?? ""}
                onChange={(event) => updateDraft("tbmlCommodity", event.target.value)}
                placeholder="Knit cotton T-shirts"
              />
            </Field>
            <Field label="Counterparty country">
              <Input
                disabled={!canEdit}
                value={draft.tbmlCounterpartyCountry ?? ""}
                onChange={(event) => updateDraft("tbmlCounterpartyCountry", event.target.value)}
                placeholder="Hong Kong SAR"
              />
            </Field>
            <Field label="Invoice value (BDT)">
              <Input
                disabled={!canEdit}
                type="number"
                value={draft.tbmlInvoiceValue ?? ""}
                onChange={(event) => updateDraft("tbmlInvoiceValue", Number(event.target.value) || undefined)}
              />
            </Field>
            <Field label="Declared value (BDT)">
              <Input
                disabled={!canEdit}
                type="number"
                value={draft.tbmlDeclaredValue ?? ""}
                onChange={(event) => updateDraft("tbmlDeclaredValue", Number(event.target.value) || undefined)}
              />
            </Field>
          </div>
        </Section>
      ) : null}

      {report.reportType === "adverse_media_str" || report.reportType === "adverse_media_sar" ? (
        <Section
          label="Adverse media provenance"
          description="Cite the publication that triggered this report so reviewers can verify the source."
        >
          <div className="grid gap-4 md:grid-cols-3">
            <Field label="Source publication">
              <Input
                disabled={!canEdit}
                value={draft.mediaSource ?? ""}
                onChange={(event) => updateDraft("mediaSource", event.target.value)}
                placeholder="The Daily Star"
              />
            </Field>
            <Field label="Source URL">
              <Input
                disabled={!canEdit}
                value={draft.mediaUrl ?? ""}
                onChange={(event) => updateDraft("mediaUrl", event.target.value)}
                placeholder="https://…"
              />
            </Field>
            <Field label="Published date">
              <Input
                disabled={!canEdit}
                type="date"
                value={draft.mediaPublishedAt ?? ""}
                onChange={(event) => updateDraft("mediaPublishedAt", event.target.value)}
              />
            </Field>
          </div>
        </Section>
      ) : null}

      {report.reportType === "additional_info" && report.supplementsReportId ? (
        <Section
          label="Supplements an earlier report"
          description="Additional Information Files inherit subject identity from their parent; edits here only affect the supplement."
        >
          <a
            href={`/strs/${report.supplementsReportId}`}
            className="inline-flex items-center gap-2 border border-border bg-card px-4 py-2 font-mono text-[11px] uppercase tracking-[0.22em] text-accent transition hover:border-foreground hover:text-foreground"
          >
            ← Open parent report
          </a>
        </Section>
      ) : null}

      {report.enrichment ? (
        <Section
          label="AI enrichment snapshot"
          description="Stored assistance remains advisory. Analysts must still approve the narrative and category before submission."
        >
          <div className="space-y-2">
            <p className="font-mono text-[10px] uppercase tracking-[0.28em] text-muted-foreground">
              Draft narrative
            </p>
            <p className="text-sm leading-relaxed text-foreground">
              {report.enrichment.draftNarrative}
            </p>
          </div>
          <div className="grid gap-5 md:grid-cols-2">
            <div className="space-y-2">
              <p className="font-mono text-[10px] uppercase tracking-[0.28em] text-muted-foreground">
                Suggested classification
              </p>
              <p className="text-sm text-foreground">
                {report.enrichment.categorySuggestion.replaceAll("_", " ")} ·{" "}
                <span className="font-mono">{report.enrichment.severitySuggestion}</span>
              </p>
            </div>
            <div className="space-y-2">
              <p className="font-mono text-[10px] uppercase tracking-[0.28em] text-muted-foreground">
                Missing fields
              </p>
              <p className="text-sm text-foreground">
                {report.enrichment.missingFields.length
                  ? report.enrichment.missingFields.join(", ")
                  : "No critical gaps detected."}
              </p>
            </div>
          </div>
          <div className="space-y-2">
            <p className="font-mono text-[10px] uppercase tracking-[0.28em] text-muted-foreground">
              Trigger facts
            </p>
            <ul className="space-y-1.5">
              {report.enrichment.triggerFacts.map((fact) => (
                <li key={fact} className="flex items-start gap-3 text-sm text-foreground">
                  <span aria-hidden className="pt-1 font-mono leading-none text-accent">┼</span>
                  <span>{fact}</span>
                </li>
              ))}
            </ul>
          </div>
          <div className="space-y-2">
            <p className="font-mono text-[10px] uppercase tracking-[0.28em] text-muted-foreground">
              Extracted entities
            </p>
            <div className="flex flex-wrap gap-2">
              {report.enrichment.extractedEntities.map((entity) => (
                <span
                  key={`${entity.entityType}-${entity.value}`}
                  className="border border-border bg-card px-3 py-1 font-mono text-[11px] uppercase tracking-[0.22em] text-muted-foreground"
                >
                  {entity.entityType}:{" "}
                  <span className="text-foreground">{entity.value}</span> (
                  {Math.round(entity.confidence * 100)}%)
                </span>
              ))}
            </div>
          </div>
          {canEdit ? (
            <div className="pt-2">
              <Button
                type="button"
                variant="ghost"
                disabled={pendingAction !== null}
                onClick={applyDraftNarrative}
              >
                {enrichmentAlreadyApplied
                  ? "AI narrative applied"
                  : applyCount > 0
                    ? "Apply again"
                    : "Apply draft narrative to editor"}
              </Button>
            </div>
          ) : null}
        </Section>
      ) : null}

      {report.reportType !== "additional_info" ? <SupplementList parentId={report.id} /> : null}

      <Section
        label="Review trail"
        description="Every transition is stored on the STR itself and mirrored to the audit log."
      >
        {report.review.statusHistory.length ? (
          <ol className="divide-y divide-border border border-border">
            {report.review.statusHistory
              .slice()
              .reverse()
              .map((event) => (
                <li
                  key={`${event.occurredAt}-${event.action}`}
                  className="space-y-2 px-4 py-3"
                >
                  <div className="flex flex-wrap items-center gap-3">
                    <span className="font-mono text-sm text-foreground">
                      {event.action.replaceAll("_", " ")}
                    </span>
                    {event.toStatus ? <StatusBadge status={event.toStatus} /> : null}
                    <span className="font-mono text-[10px] uppercase tracking-[0.22em] text-muted-foreground">
                      {new Date(event.occurredAt).toLocaleString()}
                    </span>
                  </div>
                  {event.note ? (
                    <p className="text-sm leading-relaxed text-muted-foreground">{event.note}</p>
                  ) : null}
                </li>
              ))}
          </ol>
        ) : (
          <p className="font-mono text-[11px] uppercase tracking-[0.22em] text-muted-foreground">
            No review actions recorded yet
          </p>
        )}
      </Section>

      {canReview ? (
        <Section
          label="Regulator review actions"
          description="Start review, assign, and disposition the filing without leaving the STR workspace."
        >
          <div className="grid gap-4 md:grid-cols-2">
            <Field label="Assignment user id">
              <Input
                value={assignee}
                onChange={(event) => setAssignee(event.target.value)}
                placeholder="UUID or leave blank"
              />
            </Field>
            <Field label="Review note">
              <Textarea value={reviewNote} onChange={(event) => setReviewNote(event.target.value)} />
            </Field>
          </div>
          <div className="flex flex-wrap gap-2 border-t border-border pt-4">
            <Button
              type="button"
              variant="secondary"
              disabled={pendingAction !== null}
              onClick={() => void runReview("start_review")}
            >
              {pendingAction === "review:start_review" ? "Starting…" : "Start review"}
            </Button>
            <Button
              type="button"
              variant="ghost"
              disabled={pendingAction !== null}
              onClick={() => void runReview("assign")}
            >
              {pendingAction === "review:assign" ? "Assigning…" : "Assign"}
            </Button>
            <Button
              type="button"
              variant="outline"
              disabled={pendingAction !== null}
              onClick={() => void runReview("flag")}
            >
              {pendingAction === "review:flag" ? "Flagging…" : "Flag"}
            </Button>
            <Button
              type="button"
              disabled={pendingAction !== null}
              onClick={() => void runReview("confirm")}
            >
              {pendingAction === "review:confirm" ? "Confirming…" : "Confirm"}
            </Button>
            <Button
              type="button"
              variant="destructive"
              disabled={pendingAction !== null}
              onClick={() => void runReview("dismiss")}
            >
              {pendingAction === "review:dismiss" ? "Dismissing…" : "Dismiss"}
            </Button>
          </div>
        </Section>
      ) : null}
    </div>
  );
}
