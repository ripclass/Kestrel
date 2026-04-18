"use client";

import { useEffect, useState } from "react";

import { EmptyState } from "@/components/common/empty-state";
import { LoadingState } from "@/components/common/loading";
import { detailFromPayload, readResponsePayload } from "@/lib/http";
import type { ComplianceResponse } from "@/types/api";
import type { ComplianceScore } from "@/types/domain";

function scoreTone(score: number) {
  if (score < 70) return "text-accent";
  if (score < 85) return "text-foreground";
  return "text-foreground";
}

export function ComplianceScorecard() {
  const [banks, setBanks] = useState<ComplianceScore[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    void (async () => {
      try {
        const response = await fetch("/api/reports/compliance", { cache: "no-store" });
        const payload = (await readResponsePayload<ComplianceResponse>(response)) as
          | ComplianceResponse
          | { detail?: string };
        if (!response.ok) {
          setError(detailFromPayload(payload, "Unable to load compliance scorecard."));
          return;
        }
        setBanks((payload as ComplianceResponse).banks);
        setError(null);
      } catch (caughtError) {
        setError(
          caughtError instanceof Error ? caughtError.message : "Unable to load compliance scorecard.",
        );
      } finally {
        setIsLoading(false);
      }
    })();
  }, []);

  if (isLoading) return <LoadingState label="Loading compliance scorecard…" />;

  if (error) {
    return <EmptyState title="Compliance scorecard unavailable" description={error} />;
  }

  if (banks.length === 0) {
    return (
      <EmptyState
        title="No compliance data"
        description="Compliance scoring will appear once reports and scan activity exist for this scope."
      />
    );
  }

  return (
    <section className="border border-border">
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-border bg-foreground/[0.02]">
              <th className="px-6 py-3 text-left align-bottom font-mono text-[10px] uppercase tracking-[0.24em] text-muted-foreground">
                Bank
              </th>
              <th className="px-6 py-3 text-right align-bottom font-mono text-[10px] uppercase tracking-[0.24em] text-muted-foreground">
                Timeliness
              </th>
              <th className="px-6 py-3 text-right align-bottom font-mono text-[10px] uppercase tracking-[0.24em] text-muted-foreground">
                Conversion
              </th>
              <th className="px-6 py-3 text-right align-bottom font-mono text-[10px] uppercase tracking-[0.24em] text-muted-foreground">
                Coverage
              </th>
              <th className="px-6 py-3 text-right align-bottom font-mono text-[10px] uppercase tracking-[0.24em] text-muted-foreground">
                Score
              </th>
            </tr>
          </thead>
          <tbody>
            {banks.map((bank) => (
              <tr key={bank.orgName} className="border-b border-border last:border-b-0">
                <td className="px-6 py-3 text-sm text-foreground">{bank.orgName}</td>
                <td className="px-6 py-3 text-right font-mono text-sm tabular-nums text-muted-foreground">
                  {bank.submissionTimeliness}
                </td>
                <td className="px-6 py-3 text-right font-mono text-sm tabular-nums text-muted-foreground">
                  {bank.alertConversion}
                </td>
                <td className="px-6 py-3 text-right font-mono text-sm tabular-nums text-muted-foreground">
                  {bank.peerCoverage}
                </td>
                <td
                  className={`px-6 py-3 text-right font-mono text-base tabular-nums ${scoreTone(bank.score)}`}
                >
                  {bank.score}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
