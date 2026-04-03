"use client";

import { useEffect, useState } from "react";

import { AlertQueue } from "@/components/alerts/alert-queue";
import { CaseBoard } from "@/components/cases/case-board";
import { EmptyState } from "@/components/common/empty-state";
import { LoadingState } from "@/components/common/loading";
import { AlertTicker } from "@/components/overview/alert-ticker";
import { KpiCard } from "@/components/overview/kpi-card";
import { OverviewBrief } from "@/components/overview/overview-brief";
import { detailFromPayload, readResponsePayload } from "@/lib/http";
import type { LiveOverviewResponse } from "@/types/api";

export function AnalystView() {
  const [overview, setOverview] = useState<LiveOverviewResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    void (async () => {
      try {
        const response = await fetch("/api/overview", { cache: "no-store" });
        const payload = (await readResponsePayload<LiveOverviewResponse>(response)) as
          | LiveOverviewResponse
          | { detail?: string };
        if (!response.ok) {
          setError(detailFromPayload(payload, "Unable to load analyst overview."));
          return;
        }
        setOverview(payload as LiveOverviewResponse);
        setError(null);
      } catch (caughtError) {
        setError(caughtError instanceof Error ? caughtError.message : "Unable to load analyst overview.");
      } finally {
        setIsLoading(false);
      }
    })();
  }, []);

  if (isLoading) {
    return <LoadingState label="Loading analyst overview..." />;
  }

  if (!overview) {
    return <EmptyState title="Analyst overview unavailable" description={error ?? "Overview metrics are unavailable."} />;
  }

  return (
    <div className="space-y-6">
      <AlertTicker />
      <OverviewBrief title="Investigation pulse" headline={overview.headline} operational={overview.operational} />
      <div className="grid gap-4 xl:grid-cols-3">
        {overview.stats.map((stat) => (
          <KpiCard key={stat.label} stat={stat} />
        ))}
      </div>
      <div className="grid gap-6 xl:grid-cols-[1.3fr_0.9fr]">
        <AlertQueue alertsToShow={3} />
        <CaseBoard title="Recent cases" casesToShow={3} />
      </div>
    </div>
  );
}
