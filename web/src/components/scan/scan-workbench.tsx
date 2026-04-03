"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { EmptyState } from "@/components/common/empty-state";
import { LoadingState } from "@/components/common/loading";
import { RelativeTime } from "@/components/common/relative-time";
import { StatusBadge } from "@/components/common/status-badge";
import { ScanConfig, defaultSelectedRules } from "@/components/scan/scan-config";
import { ScanProgress } from "@/components/scan/scan-progress";
import { ScanResults } from "@/components/scan/scan-results";
import { UploadDrop } from "@/components/scan/upload-drop";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { detailFromPayload, readResponsePayload } from "@/lib/http";
import type { DetectionRunDetailResponse, DetectionRunListResponse, ScanQueueResponse } from "@/types/api";
import type { DetectionRunDetail, DetectionRunSummary } from "@/types/domain";

async function fetchRunDetail(runId: string): Promise<DetectionRunDetail> {
  const response = await fetch(`/api/scan/runs/${runId}`, { cache: "no-store" });
  const payload = (await readResponsePayload<DetectionRunDetailResponse>(response)) as
    | DetectionRunDetailResponse
    | { detail?: string };

  if (!response.ok) {
    throw new Error(detailFromPayload(payload, "Unable to load detection run."));
  }

  return (payload as DetectionRunDetailResponse).run;
}

export function ScanWorkbench() {
  const [fileName, setFileName] = useState("dbbl-network-snapshot-apr03.csv");
  const [selectedRules, setSelectedRules] = useState<string[]>(defaultSelectedRules);
  const [runs, setRuns] = useState<DetectionRunSummary[]>([]);
  const [activeRun, setActiveRun] = useState<DetectionRunDetail | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

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

        const history = (payload as DetectionRunListResponse).runs;
        setRuns(history);

        if (history.length > 0) {
          setActiveRun(await fetchRunDetail(history[0].id));
        }

        setError(null);
      } catch (caughtError) {
        setError(caughtError instanceof Error ? caughtError.message : "Unable to load scan history.");
      } finally {
        setIsLoading(false);
      }
    })();
  }, []);

  function toggleRule(code: string) {
    setSelectedRules((current) =>
      current.includes(code)
        ? current.filter((item) => item !== code)
        : [...current, code],
    );
  }

  async function loadRun(runId: string) {
    setNotice(null);
    setError(null);
    try {
      setActiveRun(await fetchRunDetail(runId));
    } catch (caughtError) {
      setError(caughtError instanceof Error ? caughtError.message : "Unable to load detection run.");
    }
  }

  async function queueRun() {
    setIsSubmitting(true);
    setNotice(null);
    setError(null);
    try {
      const response = await fetch("/api/scan/runs", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          fileName: fileName.trim() || undefined,
          selectedRules,
        }),
      });
      const payload = (await readResponsePayload<ScanQueueResponse>(response)) as
        | ScanQueueResponse
        | { detail?: string };

      if (!response.ok) {
        setError(detailFromPayload(payload, "Unable to queue detection run."));
        return;
      }

      const result = payload as ScanQueueResponse;
      setActiveRun(result.run);
      setRuns((current) => [result.run, ...current.filter((run) => run.id !== result.run.id)]);
      setNotice(result.message);
    } catch (caughtError) {
      setError(caughtError instanceof Error ? caughtError.message : "Unable to queue detection run.");
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <div className="space-y-6">
      <div className="grid gap-6 xl:grid-cols-[0.9fr_1.1fr]">
        <div className="space-y-6">
          <UploadDrop fileName={fileName} onFileNameChange={setFileName} />
          <ScanConfig
            selectedRules={selectedRules}
            onToggleRule={toggleRule}
            onRun={() => void queueRun()}
            isSubmitting={isSubmitting}
          />
        </div>
        <div className="space-y-6">
          <ScanProgress
            run={activeRun}
            isLoading={isLoading}
            isSubmitting={isSubmitting}
            notice={notice}
            error={error}
          />
          <ScanResults run={activeRun} isLoading={isLoading} />
        </div>
      </div>

      <Card>
        <CardHeader className="flex flex-col gap-3 lg:flex-row lg:items-end lg:justify-between">
          <div className="space-y-2">
            <CardTitle>Recent runs</CardTitle>
            <p className="text-sm text-muted-foreground">
              Persisted detection runs for the current scope. Open a past run to inspect the same flagged candidates again.
            </p>
          </div>
          <Link href="/scan/history" className="text-sm text-primary transition hover:opacity-80">
            View full history
          </Link>
        </CardHeader>
        <CardContent className="space-y-3">
          {isLoading ? (
            <LoadingState label="Loading recent detection runs..." />
          ) : error && runs.length === 0 ? (
            <EmptyState title="Detection history unavailable" description={error} />
          ) : runs.length === 0 ? (
            <EmptyState title="No detection runs yet" description="Queue the first scan to create a persistent run history." />
          ) : (
            runs.slice(0, 4).map((run) => (
              <button
                key={run.id}
                type="button"
                onClick={() => void loadRun(run.id)}
                className="flex w-full flex-col gap-3 rounded-xl border border-border/70 bg-background/40 p-4 text-left transition hover:border-primary/40 lg:flex-row lg:items-center lg:justify-between"
              >
                <div className="space-y-1">
                  <p className="font-medium">{run.fileName}</p>
                  <p className="text-sm text-muted-foreground">
                    {run.accountsScanned.toLocaleString()} accounts scanned · {run.alertsGenerated.toLocaleString()} alerts
                  </p>
                </div>
                <div className="flex flex-wrap items-center gap-3 text-sm text-muted-foreground">
                  <StatusBadge status={run.status} />
                  <span>
                    <RelativeTime value={run.createdAt} />
                  </span>
                </div>
              </button>
            ))
          )}
        </CardContent>
      </Card>
    </div>
  );
}
