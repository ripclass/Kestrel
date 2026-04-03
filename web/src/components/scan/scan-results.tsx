import Link from "next/link";

import { EmptyState } from "@/components/common/empty-state";
import { LoadingState } from "@/components/common/loading";
import { FlaggedAccountCard } from "@/components/scan/flagged-account-card";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import type { DetectionRunDetail } from "@/types/domain";

export function ScanResults({
  run,
  isLoading,
}: {
  run: DetectionRunDetail | null;
  isLoading: boolean;
}) {
  return (
    <Card>
      <CardHeader className="flex flex-col gap-3 lg:flex-row lg:items-end lg:justify-between">
        <div className="space-y-2">
          <CardTitle>Flagged accounts</CardTitle>
          <CardDescription>
            Account-level candidates generated from the persisted run, ready for investigation and STR drafting.
          </CardDescription>
        </div>
        {run ? (
          <Link href={`/scan/${run.id}`} className="text-sm text-primary transition hover:opacity-80">
            Open full run
          </Link>
        ) : null}
      </CardHeader>
      <CardContent className="space-y-4">
        {isLoading ? (
          <LoadingState label="Loading scan results..." />
        ) : !run ? (
          <EmptyState title="No detection run selected" description="Queue a scan to populate account-level results." />
        ) : run.flaggedAccounts.length === 0 ? (
          <EmptyState
            title="No flagged accounts"
            description="This run completed without producing elevated candidates for the current organization."
          />
        ) : (
          <>
            <p className="text-sm text-muted-foreground">{run.summary}</p>
            <div className="space-y-3">
              {run.flaggedAccounts.map((account) => (
                <FlaggedAccountCard key={account.entityId} account={account} />
              ))}
            </div>
          </>
        )}
      </CardContent>
    </Card>
  );
}
