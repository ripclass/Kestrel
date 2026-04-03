"use client";

import { useEffect, useState } from "react";

import { Area, AreaChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import { EmptyState } from "@/components/common/empty-state";
import { LoadingState } from "@/components/common/loading";
import { detailFromPayload, readResponsePayload } from "@/lib/http";
import type { TrendSeriesResponse } from "@/types/api";
import type { TrendPoint } from "@/types/domain";

export function TrendCharts() {
  const [series, setSeries] = useState<TrendPoint[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    void (async () => {
      try {
        const response = await fetch("/api/reports/trends", { cache: "no-store" });
        const payload = (await readResponsePayload<TrendSeriesResponse>(response)) as
          | TrendSeriesResponse
          | { detail?: string };
        if (!response.ok) {
          setError(detailFromPayload(payload, "Unable to load trend series."));
          return;
        }
        setSeries((payload as TrendSeriesResponse).series);
        setError(null);
      } catch (caughtError) {
        setError(caughtError instanceof Error ? caughtError.message : "Unable to load trend series.");
      } finally {
        setIsLoading(false);
      }
    })();
  }, []);

  if (isLoading) {
    return <LoadingState label="Loading trend analysis..." />;
  }

  if (error) {
    return <EmptyState title="Trend analysis unavailable" description={error} />;
  }

  if (series.length === 0) {
    return <EmptyState title="No trend data" description="Trend series will appear once reports and alerts are available in this scope." />;
  }

  return (
    <div className="h-80 rounded-2xl border border-border/70 bg-card p-4">
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={series}>
          <XAxis dataKey="month" />
          <YAxis />
          <Tooltip />
          <Area type="monotone" dataKey="alerts" stroke="#58a6a6" fill="#58a6a633" />
          <Area type="monotone" dataKey="strReports" stroke="#e8c06f" fill="#e8c06f26" />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}
