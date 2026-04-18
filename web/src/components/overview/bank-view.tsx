"use client";

import { useEffect, useState } from "react";

import { EmptyState } from "@/components/common/empty-state";
import { LoadingState } from "@/components/common/loading";
import { KpiCard } from "@/components/overview/kpi-card";
import { OverviewBrief } from "@/components/overview/overview-brief";
import { MatchList } from "@/components/intelligence/match-list";
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

  if (isLoading) return <LoadingState label="Loading bank overview…" />;

  if (!overview) {
    return (
      <EmptyState
        title="Bank overview unavailable"
        description={error ?? "Overview metrics are unavailable."}
      />
    );
  }

  return (
    <div className="space-y-6">
      <OverviewBrief
        title="Bank posture summary"
        headline={overview.headline}
        operational={overview.operational}
      />
      <div className="grid gap-0 border-x border-b border-border sm:grid-cols-2 xl:grid-cols-3 xl:border-b-0">
        {overview.stats.map((stat) => (
          <KpiCard key={stat.label} stat={stat} />
        ))}
      </div>
      <div className="grid gap-6 xl:grid-cols-[1.3fr_0.9fr]">
        <MatchList compact matches={matches} />
        <section className="border border-border">
          <div className="border-b border-border px-6 py-5">
            <p className="font-mono text-[10px] uppercase tracking-[0.28em] text-muted-foreground">
              <span aria-hidden className="mr-2 text-accent">┼</span>
              Section · Network threat guidance
            </p>
          </div>
          <ul className="divide-y divide-border">
            {overview.operational.map((item) => (
              <li key={item} className="px-6 py-4 text-sm leading-relaxed text-foreground">
                {item}
              </li>
            ))}
          </ul>
          {error ? (
            <p className="border-t border-border px-6 py-4 font-mono text-xs uppercase tracking-[0.18em] text-destructive">
              <span aria-hidden className="mr-2">┼</span>ERROR · {error}
            </p>
          ) : null}
        </section>
      </div>
    </div>
  );
}
