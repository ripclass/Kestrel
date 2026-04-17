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
import { detailFromPayload, readResponsePayload } from "@/lib/http";
import type {
  DetectionRunDetailResponse,
  DetectionRunListResponse,
  ScanQueueResponse,
} from "@/types/api";
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
  const [file, setFile] = useState<File | null>(null);
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
      current.includes(code) ? current.filter((item) => item !== code) : [...current, code],
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
      let response: Response;
      if (file) {
        const formData = new FormData();
        formData.append("file", file, file.name);
        formData.append("selected_rules", selectedRules.join(","));
        response = await fetch("/api/scan/runs/upload", { method: "POST", body: formData });
      } else {
        response = await fetch("/api/scan/runs", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ fileName: fileName.trim() || undefined, selectedRules }),
        });
      }
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
      if (file) setFile(null);
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
          <UploadDrop
            fileName={fileName}
            file={file}
            onFileNameChange={setFileName}
            onFileChange={setFile}
          />
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

      <section className="border border-border">
        <div className="flex flex-col gap-3 border-b border-border px-6 py-5 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <p className="font-mono text-[10px] uppercase tracking-[0.28em] text-muted-foreground">
              <span aria-hidden className="mr-2 text-accent">┼</span>
              Section · Recent runs
            </p>
            <p className="mt-2 text-sm leading-relaxed text-muted-foreground">
              Persisted detection runs for the current scope. Open a past run to inspect the same
              flagged candidates again.
            </p>
          </div>
          <Link
            href="/scan/history"
            className="font-mono text-[11px] uppercase tracking-[0.22em] text-accent transition hover:text-foreground"
          >
            View full history →
          </Link>
        </div>
        <div className="space-y-3 p-6">
          {isLoading ? (
            <LoadingState label="Loading recent detection runs…" />
          ) : error && runs.length === 0 ? (
            <EmptyState title="Detection history unavailable" description={error} />
          ) : runs.length === 0 ? (
            <EmptyState
              title="No detection runs yet"
              description="Queue the first scan to create a persistent run history."
            />
          ) : (
            runs.slice(0, 4).map((run) => (
              <button
                key={run.id}
                type="button"
                onClick={() => void loadRun(run.id)}
                className="flex w-full flex-col gap-3 border border-border bg-card px-5 py-4 text-left transition hover:bg-foreground/[0.03] lg:flex-row lg:items-center lg:justify-between"
              >
                <div className="space-y-1">
                  <p className="font-mono text-sm text-foreground">{run.fileName}</p>
                  <p className="font-mono text-[11px] uppercase tracking-[0.22em] text-muted-foreground">
                    <span className="tabular-nums text-foreground">
                      {run.accountsScanned.toLocaleString()}
                    </span>{" "}
                    accounts scanned ·{" "}
                    <span className="tabular-nums text-foreground">
                      {run.alertsGenerated.toLocaleString()}
                    </span>{" "}
                    alerts
                  </p>
                </div>
                <div className="flex flex-wrap items-center gap-3 font-mono text-[11px] uppercase tracking-[0.22em] text-muted-foreground">
                  <StatusBadge status={run.status} />
                  <span>
                    <RelativeTime value={run.createdAt} />
                  </span>
                </div>
              </button>
            ))
          )}
        </div>
      </section>
    </div>
  );
}
