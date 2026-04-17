import { LoadingState } from "@/components/common/loading";
import { RelativeTime } from "@/components/common/relative-time";
import { StatusBadge } from "@/components/common/status-badge";
import type { DetectionRunDetail } from "@/types/domain";

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex flex-col gap-2 border border-border p-4">
      <span className="font-mono text-[10px] uppercase tracking-[0.28em] text-muted-foreground">
        {label}
      </span>
      <span className="font-mono text-2xl tabular-nums text-foreground">{value}</span>
    </div>
  );
}

export function ScanProgress({
  run,
  isLoading,
  isSubmitting = false,
  notice,
  error,
}: {
  run: DetectionRunDetail | null;
  isLoading: boolean;
  isSubmitting?: boolean;
  notice?: string | null;
  error?: string | null;
}) {
  return (
    <section className="border border-border">
      <div className="border-b border-border px-6 py-5">
        <p className="font-mono text-[10px] uppercase tracking-[0.28em] text-muted-foreground">
          <span aria-hidden className="mr-2 text-accent">┼</span>
          Section · Active run
        </p>
        <p className="mt-2 text-sm leading-relaxed text-muted-foreground">
          Run status, scan volume, and persisted detection metadata for the current snapshot.
        </p>
      </div>
      <div className="space-y-5 p-6">
        {isLoading ? (
          <LoadingState label="Loading latest detection run…" />
        ) : run ? (
          <>
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div className="space-y-1">
                <p className="font-mono text-sm text-foreground">{run.fileName}</p>
                <p className="font-mono text-[11px] uppercase tracking-[0.22em] text-muted-foreground">
                  {run.runType.replaceAll("_", " ")} snapshot
                </p>
              </div>
              <StatusBadge status={isSubmitting ? "processing" : run.status} />
            </div>
            <div className="grid gap-0 border border-border sm:grid-cols-3 [&>div]:border-r [&>div]:last:border-r-0 [&>div]:border-border">
              <Stat label="Accounts" value={run.accountsScanned.toLocaleString()} />
              <Stat label="Alerts" value={run.alertsGenerated.toLocaleString()} />
              <Stat label="Transactions" value={run.txCount.toLocaleString()} />
            </div>
            <div className="flex flex-wrap gap-4 font-mono text-[11px] uppercase tracking-[0.22em] text-muted-foreground">
              <span>
                Created <RelativeTime value={run.createdAt} />
              </span>
              {run.completedAt ? (
                <span>
                  Completed <RelativeTime value={run.completedAt} />
                </span>
              ) : null}
            </div>
            <p className="text-sm leading-relaxed text-foreground">{run.summary}</p>
            {run.error ? (
              <p className="font-mono text-xs uppercase tracking-[0.18em] text-destructive">
                <span aria-hidden className="mr-2">┼</span>ERROR · {run.error}
              </p>
            ) : null}
          </>
        ) : (
          <p className="font-mono text-[11px] uppercase tracking-[0.22em] text-muted-foreground">
            No detection run has been queued for this scope yet
          </p>
        )}
        {notice ? (
          <p className="font-mono text-xs uppercase tracking-[0.18em] text-accent">
            <span aria-hidden className="mr-2">┼</span>
            {notice}
          </p>
        ) : null}
        {error ? (
          <p className="font-mono text-xs uppercase tracking-[0.18em] text-destructive">
            <span aria-hidden className="mr-2">┼</span>ERROR · {error}
          </p>
        ) : null}
      </div>
    </section>
  );
}
