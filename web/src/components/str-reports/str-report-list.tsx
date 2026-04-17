"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import type { STRDraftPayload, STRListResponse, STRMutationResponse } from "@/types/api";
import type { STRReportSummary, Viewer } from "@/types/domain";
import { Currency } from "@/components/common/currency";
import { StatusBadge } from "@/components/common/status-badge";
import { XmlImportCard } from "@/components/str-reports/xml-import-card";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
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

const reportTypeBadgeClass: Record<string, string> = {
  str: "bg-blue-500/20 text-blue-300 border-blue-500/30",
  sar: "bg-purple-500/20 text-purple-300 border-purple-500/30",
  ctr: "bg-emerald-500/20 text-emerald-300 border-emerald-500/30",
  tbml: "bg-amber-500/20 text-amber-300 border-amber-500/30",
  complaint: "bg-rose-500/20 text-rose-300 border-rose-500/30",
  ier: "bg-cyan-500/20 text-cyan-300 border-cyan-500/30",
  internal: "bg-slate-500/20 text-slate-300 border-slate-500/30",
  adverse_media_str: "bg-orange-500/20 text-orange-300 border-orange-500/30",
  adverse_media_sar: "bg-fuchsia-500/20 text-fuchsia-300 border-fuchsia-500/30",
  escalated: "bg-red-500/20 text-red-300 border-red-500/30",
  additional_info: "bg-teal-500/20 text-teal-300 border-teal-500/30",
};

function canCreateDraft(draft: STRDraftPayload): boolean {
  const rt = draft.reportType ?? "str";
  if (rt === "ier") {
    return Boolean(draft.ierDirection && draft.ierCounterpartyFiu);
  }
  if (rt === "additional_info") {
    return Boolean(draft.supplementsReportId);
  }
  if (rt === "tbml") {
    return Boolean(draft.subjectAccount && draft.tbmlCounterpartyCountry);
  }
  if (rt === "adverse_media_str" || rt === "adverse_media_sar") {
    return Boolean(draft.subjectAccount && draft.mediaSource);
  }
  return Boolean(draft.subjectAccount);
}

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
        const payload = (await readResponsePayload<STRListResponse>(response)) as STRListResponse | { detail?: string };
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
    setNotice("Creating STR draft...");
    setIsCreating(true);
    try {
      const response = await fetch("/api/str-reports", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          ...draft,
          channels: draft.channels ?? [],
        }),
      });
      const payload = (await readResponsePayload<STRMutationResponse>(response)) as STRMutationResponse | { detail?: string };
      if (!response.ok) {
        setError(detailFromPayload(payload, "Unable to create STR draft."));
        setNotice(null);
        return;
      }
      setNotice("Draft created. Opening workspace...");
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
      <Card>
        <CardHeader>
          <CardTitle>Open a native STR draft</CardTitle>
          <CardDescription>
            Banks can file directly in Kestrel, enrich the narrative, then submit for regulator review. Regulators can
            also open internal drafts for imported or reconstructed intelligence.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
            <div className="space-y-2">
              <label className="text-xs uppercase tracking-[0.18em] text-muted-foreground">Report type</label>
              <select
                className="h-11 w-full rounded-xl border border-input bg-background/60 px-4 text-sm outline-none focus:border-primary"
                value={draft.reportType ?? "str"}
                onChange={(event) => updateField("reportType", event.target.value)}
              >
                {REPORT_TYPES.map((type) => (
                  <option key={type} value={type}>
                    {reportTypeDescription[type]}
                  </option>
                ))}
              </select>
            </div>
            {draft.reportType !== "ier" ? (
              <div className="space-y-2">
                <label className="text-xs uppercase tracking-[0.18em] text-muted-foreground">Subject account</label>
                <Input
                  value={draft.subjectAccount ?? ""}
                  onChange={(event) => updateField("subjectAccount", event.target.value)}
                  placeholder="1781430000701"
                />
              </div>
            ) : null}
            <div className="space-y-2">
              <label className="text-xs uppercase tracking-[0.18em] text-muted-foreground">Subject name</label>
              <Input
                value={draft.subjectName}
                onChange={(event) => updateField("subjectName", event.target.value)}
                placeholder="RIZWANA ENTERPRISE"
              />
            </div>
            <div className="space-y-2">
              <label className="text-xs uppercase tracking-[0.18em] text-muted-foreground">Category</label>
              <select
                className="h-11 w-full rounded-xl border border-input bg-background/60 px-4 text-sm outline-none focus:border-primary"
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
            </div>
            <div className="space-y-2">
              <label className="text-xs uppercase tracking-[0.18em] text-muted-foreground">Primary channel</label>
              <Input
                value={draft.primaryChannel}
                onChange={(event) => updateField("primaryChannel", event.target.value)}
                placeholder="RTGS"
              />
            </div>
          </div>
          <div className="grid gap-4 md:grid-cols-3">
            <div className="space-y-2">
              <label className="text-xs uppercase tracking-[0.18em] text-muted-foreground">Exposure (BDT)</label>
              <Input
                inputMode="decimal"
                type="number"
                value={draft.totalAmount}
                onChange={(event) => updateField("totalAmount", Number(event.target.value))}
              />
            </div>
            <div className="space-y-2">
              <label className="text-xs uppercase tracking-[0.18em] text-muted-foreground">Transactions</label>
              <Input
                inputMode="numeric"
                type="number"
                value={draft.transactionCount}
                onChange={(event) => updateField("transactionCount", Number(event.target.value))}
              />
            </div>
            <div className="space-y-2">
              <label className="text-xs uppercase tracking-[0.18em] text-muted-foreground">Subject phone</label>
              <Input
                value={draft.subjectPhone}
                onChange={(event) => updateField("subjectPhone", event.target.value)}
                placeholder="017XXXXXXXX"
              />
            </div>
          </div>
          {draft.reportType === "ier" ? (
            <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4 rounded-2xl border border-border/80 bg-background/40 p-4">
              <div className="space-y-2">
                <label className="text-xs uppercase tracking-[0.18em] text-muted-foreground">Direction</label>
                <select
                  className="h-11 w-full rounded-xl border border-input bg-background/60 px-4 text-sm outline-none focus:border-primary"
                  value={draft.ierDirection ?? ""}
                  onChange={(event) => updateField("ierDirection", (event.target.value || undefined) as STRDraftPayload["ierDirection"])}
                >
                  <option value="">Select direction</option>
                  <option value="outbound">Outbound (BFIU requesting)</option>
                  <option value="inbound">Inbound (foreign FIU requesting)</option>
                </select>
              </div>
              <div className="space-y-2">
                <label className="text-xs uppercase tracking-[0.18em] text-muted-foreground">Counterparty FIU</label>
                <Input
                  value={draft.ierCounterpartyFiu ?? ""}
                  onChange={(event) => updateField("ierCounterpartyFiu", event.target.value)}
                  placeholder="FINTRAC (Canada)"
                />
              </div>
              <div className="space-y-2">
                <label className="text-xs uppercase tracking-[0.18em] text-muted-foreground">Counterparty country</label>
                <Input
                  value={draft.ierCounterpartyCountry ?? ""}
                  onChange={(event) => updateField("ierCounterpartyCountry", event.target.value)}
                  placeholder="Canada"
                />
              </div>
              <div className="space-y-2">
                <label className="text-xs uppercase tracking-[0.18em] text-muted-foreground">Egmont reference</label>
                <Input
                  value={draft.ierEgmontRef ?? ""}
                  onChange={(event) => updateField("ierEgmontRef", event.target.value)}
                  placeholder="EG-2026-0419"
                />
              </div>
            </div>
          ) : null}
          {draft.reportType === "tbml" ? (
            <div className="grid gap-4 md:grid-cols-3 rounded-2xl border border-border/80 bg-background/40 p-4">
              <div className="space-y-2">
                <label className="text-xs uppercase tracking-[0.18em] text-muted-foreground">Counterparty country</label>
                <Input
                  value={draft.tbmlCounterpartyCountry ?? ""}
                  onChange={(event) => updateField("tbmlCounterpartyCountry", event.target.value)}
                  placeholder="Hong Kong SAR"
                />
              </div>
              <div className="space-y-2">
                <label className="text-xs uppercase tracking-[0.18em] text-muted-foreground">LC reference</label>
                <Input
                  value={draft.tbmlLcReference ?? ""}
                  onChange={(event) => updateField("tbmlLcReference", event.target.value)}
                  placeholder="LC-000-2026-045"
                />
              </div>
              <div className="space-y-2">
                <label className="text-xs uppercase tracking-[0.18em] text-muted-foreground">HS code</label>
                <Input
                  value={draft.tbmlHsCode ?? ""}
                  onChange={(event) => updateField("tbmlHsCode", event.target.value)}
                  placeholder="6109.10"
                />
              </div>
            </div>
          ) : null}
          {draft.reportType === "adverse_media_str" || draft.reportType === "adverse_media_sar" ? (
            <div className="grid gap-4 md:grid-cols-3 rounded-2xl border border-border/80 bg-background/40 p-4">
              <div className="space-y-2">
                <label className="text-xs uppercase tracking-[0.18em] text-muted-foreground">Source publication</label>
                <Input
                  value={draft.mediaSource ?? ""}
                  onChange={(event) => updateField("mediaSource", event.target.value)}
                  placeholder="The Daily Star"
                />
              </div>
              <div className="space-y-2">
                <label className="text-xs uppercase tracking-[0.18em] text-muted-foreground">Source URL</label>
                <Input
                  value={draft.mediaUrl ?? ""}
                  onChange={(event) => updateField("mediaUrl", event.target.value)}
                  placeholder="https://…"
                />
              </div>
              <div className="space-y-2">
                <label className="text-xs uppercase tracking-[0.18em] text-muted-foreground">Published date</label>
                <Input
                  type="date"
                  value={draft.mediaPublishedAt ?? ""}
                  onChange={(event) => updateField("mediaPublishedAt", event.target.value)}
                />
              </div>
            </div>
          ) : null}
          {draft.reportType === "additional_info" ? (
            <div className="rounded-2xl border border-border/80 bg-background/40 p-4">
              <div className="space-y-2">
                <label className="text-xs uppercase tracking-[0.18em] text-muted-foreground">Supplements report ID</label>
                <Input
                  value={draft.supplementsReportId ?? ""}
                  onChange={(event) => updateField("supplementsReportId", event.target.value)}
                  placeholder="Parent report UUID"
                />
                <p className="text-xs text-muted-foreground">
                  Subject identity carries over from the parent report automatically.
                </p>
              </div>
            </div>
          ) : null}
          <div className="space-y-2">
            <label className="text-xs uppercase tracking-[0.18em] text-muted-foreground">Initial narrative</label>
            <Textarea
              disabled={isCreating}
              value={draft.narrative}
              onChange={(event) => updateField("narrative", event.target.value)}
              placeholder="Describe the suspicious pattern, counterparties, and why this requires filing."
            />
          </div>
          {error ? <p className="text-sm text-red-300">{error}</p> : null}
          {notice ? <p className="text-sm text-primary/80">{notice}</p> : null}
          <div className="flex flex-wrap items-center justify-between gap-3">
            <p className="text-sm text-muted-foreground">
              Signed in as {viewer.fullName} at {viewer.orgName}.
            </p>
            <Button
              type="button"
              disabled={isCreating || !canCreateDraft(draft)}
              onClick={() => void createDraft()}
            >
              {isCreating ? "Creating draft..." : "Create draft"}
            </Button>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Current report lifecycle</CardTitle>
          <CardDescription>Every draft, submitted filing, and regulator review action lands here.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex flex-wrap gap-2">
            {(["all", ...REPORT_TYPES] as ReportTypeFilter[]).map((type) => (
              <button
                key={type}
                type="button"
                onClick={() => setFilter(type)}
                className={`rounded-full border px-3 py-1 text-xs font-medium transition ${
                  filter === type
                    ? "border-primary bg-primary/15 text-primary"
                    : "border-border text-muted-foreground hover:border-primary/40"
                }`}
              >
                {type === "all" ? "All" : reportTypeLabel[type]}
              </button>
            ))}
          </div>
          {reports.length === 0 ? (
            <p className="text-sm text-muted-foreground">No reports yet. Create the first draft above.</p>
          ) : (
            reports.map((report) => (
              <Link
                key={report.id}
                href={`/strs/${report.id}`}
                className="block rounded-2xl border border-border/80 bg-background/50 p-4 transition hover:border-primary/60 hover:bg-background/70"
              >
                <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
                  <div className="space-y-2">
                    <div className="flex flex-wrap items-center gap-3">
                      <h3 className="text-base font-semibold">{report.reportRef}</h3>
                      <span
                        className={`inline-flex items-center rounded-full border px-2 py-0.5 text-[10px] font-semibold tracking-widest ${
                          reportTypeBadgeClass[report.reportType] ?? "bg-muted text-muted-foreground border-border"
                        }`}
                      >
                        {reportTypeLabel[report.reportType] ?? report.reportType.toUpperCase()}
                      </span>
                      <StatusBadge status={report.status} />
                    </div>
                    <p className="text-sm text-muted-foreground">
                      {report.subjectName || "Unnamed subject"} · {report.subjectAccount || "—"}
                    </p>
                    <p className="text-sm text-muted-foreground">
                      {report.orgName} · {report.category.replaceAll("_", " ")} · {report.primaryChannel || "No channel"}
                    </p>
                  </div>
                  <div className="space-y-1 text-sm text-muted-foreground">
                    <p>
                      Exposure: <Currency amount={report.totalAmount} />
                    </p>
                    <p>Transactions: {report.transactionCount}</p>
                    <p>Reported: {report.reportedAt ? new Date(report.reportedAt).toLocaleString() : "draft only"}</p>
                  </div>
                </div>
              </Link>
            ))
          )}
        </CardContent>
      </Card>
    </div>
  );
}
