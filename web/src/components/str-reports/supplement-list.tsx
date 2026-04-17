"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
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
      <Card>
        <CardContent className="py-4 text-sm text-red-300">{error}</CardContent>
      </Card>
    );
  }
  if (supplements.length === 0) return null;

  return (
    <Card>
      <CardHeader>
        <CardTitle>Supplements</CardTitle>
        <CardDescription>
          Additional Information Files linked to this report. Each one carries its own audit trail but shares the parent&apos;s subject identity.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-2">
        {supplements.map((supplement) => (
          <Link
            key={supplement.id}
            href={`/strs/${supplement.id}`}
            className="block rounded-xl border border-border/70 bg-background/60 p-3 transition hover:border-primary/60"
          >
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div className="flex flex-wrap items-center gap-3">
                <span className="font-mono text-sm">{supplement.reportRef}</span>
                <span className="text-xs uppercase tracking-widest text-muted-foreground">
                  {supplement.status.replaceAll("_", " ")}
                </span>
              </div>
              <span className="text-xs text-muted-foreground">
                Opened {new Date(supplement.createdAt).toLocaleString()}
              </span>
            </div>
          </Link>
        ))}
      </CardContent>
    </Card>
  );
}
