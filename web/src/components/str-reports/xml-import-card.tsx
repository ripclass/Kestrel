"use client";

import Link from "next/link";
import { useRef, useState } from "react";

import { Button } from "@/components/ui/button";
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
    <section className="border border-border">
      <div className="border-b border-border px-6 py-5">
        <p className="font-mono text-[10px] uppercase tracking-[0.28em] text-muted-foreground">
          <span aria-hidden className="mr-2 text-accent">┼</span>
          Section · Import goAML XML
        </p>
        <p className="mt-2 text-sm leading-relaxed text-muted-foreground">
          Banks can continue emitting goAML-format reports from their existing pipelines and upload them
          here. Kestrel parses the submission, creates the draft STR/SAR/CTR, ingests transactions, and
          resolves subjects into the shared entity pool.
        </p>
      </div>
      <div className="space-y-5 p-6">
        <div className="flex flex-wrap items-center gap-3">
          <input
            ref={inputRef}
            type="file"
            accept=".xml,application/xml,text/xml"
            onChange={(event) => setFileName(event.target.files?.[0]?.name ?? "")}
            className="text-sm file:mr-3 file:border file:border-border file:bg-card file:px-3 file:py-2 file:font-mono file:text-[11px] file:uppercase file:tracking-[0.22em] file:text-foreground hover:file:border-foreground"
          />
          {fileName ? (
            <span className="font-mono text-[11px] uppercase tracking-[0.22em] text-muted-foreground">
              {fileName}
            </span>
          ) : null}
          <div className="flex-1" />
          <Button type="button" disabled={submitting || !fileName} onClick={() => void upload()}>
            {submitting ? "Importing…" : "Import XML"}
          </Button>
        </div>
        {error ? (
          <p className="font-mono text-xs uppercase tracking-[0.18em] text-destructive">
            <span aria-hidden className="mr-2">┼</span>ERROR · {error}
          </p>
        ) : null}
        {result ? (
          <div className="border border-accent/40 bg-accent/[0.04] p-4">
            <div className="flex flex-wrap items-center gap-3">
              <span className="font-mono text-sm text-foreground">{result.reportRef}</span>
              <span className="font-mono text-[10px] uppercase tracking-[0.22em] text-muted-foreground">
                {result.reportType.replaceAll("_", " ")}
              </span>
              {result.status === "partial" ? (
                <span className="font-mono text-[10px] uppercase tracking-[0.22em] text-accent">
                  partial
                </span>
              ) : null}
            </div>
            <p className="mt-2 text-sm leading-relaxed text-foreground">
              Ingested <span className="font-mono tabular-nums">{result.transactionsIngested}</span>{" "}
              transaction{result.transactionsIngested === 1 ? "" : "s"} and resolved{" "}
              <span className="font-mono tabular-nums">{result.subjectsResolved}</span> subject
              {result.subjectsResolved === 1 ? "" : "s"}.
            </p>
            {result.warnings.length ? (
              <ul className="mt-2 space-y-1">
                {result.warnings.map((warning, index) => (
                  <li key={index} className="font-mono text-[11px] uppercase tracking-[0.22em] text-accent">
                    <span aria-hidden className="mr-2">┼</span>
                    {warning}
                  </li>
                ))}
              </ul>
            ) : null}
            <div className="mt-4">
              <Link
                href={`/strs/${result.reportId}`}
                className="inline-flex items-center gap-2 border border-border bg-card px-4 py-2 font-mono text-[11px] uppercase tracking-[0.22em] text-accent transition hover:border-foreground hover:text-foreground"
              >
                Open draft →
              </Link>
            </div>
          </div>
        ) : null}
      </div>
    </section>
  );
}
