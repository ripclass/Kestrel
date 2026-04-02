"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState, useTransition } from "react";

import type { STRDraftPayload, STRListResponse, STRMutationResponse } from "@/types/api";
import type { STRReportSummary, Viewer } from "@/types/domain";
import { Currency } from "@/components/common/currency";
import { StatusBadge } from "@/components/common/status-badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";

const emptyDraft: STRDraftPayload = {
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

export function STRReportList({ viewer }: { viewer: Viewer }) {
  const router = useRouter();
  const [reports, setReports] = useState<STRReportSummary[]>([]);
  const [draft, setDraft] = useState<STRDraftPayload>(emptyDraft);
  const [error, setError] = useState<string | null>(null);
  const [isPending, startTransition] = useTransition();

  useEffect(() => {
    void (async () => {
      const response = await fetch("/api/str-reports", { cache: "no-store" });
      const payload = (await response.json()) as STRListResponse | { detail?: string };
      if (!response.ok) {
        setError("detail" in payload ? (payload.detail ?? "Unable to load STR reports.") : "Unable to load STR reports.");
        return;
      }
      setReports((payload as STRListResponse).reports);
    })();
  }, []);

  function updateField<K extends keyof STRDraftPayload>(field: K, value: STRDraftPayload[K]) {
    setDraft((current) => ({ ...current, [field]: value }));
  }

  async function createDraft() {
    setError(null);
    const response = await fetch("/api/str-reports", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        ...draft,
        channels: draft.channels ?? [],
      }),
    });
    const payload = (await response.json()) as STRMutationResponse | { detail?: string };
    if (!response.ok) {
      setError("detail" in payload ? (payload.detail ?? "Unable to create STR draft.") : "Unable to create STR draft.");
      return;
    }
    router.push(`/strs/${(payload as STRMutationResponse).report.id}`);
  }

  return (
    <div className="space-y-6">
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
              <label className="text-xs uppercase tracking-[0.18em] text-muted-foreground">Subject account</label>
              <Input
                value={draft.subjectAccount}
                onChange={(event) => updateField("subjectAccount", event.target.value)}
                placeholder="1781430000701"
              />
            </div>
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
          <div className="space-y-2">
            <label className="text-xs uppercase tracking-[0.18em] text-muted-foreground">Initial narrative</label>
            <Textarea
              value={draft.narrative}
              onChange={(event) => updateField("narrative", event.target.value)}
              placeholder="Describe the suspicious pattern, counterparties, and why this requires filing."
            />
          </div>
          {error ? <p className="text-sm text-red-300">{error}</p> : null}
          <div className="flex flex-wrap items-center justify-between gap-3">
            <p className="text-sm text-muted-foreground">
              Signed in as {viewer.fullName} at {viewer.orgName}.
            </p>
            <Button
              disabled={isPending || !draft.subjectAccount}
              onClick={() => startTransition(() => void createDraft())}
            >
              {isPending ? "Opening draft..." : "Create STR draft"}
            </Button>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Current STR lifecycle</CardTitle>
          <CardDescription>Every draft, submitted filing, and regulator review action lands here.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {reports.length === 0 ? (
            <p className="text-sm text-muted-foreground">No STRs yet. Create the first draft above.</p>
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
                      <StatusBadge status={report.status} />
                    </div>
                    <p className="text-sm text-muted-foreground">
                      {report.subjectName || "Unnamed subject"} · {report.subjectAccount}
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
