"use client";

import { useState } from "react";

import { detailFromPayload, readResponsePayload } from "@/lib/http";
import type { ReportExportResponse } from "@/types/api";
import { Button } from "@/components/ui/button";

export function ReportBuilder() {
  const [reportType, setReportType] = useState("national");
  const [notice, setNotice] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function queueExport() {
    setIsSubmitting(true);
    setNotice(null);
    setError(null);
    try {
      const response = await fetch("/api/reports/export", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ reportType }),
      });
      const payload = (await readResponsePayload<ReportExportResponse>(response)) as
        | ReportExportResponse
        | { detail?: string };
      if (!response.ok) {
        setError(detailFromPayload(payload, "Unable to queue export."));
        return;
      }
      setNotice((payload as ReportExportResponse).message);
    } catch (caughtError) {
      setError(caughtError instanceof Error ? caughtError.message : "Unable to queue export.");
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <section className="border border-border">
      <div className="border-b border-border px-6 py-5">
        <p className="font-mono text-[10px] uppercase tracking-[0.28em] text-muted-foreground">
          <span aria-hidden className="mr-2 text-accent">┼</span>
          Section · Report builder
        </p>
        <p className="mt-2 text-sm leading-relaxed text-muted-foreground">
          Select a briefing pack, typology digest, or compliance scorecard export.
        </p>
      </div>
      <div className="space-y-5 p-6">
        <label className="flex flex-col gap-2">
          <span className="font-mono text-[10px] uppercase tracking-[0.28em] text-muted-foreground">
            Export type
          </span>
          <select
            className="h-11 w-full rounded-none border border-input bg-card px-4 text-sm outline-none focus:border-foreground"
            value={reportType}
            onChange={(event) => setReportType(event.target.value)}
          >
            <option value="national">National briefing pack</option>
            <option value="compliance">Compliance scorecard</option>
            <option value="trends">Trend analysis digest</option>
          </select>
        </label>
        <div className="flex gap-2 border-t border-border pt-4">
          <Button type="button" disabled={isSubmitting} onClick={() => void queueExport()}>
            {isSubmitting ? "Queueing…" : "Generate PDF"}
          </Button>
          <Button type="button" variant="outline" disabled>
            Export XLSX
          </Button>
        </div>
        {notice ? (
          <p className="font-mono text-xs uppercase tracking-[0.18em] text-accent">
            <span aria-hidden className="mr-2">┼</span>
            {notice}
          </p>
        ) : null}
        {error ? (
          <p className="font-mono text-xs uppercase tracking-[0.18em] text-destructive">
            <span aria-hidden className="mr-2">┼</span>ERROR · {error}
          </p>
        ) : null}
      </div>
    </section>
  );
}
