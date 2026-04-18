"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { EmptyState } from "@/components/common/empty-state";
import { LoadingState } from "@/components/common/loading";
import { ScanProgress } from "@/components/scan/scan-progress";
import { ScanResults } from "@/components/scan/scan-results";
import { detailFromPayload, readResponsePayload } from "@/lib/http";
import type { DetectionRunDetailResponse } from "@/types/api";
import type { DetectionRunDetail } from "@/types/domain";

export function ScanRunWorkspace({ runId }: { runId: string }) {
  const [run, setRun] = useState<DetectionRunDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    void (async () => {
      try {
        const response = await fetch(`/api/scan/runs/${runId}`, { cache: "no-store" });
        const payload = (await readResponsePayload<DetectionRunDetailResponse>(response)) as
          | DetectionRunDetailResponse
          | { detail?: string };
        if (!response.ok) {
          setError(detailFromPayload(payload, "Unable to load detection run."));
          return;
        }
        setRun((payload as DetectionRunDetailResponse).run);
        setError(null);
      } catch (caughtError) {
        setError(caughtError instanceof Error ? caughtError.message : "Unable to load detection run.");
      } finally {
        setIsLoading(false);
      }
    })();
  }, [runId]);

  if (isLoading) return <LoadingState label="Loading detection run…" />;

  if (!run) {
    return (
      <EmptyState
        title="Detection run unavailable"
        description={error ?? "This run is outside the current scope."}
      />
    );
  }

  return (
    <div className="space-y-6">
      <section className="border border-border">
        <div className="flex flex-col gap-3 border-b border-border px-6 py-5 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <p className="font-mono text-[10px] uppercase tracking-[0.28em] text-muted-foreground">
              <span aria-hidden className="mr-2 text-accent">┼</span>
              Section · {run.fileName}
            </p>
            <p className="mt-2 text-sm leading-relaxed text-muted-foreground">
              Stored detection run with account-level scoring and shared-intelligence context.
            </p>
          </div>
          <div className="flex flex-wrap gap-4 font-mono text-[11px] uppercase tracking-[0.22em]">
            <Link href="/scan" className="text-accent transition hover:text-foreground">
              New scan →
            </Link>
            <Link href="/scan/history" className="text-accent transition hover:text-foreground">
              View history →
            </Link>
          </div>
        </div>
        <p className="px-6 py-4 text-sm leading-relaxed text-muted-foreground">
          This view is pinned to a persisted run so analysts can revisit the same flagged output
          without rerunning the scan.
        </p>
      </section>
      <ScanProgress run={run} isLoading={false} />
      <ScanResults run={run} isLoading={false} />
    </div>
  );
}
