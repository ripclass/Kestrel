"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { EmptyState } from "@/components/common/empty-state";
import { LoadingState } from "@/components/common/loading";
import { RelativeTime } from "@/components/common/relative-time";
import { StatusBadge } from "@/components/common/status-badge";
import { detailFromPayload, readResponsePayload } from "@/lib/http";
import type { DetectionRunListResponse } from "@/types/api";
import type { DetectionRunSummary } from "@/types/domain";

function Th({ children, className = "" }: { children: React.ReactNode; className?: string }) {
  return (
    <th
      className={`px-6 py-3 text-left align-bottom font-mono text-[10px] uppercase tracking-[0.24em] text-muted-foreground ${className}`}
    >
      {children}
    </th>
  );
}

function Td({ children, className = "" }: { children: React.ReactNode; className?: string }) {
  return <td className={`px-6 py-3 align-top ${className}`}>{children}</td>;
}

export function ScanHistoryTable() {
  const [runs, setRuns] = useState<DetectionRunSummary[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    void (async () => {
      try {
        const response = await fetch("/api/scan/runs", { cache: "no-store" });
        const payload = (await readResponsePayload<DetectionRunListResponse>(response)) as
          | DetectionRunListResponse
          | { detail?: string };

        if (!response.ok) {
          setError(detailFromPayload(payload, "Unable to load scan history."));
          return;
        }

        setRuns((payload as DetectionRunListResponse).runs);
        setError(null);
      } catch (caughtError) {
        setError(caughtError instanceof Error ? caughtError.message : "Unable to load scan history.");
      } finally {
        setIsLoading(false);
      }
    })();
  }, []);

  if (isLoading) return <LoadingState label="Loading scan history…" />;

  if (error) {
    return <EmptyState title="Scan history unavailable" description={error} />;
  }

  if (runs.length === 0) {
    return (
      <EmptyState
        title="No scans yet"
        description="Queued detection runs will appear here with their full history."
      />
    );
  }

  return (
    <section className="border border-border">
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-border bg-foreground/[0.02]">
              <Th>File</Th>
              <Th>Status</Th>
              <Th className="text-right">Accounts</Th>
              <Th className="text-right">Alerts</Th>
              <Th className="text-right">Transactions</Th>
              <Th className="text-right">Created</Th>
            </tr>
          </thead>
          <tbody>
            {runs.map((run) => (
              <tr key={run.id} className="border-b border-border last:border-b-0">
                <Td>
                  <Link
                    href={`/scan/${run.id}`}
                    className="font-mono text-accent transition hover:text-foreground"
                  >
                    {run.fileName}
                  </Link>
                </Td>
                <Td>
                  <StatusBadge status={run.status} />
                </Td>
                <Td className="text-right">
                  <span className="font-mono tabular-nums text-foreground">
                    {run.accountsScanned.toLocaleString()}
                  </span>
                </Td>
                <Td className="text-right">
                  <span className="font-mono tabular-nums text-foreground">
                    {run.alertsGenerated.toLocaleString()}
                  </span>
                </Td>
                <Td className="text-right">
                  <span className="font-mono tabular-nums text-foreground">
                    {run.txCount.toLocaleString()}
                  </span>
                </Td>
                <Td className="text-right">
                  <span className="font-mono text-[11px] uppercase tracking-[0.18em] text-muted-foreground">
                    <RelativeTime value={run.createdAt} />
                  </span>
                </Td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
