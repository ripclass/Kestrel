"use client";

import { useEffect, useState } from "react";

import { DataTable } from "@/components/common/data-table";
import { EmptyState } from "@/components/common/empty-state";
import { LoadingState } from "@/components/common/loading";
import { detailFromPayload, readResponsePayload } from "@/lib/http";
import type { ComplianceResponse } from "@/types/api";
import type { ComplianceScore } from "@/types/domain";

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
        setError(caughtError instanceof Error ? caughtError.message : "Unable to load compliance scorecard.");
      } finally {
        setIsLoading(false);
      }
    })();
  }, []);

  if (isLoading) {
    return <LoadingState label="Loading compliance scorecard..." />;
  }

  if (error) {
    return <EmptyState title="Compliance scorecard unavailable" description={error} />;
  }

  if (banks.length === 0) {
    return <EmptyState title="No compliance data" description="Compliance scoring will appear once reports and scan activity exist for this scope." />;
  }

  return (
    <DataTable
      columns={["Bank", "Timeliness", "Conversion", "Coverage", "Score"]}
      rows={banks.map((bank) => [
        bank.orgName,
        `${bank.submissionTimeliness}`,
        `${bank.alertConversion}`,
        `${bank.peerCoverage}`,
        `${bank.score}`,
      ])}
    />
  );
}
