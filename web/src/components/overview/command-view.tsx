"use client";

import { useEffect, useState } from "react";

import { EmptyState } from "@/components/common/empty-state";
import { LoadingState } from "@/components/common/loading";
import { AlertTicker } from "@/components/overview/alert-ticker";
import { KpiCard } from "@/components/overview/kpi-card";
import { MatchTicker } from "@/components/overview/match-ticker";
import { OverviewBrief } from "@/components/overview/overview-brief";
import { ThreatMap } from "@/components/overview/threat-map";
import { detailFromPayload, readResponsePayload } from "@/lib/http";
import type { ComplianceResponse, NationalReportResponse } from "@/types/api";
import type { ComplianceScore } from "@/types/domain";

const levelTone: Record<string, string> = {
  "Very high": "border-accent text-accent",
  High: "border-accent/60 text-accent",
  Elevated: "border-foreground/40 text-foreground",
  Monitoring: "border-border text-muted-foreground",
};

export function CommandView() {
  const [dashboard, setDashboard] = useState<NationalReportResponse | null>(null);
  const [compliance, setCompliance] = useState<ComplianceScore[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    void (async () => {
      try {
        const [nationalResponse, complianceResponse] = await Promise.all([
          fetch("/api/reports/national", { cache: "no-store" }),
          fetch("/api/reports/compliance", { cache: "no-store" }),
        ]);
        const [nationalPayload, compliancePayload] = await Promise.all([
          readResponsePayload<NationalReportResponse>(nationalResponse),
          readResponsePayload<ComplianceResponse>(complianceResponse),
        ]);

        if (!nationalResponse.ok) {
          setError(detailFromPayload(nationalPayload, "Unable to load national dashboard."));
          return;
        }
        if (!complianceResponse.ok) {
          setError(detailFromPayload(compliancePayload, "Unable to load compliance preview."));
          return;
        }

        setDashboard(nationalPayload as NationalReportResponse);
        setCompliance((compliancePayload as ComplianceResponse).banks);
        setError(null);
      } catch (caughtError) {
        setError(caughtError instanceof Error ? caughtError.message : "Unable to load command view.");
      } finally {
        setIsLoading(false);
      }
    })();
  }, []);

  if (isLoading) return <LoadingState label="Loading command view…" />;

  if (!dashboard) {
    return <EmptyState title="Command view unavailable" description={error ?? "National metrics are unavailable."} />;
  }

  const laggingBanks = compliance.filter((b) => b.score < 70).slice(0, 3);
  const topBanks = compliance.filter((b) => b.score >= 70).slice(0, 3);

  return (
    <div className="space-y-6">
      <AlertTicker />
      <MatchTicker />
      <OverviewBrief
        title="National command summary"
        headline={dashboard.headline}
        operational={dashboard.operational}
      />
      <div className="grid gap-0 border-x border-b border-border sm:grid-cols-2 xl:grid-cols-3 xl:border-b-0">
        {dashboard.stats.map((stat) => (
          <KpiCard key={stat.label} stat={stat} />
        ))}
      </div>
      {dashboard.threatMap.length > 0 ? (
        <div className="flex flex-wrap gap-0 border border-border">
          {dashboard.threatMap.map((row) => (
            <span
              key={row.channel}
              className={`flex items-center gap-2 border-r border-border px-4 py-2.5 font-mono text-[11px] uppercase tracking-[0.18em] last:border-r-0 ${levelTone[row.level] ?? "border-border text-muted-foreground"}`}
            >
              {row.channel}
              <span className="tabular-nums opacity-70">· {row.signalCount} signals</span>
            </span>
          ))}
        </div>
      ) : null}
      <div className="grid gap-6 xl:grid-cols-[1.3fr_0.9fr]">
        <ThreatMap rows={dashboard.threatMap} />
        <section className="border border-border">
          <div className="border-b border-border px-6 py-5">
            <p className="font-mono text-[10px] uppercase tracking-[0.28em] text-muted-foreground">
              <span aria-hidden className="mr-2 text-accent">┼</span>
              Section · Bank compliance posture
            </p>
          </div>
          <div className="space-y-6 px-6 py-6">
            {laggingBanks.length > 0 ? (
              <section>
                <p className="font-mono text-[10px] uppercase tracking-[0.28em] text-accent">
                  Attention needed
                </p>
                <ul className="mt-3 divide-y divide-border border border-border">
                  {laggingBanks.map((bank) => (
                    <li key={bank.orgName} className="flex items-start justify-between gap-6 px-4 py-3">
                      <div>
                        <p className="text-sm font-semibold text-foreground">{bank.orgName}</p>
                        <p className="mt-1 text-xs text-muted-foreground">
                          Timeliness {bank.submissionTimeliness} · Conversion {bank.alertConversion} · Peer {bank.peerCoverage}
                        </p>
                      </div>
                      <span className="font-mono text-2xl leading-none tabular-nums text-accent">
                        {bank.score}
                      </span>
                    </li>
                  ))}
                </ul>
              </section>
            ) : null}
            {topBanks.length > 0 ? (
              <section>
                <p className="font-mono text-[10px] uppercase tracking-[0.28em] text-muted-foreground">
                  Leading
                </p>
                <ul className="mt-3 divide-y divide-border border border-border">
                  {topBanks.map((bank) => (
                    <li key={bank.orgName} className="flex items-start justify-between gap-6 px-4 py-3">
                      <div>
                        <p className="text-sm font-semibold text-foreground">{bank.orgName}</p>
                        <p className="mt-1 text-xs text-muted-foreground">
                          Timeliness {bank.submissionTimeliness} · Conversion {bank.alertConversion} · Peer {bank.peerCoverage}
                        </p>
                      </div>
                      <span className="font-mono text-2xl leading-none tabular-nums text-foreground">
                        {bank.score}
                      </span>
                    </li>
                  ))}
                </ul>
              </section>
            ) : null}
            {error ? (
              <p className="font-mono text-xs uppercase tracking-[0.18em] text-destructive">
                <span aria-hidden className="mr-2">┼</span>ERROR · {error}
              </p>
            ) : null}
          </div>
        </section>
      </div>
    </div>
  );
}
