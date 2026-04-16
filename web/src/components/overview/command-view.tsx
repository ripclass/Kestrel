"use client";

import { useEffect, useState } from "react";

import { EmptyState } from "@/components/common/empty-state";
import { LoadingState } from "@/components/common/loading";
import { AlertTicker } from "@/components/overview/alert-ticker";
import { KpiCard } from "@/components/overview/kpi-card";
import { MatchTicker } from "@/components/overview/match-ticker";
import { OverviewBrief } from "@/components/overview/overview-brief";
import { ThreatMap } from "@/components/overview/threat-map";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { detailFromPayload, readResponsePayload } from "@/lib/http";
import type { ComplianceResponse, NationalReportResponse } from "@/types/api";
import type { ComplianceScore } from "@/types/domain";

const levelColor: Record<string, string> = {
  "Very high": "bg-red-500/20 text-red-400 border-red-500/30",
  "High": "bg-orange-500/20 text-orange-400 border-orange-500/30",
  "Elevated": "bg-yellow-500/20 text-yellow-400 border-yellow-500/30",
  "Monitoring": "bg-muted text-muted-foreground border-border",
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

  if (isLoading) {
    return <LoadingState label="Loading command view..." />;
  }

  if (!dashboard) {
    return <EmptyState title="Command view unavailable" description={error ?? "National metrics are unavailable."} />;
  }

  const laggingBanks = compliance.filter((b) => b.score < 70).slice(0, 3);
  const topBanks = compliance.filter((b) => b.score >= 70).slice(0, 3);

  return (
    <div className="space-y-6">
      <AlertTicker />
      <MatchTicker />
      <OverviewBrief title="National command summary" headline={dashboard.headline} operational={dashboard.operational} />
      <div className="grid gap-4 xl:grid-cols-3">
        {dashboard.stats.map((stat) => (
          <KpiCard key={stat.label} stat={stat} />
        ))}
      </div>
      {dashboard.threatMap.length > 0 ? (
        <div className="flex flex-wrap gap-2">
          {dashboard.threatMap.map((row) => (
            <span
              key={row.channel}
              className={`inline-flex items-center gap-1.5 rounded-full border px-3 py-1 text-xs font-medium ${levelColor[row.level] ?? "bg-muted text-muted-foreground border-border"}`}
            >
              {row.channel}
              <span className="opacity-70">{row.signalCount} signals</span>
            </span>
          ))}
        </div>
      ) : null}
      <div className="grid gap-6 xl:grid-cols-[1.3fr_0.9fr]">
        <ThreatMap rows={dashboard.threatMap} />
        <Card>
          <CardHeader>
            <CardTitle>Bank compliance posture</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            {laggingBanks.length > 0 ? (
              <div className="space-y-2">
                <p className="text-xs font-medium uppercase tracking-widest text-orange-400">Attention needed</p>
                {laggingBanks.map((bank) => (
                  <div key={bank.orgName} className="rounded-xl border border-orange-500/30 bg-orange-500/5 p-4">
                    <div className="flex items-center justify-between">
                      <p className="font-medium">{bank.orgName}</p>
                      <span className="text-xl font-semibold text-orange-400">{bank.score}</span>
                    </div>
                    <p className="mt-2 text-sm text-muted-foreground">
                      Timeliness {bank.submissionTimeliness}, conversion {bank.alertConversion}, peer coverage {bank.peerCoverage}
                    </p>
                  </div>
                ))}
              </div>
            ) : null}
            {topBanks.length > 0 ? (
              <div className="space-y-2">
                <p className="text-xs font-medium uppercase tracking-widest text-muted-foreground">Leading</p>
                {topBanks.map((bank) => (
                  <div key={bank.orgName} className="rounded-xl border border-border/70 bg-background/50 p-4">
                    <div className="flex items-center justify-between">
                      <p className="font-medium">{bank.orgName}</p>
                      <span className="text-xl font-semibold">{bank.score}</span>
                    </div>
                    <p className="mt-2 text-sm text-muted-foreground">
                      Timeliness {bank.submissionTimeliness}, conversion {bank.alertConversion}, peer coverage {bank.peerCoverage}
                    </p>
                  </div>
                ))}
              </div>
            ) : null}
            {error ? <p className="text-sm text-red-300">{error}</p> : null}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
