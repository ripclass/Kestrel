import { LoadingState } from "@/components/common/loading";
import { RelativeTime } from "@/components/common/relative-time";
import { StatusBadge } from "@/components/common/status-badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import type { DetectionRunDetail } from "@/types/domain";

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
    <Card>
      <CardHeader>
        <CardTitle>Active run</CardTitle>
        <CardDescription>Run status, scan volume, and persisted detection metadata for the current snapshot.</CardDescription>
      </CardHeader>
      <CardContent className="space-y-3 text-sm text-muted-foreground">
        {isLoading ? (
          <LoadingState label="Loading latest detection run..." />
        ) : run ? (
          <>
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div className="space-y-1">
                <p className="font-medium text-foreground">{run.fileName}</p>
                <p>{run.runType.replaceAll("_", " ")} snapshot</p>
              </div>
              <StatusBadge status={isSubmitting ? "processing" : run.status} />
            </div>
            <div className="grid gap-3 sm:grid-cols-3">
              <div className="rounded-xl border border-border/70 bg-background/40 p-3">
                <p className="text-xs uppercase tracking-[0.18em] text-primary">Accounts</p>
                <p className="mt-1 text-lg font-semibold text-foreground">{run.accountsScanned.toLocaleString()}</p>
              </div>
              <div className="rounded-xl border border-border/70 bg-background/40 p-3">
                <p className="text-xs uppercase tracking-[0.18em] text-primary">Alerts</p>
                <p className="mt-1 text-lg font-semibold text-foreground">{run.alertsGenerated.toLocaleString()}</p>
              </div>
              <div className="rounded-xl border border-border/70 bg-background/40 p-3">
                <p className="text-xs uppercase tracking-[0.18em] text-primary">Transactions</p>
                <p className="mt-1 text-lg font-semibold text-foreground">{run.txCount.toLocaleString()}</p>
              </div>
            </div>
            <div className="flex flex-wrap gap-4 text-xs uppercase tracking-[0.18em]">
              <span>
                Created <RelativeTime value={run.createdAt} />
              </span>
              {run.completedAt ? (
                <span>
                  Completed <RelativeTime value={run.completedAt} />
                </span>
              ) : null}
            </div>
            <p>{run.summary}</p>
            {run.error ? <p className="text-red-300">{run.error}</p> : null}
          </>
        ) : (
          <p>No detection run has been queued for this scope yet.</p>
        )}
        {notice ? <p className="text-primary/80">{notice}</p> : null}
        {error ? <p className="text-red-300">{error}</p> : null}
      </CardContent>
    </Card>
  );
}
