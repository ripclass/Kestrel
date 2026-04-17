"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import type { STRDraftPayload, STRListResponse, STRMutationResponse } from "@/types/api";
import type { STRReportSummary, Viewer } from "@/types/domain";
import { Currency } from "@/components/common/currency";
import { StatusBadge } from "@/components/common/status-badge";
import { XmlImportCard } from "@/components/str-reports/xml-import-card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { detailFromPayload, readResponsePayload } from "@/lib/http";

const emptyDraft: STRDraftPayload = {
  reportType: "str",
  subjectAccount: "",
  subjectName: "",
  subjectBank: "",
  subjectPhone: "",
  subjectWallet: "",
  subjectNid: "",
  totalAmount: 0,
  currency: "BDT",
  transactionCount: 0,
  primaryChannel: "RTGS",
  category: "fraud",
  channels: [],
  dateRangeStart: "",
  dateRangeEnd: "",
  narrative: "",
  metadata: {},
};

const REPORT_TYPES = [
  "str",
  "sar",
  "ctr",
  "tbml",
  "complaint",
  "ier",
  "internal",
  "adverse_media_str",
  "adverse_media_sar",
  "escalated",
  "additional_info",
] as const;

type ReportTypeFilter = "all" | (typeof REPORT_TYPES)[number];

const reportTypeLabel: Record<string, string> = {
  str: "STR",
  sar: "SAR",
  ctr: "CTR",
  tbml: "TBML",
  complaint: "Complaint",
  ier: "IER",
  internal: "Internal",
  adverse_media_str: "AM-STR",
  adverse_media_sar: "AM-SAR",
  escalated: "Escalated",
  additional_info: "Addl. Info",
};

const reportTypeDescription: Record<string, string> = {
  str: "STR — Suspicious Transaction",
  sar: "SAR — Suspicious Activity",
  ctr: "CTR — Cash Transaction",
  tbml: "TBML — Trade-Based Money Laundering",
  complaint: "Complaint Report",
  ier: "IER — Information Exchange Request (Egmont)",
  internal: "Internal Report",
  adverse_media_str: "Adverse Media → STR",
  adverse_media_sar: "Adverse Media → SAR",
  escalated: "FIU Escalated Report",
  additional_info: "Additional Information File",
};

// Sovereign Ledger three-tone badging. Escalated + adverse-media are alarm;
// IER + TBML are in-flight foreground; everything else is neutral.
const reportTypeTone: Record<string, string> = {
  str: "border-border text-muted-foreground",
  sar: "border-border text-muted-foreground",
  ctr: "border-border text-muted-foreground",
  tbml: "border-foreground/30 text-foreground",
  complaint: "border-foreground/30 text-foreground",
  ier: "border-foreground/30 text-foreground",
  internal: "border-border text-muted-foreground",
  adverse_media_str: "border-accent/40 text-accent",
  adverse_media_sar: "border-accent/40 text-accent",
  escalated: "border-accent/50 text-accent",
  additional_info: "border-border text-muted-foreground",
};

function canCreateDraft(draft: STRDraftPayload): boolean {
  const rt = draft.reportType ?? "str";
  if (rt === "ier") return Boolean(draft.ierDirection && draft.ierCounterpartyFiu);
  if (rt === "additional_info") return Boolean(draft.supplementsReportId);
  if (rt === "tbml") return Boolean(draft.subjectAccount && draft.tbmlCounterpartyCountry);
  if (rt === "adverse_media_str" || rt === "adverse_media_sar") {
    return Boolean(draft.subjectAccount && draft.mediaSource);
  }
  return Boolean(draft.subjectAccount);
}

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

const selectClass =
  "h-11 w-full rounded-none border border-input bg-card px-4 text-sm outline-none focus:border-foreground";

export function STRReportList({ viewer }: { viewer: Viewer }) {
  const router = useRouter();
  const [reports, setReports] = useState<STRReportSummary[]>([]);
  const [draft, setDraft] = useState<STRDraftPayload>(emptyDraft);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [isCreating, setIsCreating] = useState(false);
  const [filter, setFilter] = useState<ReportTypeFilter>("all");

  useEffect(() => {
    void (async () => {
      try {
        const url = filter === "all" ? "/api/str-reports" : `/api/str-reports?report_type=${filter}`;
        const response = await fetch(url, { cache: "no-store" });
        const payload = (await readResponsePayload<STRListResponse>(response)) as
          | STRListResponse
          | { detail?: string };
        if (!response.ok) {
          setError(detailFromPayload(payload, "Unable to load STR reports."));
          return;
        }
        setReports((payload as STRListResponse).reports);
        setError(null);
      } catch (caughtError) {
        setError(caughtError instanceof Error ? caughtError.message : "Unable to load STR reports.");
      }
    })();
  }, [filter]);

  function updateField<K extends keyof STRDraftPayload>(field: K, value: STRDraftPayload[K]) {
    setDraft((current) => ({ ...current, [field]: value }));
  }

  async function createDraft() {
    setError(null);
    setNotice("Creating STR draft…");
    setIsCreating(true);
    try {
      const response = await fetch("/api/str-reports", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ...draft, channels: draft.channels ?? [] }),
      });
      const payload = (await readResponsePayload<STRMutationResponse>(response)) as
        | STRMutationResponse
        | { detail?: string };
      if (!response.ok) {
        setError(detailFromPayload(payload, "Unable to create STR draft."));
        setNotice(null);
        return;
      }
      setNotice("Draft created. Opening workspace…");
      router.push(`/strs/${(payload as STRMutationResponse).report.id}`);
    } catch (caughtError) {
      setError(caughtError instanceof Error ? caughtError.message : "Unable to create STR draft.");
      setNotice(null);
    } finally {
      setIsCreating(false);
    }
  }

  return (
    <div className="space-y-6">
      <XmlImportCard onImported={() => setFilter((prev) => prev)} />

      <section className="border border-border">
        <div className="border-b border-border px-6 py-5">
          <p className="font-mono text-[10px] uppercase tracking-[0.28em] text-muted-foreground">
            <span aria-hidden className="mr-2 text-accent">┼</span>
            Section · Open a native STR draft
          </p>
          <p className="mt-2 text-sm leading-relaxed text-muted-foreground">
            Banks can file directly in Kestrel, enrich the narrative, then submit for regulator review.
            Regulators can also open internal drafts for imported or reconstructed intelligence.
          </p>
        </div>
        <div className="space-y-5 p-6">
          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
            <Field label="Report type">
              <select
                className={selectClass}
                value={draft.reportType ?? "str"}
                onChange={(event) => updateField("reportType", event.target.value)}
              >
                {REPORT_TYPES.map((type) => (
                  <option key={type} value={type}>
                    {reportTypeDescription[type]}
                  </option>
                ))}
              </select>
            </Field>
            {draft.reportType !== "ier" ? (
              <Field label="Subject account">
                <Input
                  value={draft.subjectAccount ?? ""}
                  onChange={(event) => updateField("subjectAccount", event.target.value)}
                  placeholder="1781430000701"
                />
              </Field>
            ) : null}
            <Field label="Subject name">
              <Input
                value={draft.subjectName}
                onChange={(event) => updateField("subjectName", event.target.value)}
                placeholder="RIZWANA ENTERPRISE"
              />
            </Field>
            <Field label="Category">
              <select
                className={selectClass}
                value={draft.category}
                onChange={(event) => updateField("category", event.target.value)}
              >
                <option value="fraud">Fraud</option>
                <option value="money_laundering">Money laundering</option>
                <option value="terrorist_financing">Terrorist financing</option>
                <option value="tbml">TBML</option>
                <option value="cyber_crime">Cyber crime</option>
                <option value="other">Other</option>
              </select>
            </Field>
            <Field label="Primary channel">
              <Input
                value={draft.primaryChannel}
                onChange={(event) => updateField("primaryChannel", event.target.value)}
                placeholder="RTGS"
              />
            </Field>
          </div>
          <div className="grid gap-4 md:grid-cols-3">
            <Field label="Exposure (BDT)">
              <Input
                inputMode="decimal"
                type="number"
                value={draft.totalAmount}
                onChange={(event) => updateField("totalAmount", Number(event.target.value))}
              />
            </Field>
            <Field label="Transactions">
              <Input
                inputMode="numeric"
                type="number"
                value={draft.transactionCount}
                onChange={(event) => updateField("transactionCount", Number(event.target.value))}
              />
            </Field>
            <Field label="Subject phone">
              <Input
                value={draft.subjectPhone}
                onChange={(event) => updateField("subjectPhone", event.target.value)}
                placeholder="017XXXXXXXX"
              />
            </Field>
          </div>

          {draft.reportType === "ier" ? (
            <TypeBlock label="Type-specific · Information Exchange Request">
              <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
                <Field label="Direction">
                  <select
                    className={selectClass}
                    value={draft.ierDirection ?? ""}
                    onChange={(event) =>
                      updateField(
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
                    value={draft.ierCounterpartyFiu ?? ""}
                    onChange={(event) => updateField("ierCounterpartyFiu", event.target.value)}
                    placeholder="FINTRAC (Canada)"
                  />
                </Field>
                <Field label="Counterparty country">
                  <Input
                    value={draft.ierCounterpartyCountry ?? ""}
                    onChange={(event) => updateField("ierCounterpartyCountry", event.target.value)}
                    placeholder="Canada"
                  />
                </Field>
                <Field label="Egmont reference">
                  <Input
                    value={draft.ierEgmontRef ?? ""}
                    onChange={(event) => updateField("ierEgmontRef", event.target.value)}
                    placeholder="EG-2026-0419"
                  />
                </Field>
              </div>
            </TypeBlock>
          ) : null}

          {draft.reportType === "tbml" ? (
            <TypeBlock label="Type-specific · Trade-based money laundering">
              <div className="grid gap-4 md:grid-cols-3">
                <Field label="Counterparty country">
                  <Input
                    value={draft.tbmlCounterpartyCountry ?? ""}
                    onChange={(event) => updateField("tbmlCounterpartyCountry", event.target.value)}
                    placeholder="Hong Kong SAR"
                  />
                </Field>
                <Field label="LC reference">
                  <Input
                    value={draft.tbmlLcReference ?? ""}
                    onChange={(event) => updateField("tbmlLcReference", event.target.value)}
                    placeholder="LC-000-2026-045"
                  />
                </Field>
                <Field label="HS code">
                  <Input
                    value={draft.tbmlHsCode ?? ""}
                    onChange={(event) => updateField("tbmlHsCode", event.target.value)}
                    placeholder="6109.10"
                  />
                </Field>
              </div>
            </TypeBlock>
          ) : null}

          {draft.reportType === "adverse_media_str" || draft.reportType === "adverse_media_sar" ? (
            <TypeBlock label="Type-specific · Adverse media provenance">
              <div className="grid gap-4 md:grid-cols-3">
                <Field label="Source publication">
                  <Input
                    value={draft.mediaSource ?? ""}
                    onChange={(event) => updateField("mediaSource", event.target.value)}
                    placeholder="The Daily Star"
                  />
                </Field>
                <Field label="Source URL">
                  <Input
                    value={draft.mediaUrl ?? ""}
                    onChange={(event) => updateField("mediaUrl", event.target.value)}
                    placeholder="https://…"
                  />
                </Field>
                <Field label="Published date">
                  <Input
                    type="date"
                    value={draft.mediaPublishedAt ?? ""}
                    onChange={(event) => updateField("mediaPublishedAt", event.target.value)}
                  />
                </Field>
              </div>
            </TypeBlock>
          ) : null}

          {draft.reportType === "additional_info" ? (
            <TypeBlock label="Type-specific · Additional Information File">
              <Field label="Supplements report ID">
                <Input
                  value={draft.supplementsReportId ?? ""}
                  onChange={(event) => updateField("supplementsReportId", event.target.value)}
                  placeholder="Parent report UUID"
                />
              </Field>
              <p className="mt-2 font-mono text-[10px] uppercase tracking-[0.22em] text-muted-foreground">
                Subject identity carries over from the parent report automatically.
              </p>
            </TypeBlock>
          ) : null}

          <Field label="Initial narrative">
            <Textarea
              disabled={isCreating}
              value={draft.narrative}
              onChange={(event) => updateField("narrative", event.target.value)}
              placeholder="Describe the suspicious pattern, counterparties, and why this requires filing."
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

          <div className="flex flex-wrap items-center justify-between gap-3 border-t border-border pt-4">
            <p className="font-mono text-[11px] uppercase tracking-[0.22em] text-muted-foreground">
              Signed in as {viewer.fullName} · {viewer.orgName}
            </p>
            <Button
              type="button"
              disabled={isCreating || !canCreateDraft(draft)}
              onClick={() => void createDraft()}
            >
              {isCreating ? "Creating draft…" : "Create draft"}
            </Button>
          </div>
        </div>
      </section>

      <section className="border border-border">
        <div className="flex flex-col gap-3 border-b border-border px-6 py-5 lg:flex-row lg:items-center lg:justify-between">
          <div>
            <p className="font-mono text-[10px] uppercase tracking-[0.28em] text-muted-foreground">
              <span aria-hidden className="mr-2 text-accent">┼</span>
              Section · Current report lifecycle
            </p>
            <p className="mt-2 text-sm leading-relaxed text-muted-foreground">
              Every draft, submitted filing, and regulator review action lands here.
            </p>
          </div>
          <a
            href={`/api/str-reports/export${filter === "all" ? "" : `?report_type=${filter}`}`}
            className="inline-flex items-center gap-2 border border-border bg-card px-4 py-2 font-mono text-[11px] uppercase tracking-[0.22em] text-foreground transition hover:border-foreground"
          >
            Export Excel
          </a>
        </div>
        <div className="space-y-4 p-6">
          <div className="flex flex-wrap gap-0 border border-border">
            {(["all", ...REPORT_TYPES] as ReportTypeFilter[]).map((type) => (
              <button
                key={type}
                type="button"
                onClick={() => setFilter(type)}
                className={`border-r border-border px-4 py-2 font-mono text-[11px] uppercase tracking-[0.22em] transition last:border-r-0 ${
                  filter === type
                    ? "bg-foreground text-background"
                    : "text-muted-foreground hover:bg-foreground/[0.04] hover:text-foreground"
                }`}
              >
                {type === "all" ? "All" : reportTypeLabel[type]}
              </button>
            ))}
          </div>

          {reports.length === 0 ? (
            <p className="font-mono text-[11px] uppercase tracking-[0.22em] text-muted-foreground">
              No reports yet · create the first draft above
            </p>
          ) : (
            <div className="space-y-3">
              {reports.map((report) => (
                <Link
                  key={report.id}
                  href={`/strs/${report.id}`}
                  className="block border border-border bg-card px-5 py-4 transition hover:bg-foreground/[0.03]"
                >
                  <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
                    <div className="space-y-2">
                      <div className="flex flex-wrap items-center gap-3">
                        <h3 className="font-mono text-base text-foreground">{report.reportRef}</h3>
                        <span
                          className={`inline-flex items-center border px-2 py-0.5 font-mono text-[10px] uppercase tracking-[0.22em] ${
                            reportTypeTone[report.reportType] ?? "border-border text-muted-foreground"
                          }`}
                        >
                          {reportTypeLabel[report.reportType] ?? report.reportType.toUpperCase()}
                        </span>
                        <StatusBadge status={report.status} />
                      </div>
                      <p className="text-sm leading-relaxed text-foreground">
                        {report.subjectName || "Unnamed subject"} ·{" "}
                        <span className="font-mono text-muted-foreground">
                          {report.subjectAccount || "—"}
                        </span>
                      </p>
                      <p className="font-mono text-[11px] uppercase tracking-[0.22em] text-muted-foreground">
                        {report.orgName} · {report.category.replaceAll("_", " ")} ·{" "}
                        {report.primaryChannel || "No channel"}
                      </p>
                    </div>
                    <div className="space-y-1 font-mono text-[11px] uppercase tracking-[0.22em] text-muted-foreground">
                      <p>
                        Exposure ·{" "}
                        <span className="tabular-nums text-foreground">
                          <Currency amount={report.totalAmount} />
                        </span>
                      </p>
                      <p>
                        Transactions ·{" "}
                        <span className="tabular-nums text-foreground">{report.transactionCount}</span>
                      </p>
                      <p>
                        Reported ·{" "}
                        <span className="text-foreground">
                          {report.reportedAt ? new Date(report.reportedAt).toLocaleString() : "draft only"}
                        </span>
                      </p>
                    </div>
                  </div>
                </Link>
              ))}
            </div>
          )}
        </div>
      </section>
    </div>
  );
}

function TypeBlock({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="space-y-4 border border-border bg-card/40 p-4">
      <p className="font-mono text-[10px] uppercase tracking-[0.28em] text-accent">
        <span aria-hidden className="mr-2">┼</span>
        {label}
      </p>
      {children}
    </div>
  );
}
