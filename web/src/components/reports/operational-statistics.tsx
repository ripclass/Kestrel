"use client";

import { useEffect, useMemo, useState } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { detailFromPayload, readResponsePayload } from "@/lib/http";
import type { OperationalStatistics } from "@/types/domain";

const PIE_COLORS = ["#58a6a6", "#c7a77a", "#d48aa0", "#8cb5d6", "#b8a0e0", "#94c17a", "#e6b380"];

export function OperationalStatisticsDashboard() {
  const [stats, setStats] = useState<OperationalStatistics | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    void (async () => {
      try {
        const response = await fetch("/api/admin/statistics", { cache: "no-store" });
        const payload = (await readResponsePayload<OperationalStatistics>(response)) as
          | OperationalStatistics
          | { detail?: string };
        if (!response.ok) {
          setError(detailFromPayload(payload, "Unable to load statistics."));
          return;
        }
        setStats(payload as OperationalStatistics);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Unable to load statistics.");
      }
    })();
  }, []);

  const reportsByMonth = useMemo(() => {
    if (!stats) return [];
    const bucket = new Map<string, Record<string, number | string>>();
    for (const row of stats.reportsByTypeByMonth) {
      const entry = bucket.get(row.month) ?? { month: row.month };
      entry[row.reportType] = ((entry[row.reportType] as number) ?? 0) + row.count;
      bucket.set(row.month, entry);
    }
    return Array.from(bucket.values()).sort((a, b) =>
      String(a.month).localeCompare(String(b.month)),
    );
  }, [stats]);

  const reportTypes = useMemo(() => {
    if (!stats) return [];
    return Array.from(new Set(stats.reportsByTypeByMonth.map((row) => row.reportType)));
  }, [stats]);

  if (error) {
    return (
      <Card>
        <CardContent className="py-10 text-sm text-red-300">{error}</CardContent>
      </Card>
    );
  }
  if (!stats) {
    return (
      <Card>
        <CardContent className="py-10 text-sm text-muted-foreground">Loading statistics…</CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle>Reports filed per month</CardTitle>
          <CardDescription>Stacked by report type across the last 24 months of activity.</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="h-80">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={reportsByMonth}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(88,166,166,0.15)" />
                <XAxis dataKey="month" stroke="#9aa9bd" />
                <YAxis stroke="#9aa9bd" />
                <Tooltip contentStyle={{ background: "#101b2b", border: "1px solid rgba(88,166,166,0.4)", borderRadius: 12 }} />
                {reportTypes.map((type, index) => (
                  <Bar
                    key={type}
                    dataKey={type}
                    stackId="a"
                    fill={PIE_COLORS[index % PIE_COLORS.length]}
                  />
                ))}
              </BarChart>
            </ResponsiveContainer>
          </div>
        </CardContent>
      </Card>

      <div className="grid gap-6 xl:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Top reporting organizations</CardTitle>
            <CardDescription>Lifetime report counts (top 10).</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="h-72">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={stats.reportsByOrg.slice(0, 10)} layout="vertical">
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(88,166,166,0.15)" />
                  <XAxis type="number" stroke="#9aa9bd" />
                  <YAxis type="category" dataKey="orgName" stroke="#9aa9bd" width={150} />
                  <Tooltip contentStyle={{ background: "#101b2b", border: "1px solid rgba(88,166,166,0.4)", borderRadius: 12 }} />
                  <Bar dataKey="count" fill="#58a6a6" />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>CTR volume by month</CardTitle>
            <CardDescription>Cash-transaction-report counts and aggregate amount.</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="h-72">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={[...stats.ctrVolumeByMonth].reverse()}>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(88,166,166,0.15)" />
                  <XAxis dataKey="month" stroke="#9aa9bd" />
                  <YAxis stroke="#9aa9bd" />
                  <Tooltip contentStyle={{ background: "#101b2b", border: "1px solid rgba(88,166,166,0.4)", borderRadius: 12 }} />
                  <Bar dataKey="count" fill="#c7a77a" name="Count" />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-6 xl:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Disseminations by recipient</CardTitle>
            <CardDescription>Where outbound intelligence is going.</CardDescription>
          </CardHeader>
          <CardContent>
            {stats.disseminationsByAgency.length === 0 ? (
              <p className="text-sm text-muted-foreground">No disseminations recorded yet.</p>
            ) : (
              <div className="h-72">
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie
                      data={stats.disseminationsByAgency}
                      dataKey="count"
                      nameKey="recipientAgency"
                      outerRadius={100}
                      label
                    >
                      {stats.disseminationsByAgency.map((_, index) => (
                        <Cell key={`cell-${index}`} fill={PIE_COLORS[index % PIE_COLORS.length]} />
                      ))}
                    </Pie>
                    <Tooltip contentStyle={{ background: "#101b2b", border: "1px solid rgba(88,166,166,0.4)", borderRadius: 12 }} />
                  </PieChart>
                </ResponsiveContainer>
              </div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Case outcomes</CardTitle>
            <CardDescription>Status breakdown across the case ledger.</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="h-72">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={stats.caseOutcomes}
                    dataKey="count"
                    nameKey="status"
                    outerRadius={100}
                    label
                  >
                    {stats.caseOutcomes.map((_, index) => (
                      <Cell key={`cell-${index}`} fill={PIE_COLORS[index % PIE_COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip contentStyle={{ background: "#101b2b", border: "1px solid rgba(88,166,166,0.4)", borderRadius: 12 }} />
                </PieChart>
              </ResponsiveContainer>
            </div>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Average time-to-review</CardTitle>
          <CardDescription>Hours between submission and review, by report type.</CardDescription>
        </CardHeader>
        <CardContent>
          {stats.timeToReview.length === 0 ? (
            <p className="text-sm text-muted-foreground">No reviewed reports yet.</p>
          ) : (
            <div className="grid gap-3 md:grid-cols-3">
              {stats.timeToReview.map((row) => (
                <div key={row.reportType} className="rounded-xl border border-border/70 bg-background/60 p-4">
                  <p className="text-xs uppercase tracking-[0.18em] text-muted-foreground">
                    {row.reportType.replaceAll("_", " ")}
                  </p>
                  <p className="mt-2 text-2xl font-semibold">{row.averageHours.toFixed(1)}h</p>
                  <p className="mt-1 text-xs text-muted-foreground">
                    {row.sampleSize} report{row.sampleSize === 1 ? "" : "s"} reviewed
                  </p>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      <p className="text-xs text-muted-foreground">
        Generated {new Date(stats.generatedAt).toLocaleString()}
      </p>
    </div>
  );
}
