"use client";

import { useState } from "react";

import { Button } from "@/components/ui/button";

export function CaseExport({ caseId, caseRef }: { caseId: string; caseRef: string }) {
  const [isGenerating, setIsGenerating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function generatePdf() {
    setIsGenerating(true);
    setError(null);
    try {
      const response = await fetch(`/api/cases/${caseId}/export`, { cache: "no-store" });
      if (!response.ok) {
        const detail = await response.json().catch(() => ({ detail: "PDF export failed." }));
        setError(detail.detail || "PDF export failed.");
        return;
      }
      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `${caseRef || `case-${caseId}`}.pdf`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
    } catch (caughtError) {
      setError(caughtError instanceof Error ? caughtError.message : "PDF export failed.");
    } finally {
      setIsGenerating(false);
    }
  }

  return (
    <div className="flex flex-col gap-3">
      <div className="flex flex-wrap gap-2">
        <Button type="button" disabled={isGenerating} onClick={() => void generatePdf()}>
          {isGenerating ? "Generating PDF…" : "Generate case PDF"}
        </Button>
        <Button type="button" variant="outline" disabled>
          Export evidence pack
        </Button>
      </div>
      {error ? (
        <p className="font-mono text-xs uppercase tracking-[0.18em] text-destructive">
          <span aria-hidden className="mr-2">┼</span>ERROR · {error}
        </p>
      ) : null}
    </div>
  );
}
