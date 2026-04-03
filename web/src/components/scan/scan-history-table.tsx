"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { DataTable } from "@/components/common/data-table";
import { EmptyState } from "@/components/common/empty-state";
import { LoadingState } from "@/components/common/loading";
import { RelativeTime } from "@/components/common/relative-time";
import { StatusBadge } from "@/components/common/status-badge";
import { detailFromPayload, readResponsePayload } from "@/lib/http";
import type { DetectionRunListResponse } from "@/types/api";
import type { DetectionRunSummary } from "@/types/domain";

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

  if (isLoading) {
    return <LoadingState label="Loading scan history..." />;
  }

  if (error) {
    return <EmptyState title="Scan history unavailable" description={error} />;
  }

  if (runs.length === 0) {
    return <EmptyState title="No scans yet" description="Queued detection runs will appear here with their full history." />;
  }

  return (
    <DataTable
      columns={["File", "Status", "Accounts", "Alerts", "Transactions", "Created"]}
      rows={runs.map((run) => [
        <Link key={`${run.id}-file`} href={`/scan/${run.id}`} className="text-primary transition hover:opacity-80">
          {run.fileName}
        </Link>,
        <StatusBadge key={`${run.id}-status`} status={run.status} />,
        `${run.accountsScanned.toLocaleString()}`,
        `${run.alertsGenerated.toLocaleString()}`,
        `${run.txCount.toLocaleString()}`,
        <RelativeTime key={`${run.id}-created`} value={run.createdAt} />,
      ])}
    />
  );
}
