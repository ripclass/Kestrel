"use client";

import { useState } from "react";

import { detailFromPayload, readResponsePayload } from "@/lib/http";
import type { ReportExportResponse } from "@/types/api";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

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
    <Card>
      <CardHeader>
        <CardTitle>Report builder</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4 text-sm text-muted-foreground">
        <p>Select briefing pack, typology digest, or compliance scorecard export.</p>
        <select
          className="h-10 rounded-lg border border-input bg-background/60 px-3 text-sm outline-none focus:border-primary"
          value={reportType}
          onChange={(event) => setReportType(event.target.value)}
        >
          <option value="national">National briefing pack</option>
          <option value="compliance">Compliance scorecard</option>
          <option value="trends">Trend analysis digest</option>
        </select>
        <div className="flex gap-3">
          <Button type="button" disabled={isSubmitting} onClick={() => void queueExport()}>
            {isSubmitting ? "Queueing..." : "Generate PDF"}
          </Button>
          <Button type="button" variant="outline" disabled>
            Export XLSX
          </Button>
        </div>
        {notice ? <p className="text-primary/80">{notice}</p> : null}
        {error ? <p className="text-red-300">{error}</p> : null}
      </CardContent>
    </Card>
  );
}
