"use client";

import { useEffect, useState } from "react";

import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import { EmptyState } from "@/components/common/empty-state";
import { LoadingState } from "@/components/common/loading";
import { detailFromPayload, readResponsePayload } from "@/lib/http";
import type { TrendSeriesResponse } from "@/types/api";
import type { TrendPoint } from "@/types/domain";

const AXIS_STROKE = "#8E929A";
const GRID_STROKE = "rgba(234, 230, 218, 0.08)";
const ALERTS_STROKE = "#FF3823";
const STR_STROKE = "#EAE6DA";

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

  if (isLoading) return <LoadingState label="Loading trend analysis…" />;
  if (error) return <EmptyState title="Trend analysis unavailable" description={error} />;
  if (series.length === 0) {
    return (
      <EmptyState
        title="No trend data"
        description="Trend series will appear once reports and alerts are available in this scope."
      />
    );
  }

  return (
    <section className="border border-border">
      <div className="border-b border-border px-6 py-5">
        <p className="font-mono text-[10px] uppercase tracking-[0.28em] text-muted-foreground">
          <span aria-hidden className="mr-2 text-accent">┼</span>
          Section · Alerts and STRs over time
        </p>
      </div>
      <div className="h-80 p-6">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={series}>
            <CartesianGrid strokeDasharray="3 3" stroke={GRID_STROKE} />
            <XAxis
              dataKey="month"
              stroke={AXIS_STROKE}
              tick={{ fontFamily: "var(--font-plex-mono)", fontSize: 10 }}
            />
            <YAxis
              stroke={AXIS_STROKE}
              tick={{ fontFamily: "var(--font-plex-mono)", fontSize: 10 }}
            />
            <Tooltip
              contentStyle={{
                background: "#15171C",
                border: "1px solid rgba(234, 230, 218, 0.12)",
                borderRadius: 0,
                fontFamily: "var(--font-plex-mono)",
                fontSize: 11,
              }}
              labelStyle={{ color: "#8E929A" }}
            />
            <Area
              type="monotone"
              dataKey="alerts"
              stroke={ALERTS_STROKE}
              fill={ALERTS_STROKE}
              fillOpacity={0.12}
              strokeWidth={1.5}
            />
            <Area
              type="monotone"
              dataKey="strReports"
              stroke={STR_STROKE}
              fill={STR_STROKE}
              fillOpacity={0.08}
              strokeWidth={1}
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </section>
  );
}
