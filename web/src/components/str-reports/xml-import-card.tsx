"use client";

import Link from "next/link";
import { useRef, useState } from "react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { detailFromPayload, readResponsePayload } from "@/lib/http";

type ImportResult = {
  reportId: string;
  reportRef: string;
  reportType: string;
  transactionsIngested: number;
  subjectsResolved: number;
  warnings: string[];
  status: "ok" | "partial";
};

type RawImportResponse = {
  report_id: string;
  report_ref: string;
  report_type: string;
  transactions_ingested: number;
  subjects_resolved: number;
  warnings: string[];
  status: "ok" | "partial";
};

export function XmlImportCard({ onImported }: { onImported?: () => void }) {
  const inputRef = useRef<HTMLInputElement | null>(null);
  const [fileName, setFileName] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<ImportResult | null>(null);

  async function upload() {
    const input = inputRef.current;
    if (!input?.files?.length) {
      setError("Pick an XML file first.");
      return;
    }
    const file = input.files[0];
    const form = new FormData();
    form.append("file", file);
    setSubmitting(true);
    setError(null);
    setResult(null);
    try {
      const response = await fetch("/api/str-reports/import-xml", {
        method: "POST",
        body: form,
      });
      const payload = (await readResponsePayload<RawImportResponse>(response)) as
        | RawImportResponse
        | { detail?: string };
      if (!response.ok) {
        setError(detailFromPayload(payload, "Unable to import XML report."));
        return;
      }
      const raw = payload as RawImportResponse;
      setResult({
        reportId: raw.report_id,
        reportRef: raw.report_ref,
        reportType: raw.report_type,
        transactionsIngested: raw.transactions_ingested,
        subjectsResolved: raw.subjects_resolved,
        warnings: raw.warnings ?? [],
        status: raw.status,
      });
      if (input) input.value = "";
      setFileName("");
      onImported?.();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to import XML report.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Import goAML XML</CardTitle>
        <CardDescription>
          Banks can continue emitting goAML-format reports from their existing pipelines and upload them here. Kestrel parses the
          submission, creates the draft STR/SAR/CTR, ingests transactions, and resolves subjects into the shared entity pool.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="flex flex-wrap items-center gap-3">
          <input
            ref={inputRef}
            type="file"
            accept=".xml,application/xml,text/xml"
            onChange={(event) => setFileName(event.target.files?.[0]?.name ?? "")}
            className="text-sm file:mr-3 file:rounded-xl file:border file:border-border file:bg-background/60 file:px-3 file:py-2 file:text-xs file:text-foreground hover:file:border-primary/50"
          />
          {fileName ? <span className="text-xs text-muted-foreground">{fileName}</span> : null}
          <div className="flex-1" />
          <Button type="button" disabled={submitting || !fileName} onClick={() => void upload()}>
            {submitting ? "Importing…" : "Import XML"}
          </Button>
        </div>
        {error ? <p className="text-sm text-red-300">{error}</p> : null}
        {result ? (
          <div className="rounded-2xl border border-primary/30 bg-primary/5 p-4 text-sm">
            <div className="flex flex-wrap items-center gap-3">
              <span className="font-semibold">{result.reportRef}</span>
              <span className="text-xs uppercase tracking-widest text-muted-foreground">
                {result.reportType.replaceAll("_", " ")}
              </span>
              {result.status === "partial" ? (
                <span className="text-xs uppercase tracking-widest text-amber-300">partial</span>
              ) : null}
            </div>
            <p className="mt-2 text-sm text-muted-foreground">
              Ingested {result.transactionsIngested} transaction{result.transactionsIngested === 1 ? "" : "s"} and resolved{" "}
              {result.subjectsResolved} subject{result.subjectsResolved === 1 ? "" : "s"}.
            </p>
            {result.warnings.length ? (
              <ul className="mt-2 space-y-1 text-xs text-amber-300">
                {result.warnings.map((warning, index) => (
                  <li key={index}>⚠ {warning}</li>
                ))}
              </ul>
            ) : null}
            <div className="mt-3">
              <Link
                href={`/strs/${result.reportId}`}
                className="inline-flex items-center gap-2 rounded-xl border border-border/80 bg-background/60 px-4 py-2 text-xs font-medium text-primary hover:border-primary/60"
              >
                Open draft →
              </Link>
            </div>
          </div>
        ) : null}
      </CardContent>
    </Card>
  );
}
