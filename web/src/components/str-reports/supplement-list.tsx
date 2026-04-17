"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import { detailFromPayload, readResponsePayload } from "@/lib/http";
import type { STRListResponse } from "@/types/api";
import type { STRReportSummary } from "@/types/domain";

export function SupplementList({ parentId }: { parentId: string }) {
  const [supplements, setSupplements] = useState<STRReportSummary[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const response = await fetch(`/api/str-reports/${parentId}/supplements`, { cache: "no-store" });
      const payload = (await readResponsePayload<STRListResponse>(response)) as
        | STRListResponse
        | { detail?: string };
      if (!response.ok) {
        setError(detailFromPayload(payload, "Unable to load supplements."));
        return;
      }
      setSupplements((payload as STRListResponse).reports);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to load supplements.");
    } finally {
      setLoading(false);
    }
  }, [parentId]);

  useEffect(() => {
    void load();
  }, [load]);

  if (loading) return null;
  if (error) {
    return (
      <p className="font-mono text-xs uppercase tracking-[0.18em] text-destructive">
        <span aria-hidden className="mr-2">┼</span>ERROR · {error}
      </p>
    );
  }
  if (supplements.length === 0) return null;

  return (
    <section className="border border-border">
      <div className="border-b border-border px-6 py-5">
        <p className="font-mono text-[10px] uppercase tracking-[0.28em] text-muted-foreground">
          <span aria-hidden className="mr-2 text-accent">┼</span>
          Section · Supplements
        </p>
        <p className="mt-2 text-sm leading-relaxed text-muted-foreground">
          Additional Information Files linked to this report. Each one carries its own audit trail but
          shares the parent&apos;s subject identity.
        </p>
      </div>
      <ul className="divide-y divide-border">
        {supplements.map((supplement) => (
          <li key={supplement.id}>
            <Link
              href={`/strs/${supplement.id}`}
              className="flex flex-wrap items-center justify-between gap-3 px-6 py-4 transition hover:bg-foreground/[0.03]"
            >
              <div className="flex flex-wrap items-center gap-3">
                <span className="font-mono text-sm text-foreground">{supplement.reportRef}</span>
                <span className="font-mono text-[10px] uppercase tracking-[0.22em] text-muted-foreground">
                  {supplement.status.replaceAll("_", " ")}
                </span>
              </div>
              <span className="font-mono text-[11px] uppercase tracking-[0.22em] text-muted-foreground">
                Opened {new Date(supplement.createdAt).toLocaleString()}
              </span>
            </Link>
          </li>
        ))}
      </ul>
    </section>
  );
}
