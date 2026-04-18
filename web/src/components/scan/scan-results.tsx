import Link from "next/link";

import { EmptyState } from "@/components/common/empty-state";
import { LoadingState } from "@/components/common/loading";
import { FlaggedAccountCard } from "@/components/scan/flagged-account-card";
import type { DetectionRunDetail } from "@/types/domain";

export function ScanResults({
  run,
  isLoading,
}: {
  run: DetectionRunDetail | null;
  isLoading: boolean;
}) {
  return (
    <section className="border border-border">
      <div className="flex flex-col gap-3 border-b border-border px-6 py-5 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <p className="font-mono text-[10px] uppercase tracking-[0.28em] text-muted-foreground">
            <span aria-hidden className="mr-2 text-accent">┼</span>
            Section · Flagged accounts
          </p>
          <p className="mt-2 text-sm leading-relaxed text-muted-foreground">
            Account-level candidates generated from the persisted run, ready for investigation and STR
            drafting.
          </p>
        </div>
        {run ? (
          <Link
            href={`/scan/${run.id}`}
            className="font-mono text-[11px] uppercase tracking-[0.22em] text-accent transition hover:text-foreground"
          >
            Open full run →
          </Link>
        ) : null}
      </div>
      <div className="space-y-4 p-6">
        {isLoading ? (
          <LoadingState label="Loading scan results…" />
        ) : !run ? (
          <EmptyState
            title="No detection run selected"
            description="Queue a scan to populate account-level results."
          />
        ) : run.flaggedAccounts.length === 0 ? (
          <EmptyState
            title="No flagged accounts"
            description="This run completed without producing elevated candidates for the current organisation."
          />
        ) : (
          <>
            <p className="text-sm leading-relaxed text-muted-foreground">{run.summary}</p>
            <div className="space-y-3">
              {run.flaggedAccounts.map((account) => (
                <FlaggedAccountCard key={account.entityId} account={account} />
              ))}
            </div>
          </>
        )}
      </div>
    </section>
  );
}
