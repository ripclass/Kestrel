"use client";

import { useEffect, useState } from "react";

import { EmptyState } from "@/components/common/empty-state";
import { LoadingState } from "@/components/common/loading";
import { KpiCard } from "@/components/overview/kpi-card";
import { OverviewBrief } from "@/components/overview/overview-brief";
import { MatchList } from "@/components/intelligence/match-list";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { detailFromPayload, readResponsePayload } from "@/lib/http";
import type { LiveOverviewResponse, MatchListResponse } from "@/types/api";
import type { MatchSummary } from "@/types/domain";

export function BankView() {
  const [overview, setOverview] = useState<LiveOverviewResponse | null>(null);
  const [matches, setMatches] = useState<MatchSummary[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    void (async () => {
      try {
        const [overviewResponse, matchesResponse] = await Promise.all([
          fetch("/api/overview", { cache: "no-store" }),
          fetch("/api/intelligence/matches", { cache: "no-store" }),
        ]);
        const [overviewPayload, matchesPayload] = await Promise.all([
          readResponsePayload<LiveOverviewResponse>(overviewResponse),
          readResponsePayload<MatchListResponse>(matchesResponse),
        ]);

        if (!overviewResponse.ok) {
          setError(detailFromPayload(overviewPayload, "Unable to load bank overview."));
          return;
        }
        if (!matchesResponse.ok) {
          setError(detailFromPayload(matchesPayload, "Unable to load cross-bank matches."));
          return;
        }

        setOverview(overviewPayload as LiveOverviewResponse);
        setMatches((matchesPayload as MatchListResponse).matches);
        setError(null);
      } catch (caughtError) {
        setError(caughtError instanceof Error ? caughtError.message : "Unable to load bank overview.");
      } finally {
        setIsLoading(false);
      }
    })();
  }, []);

  if (isLoading) {
    return <LoadingState label="Loading bank overview..." />;
  }

  if (!overview) {
    return <EmptyState title="Bank overview unavailable" description={error ?? "Overview metrics are unavailable."} />;
  }

  return (
    <div className="space-y-6">
      <OverviewBrief title="Bank posture summary" headline={overview.headline} operational={overview.operational} />
      <div className="grid gap-4 xl:grid-cols-3">
        {overview.stats.map((stat) => (
          <KpiCard key={stat.label} stat={stat} />
        ))}
      </div>
      <div className="grid gap-6 xl:grid-cols-[1.3fr_0.9fr]">
        <MatchList compact matches={matches} />
        <Card>
          <CardHeader>
            <CardTitle>Network threat guidance</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4 text-sm text-muted-foreground">
            {overview.operational.map((item) => (
              <div key={item} className="rounded-xl border border-border/70 bg-background/50 p-4">
                {item}
              </div>
            ))}
            {error ? <p className="text-red-300">{error}</p> : null}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
