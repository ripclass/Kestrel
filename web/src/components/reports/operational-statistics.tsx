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

import { detailFromPayload, readResponsePayload } from "@/lib/http";
import type { OperationalStatistics } from "@/types/domain";

const AXIS_STROKE = "#8E929A";
const GRID_STROKE = "rgba(234, 230, 218, 0.08)";
const ALARM = "#FF3823";
const FOREGROUND = "#EAE6DA";
const MUTED = "#8E929A";
// Monochromatic ramp that scales bone-to-muted, with vermillion reserved for
// the most urgent slice (first series is treated as the alarm lane).
const SERIES_PALETTE = [ALARM, FOREGROUND, MUTED, "#5A6070", "#3F454E", "#2A2E35", "#1F2228"];

const tooltipStyle: React.CSSProperties = {
  background: "#15171C",
  border: "1px solid rgba(234, 230, 218, 0.12)",
  borderRadius: 0,
  fontFamily: "var(--font-plex-mono), ui-monospace, monospace",
  fontSize: 11,
};

const tickStyle = {
  fontFamily: "var(--font-plex-mono), ui-monospace, monospace",
  fontSize: 10,
};

function Section({
  label,
  description,
  children,
}: {
  label: string;
  description?: string;
  children: React.ReactNode;
}) {
  return (
    <section className="border border-border">
      <div className="border-b border-border px-6 py-5">
        <p className="font-mono text-[10px] uppercase tracking-[0.28em] text-muted-foreground">
          <span aria-hidden className="mr-2 text-accent">┼</span>
          Section · {label}
        </p>
        {description ? (
          <p className="mt-2 text-sm leading-relaxed text-muted-foreground">{description}</p>
        ) : null}
      </div>
      <div className="p-6">{children}</div>
    </section>
  );
}

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
      <p className="font-mono text-xs uppercase tracking-[0.18em] text-destructive">
        <span aria-hidden className="mr-2">┼</span>ERROR · {error}
      </p>
    );
  }
  if (!stats) {
    return (
      <p className="font-mono text-xs uppercase tracking-[0.22em] text-muted-foreground">
        <span aria-hidden className="mr-2 text-accent">┼</span>Loading statistics…
      </p>
    );
  }

  return (
    <div className="space-y-6">
      <Section
        label="Reports filed per month"
        description="Stacked by report type across the last 24 months of activity."
      >
        <div className="h-80">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={reportsByMonth}>
              <CartesianGrid strokeDasharray="3 3" stroke={GRID_STROKE} />
              <XAxis dataKey="month" stroke={AXIS_STROKE} tick={tickStyle} />
              <YAxis stroke={AXIS_STROKE} tick={tickStyle} />
              <Tooltip contentStyle={tooltipStyle} labelStyle={{ color: MUTED }} />
              {reportTypes.map((type, index) => (
                <Bar
                  key={type}
                  dataKey={type}
                  stackId="a"
                  fill={SERIES_PALETTE[index % SERIES_PALETTE.length]}
                />
              ))}
            </BarChart>
          </ResponsiveContainer>
        </div>
      </Section>

      <div className="grid gap-6 xl:grid-cols-2">
        <Section label="Top reporting organisations" description="Lifetime report counts · top 10.">
          <div className="h-72">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={stats.reportsByOrg.slice(0, 10)} layout="vertical">
                <CartesianGrid strokeDasharray="3 3" stroke={GRID_STROKE} />
                <XAxis type="number" stroke={AXIS_STROKE} tick={tickStyle} />
                <YAxis
                  type="category"
                  dataKey="orgName"
                  stroke={AXIS_STROKE}
                  tick={tickStyle}
                  width={150}
                />
                <Tooltip contentStyle={tooltipStyle} labelStyle={{ color: MUTED }} />
                <Bar dataKey="count" fill={FOREGROUND} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </Section>

        <Section
          label="CTR volume by month"
          description="Cash-transaction-report counts and aggregate amount."
        >
          <div className="h-72">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={[...stats.ctrVolumeByMonth].reverse()}>
                <CartesianGrid strokeDasharray="3 3" stroke={GRID_STROKE} />
                <XAxis dataKey="month" stroke={AXIS_STROKE} tick={tickStyle} />
                <YAxis stroke={AXIS_STROKE} tick={tickStyle} />
                <Tooltip contentStyle={tooltipStyle} labelStyle={{ color: MUTED }} />
                <Bar dataKey="count" fill={ALARM} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </Section>
      </div>

      <div className="grid gap-6 xl:grid-cols-2">
        <Section
          label="Disseminations by recipient"
          description="Where outbound intelligence is going."
        >
          {stats.disseminationsByAgency.length === 0 ? (
            <p className="font-mono text-[11px] uppercase tracking-[0.22em] text-muted-foreground">
              No disseminations recorded yet
            </p>
          ) : (
            <div className="h-72">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={stats.disseminationsByAgency}
                    dataKey="count"
                    nameKey="recipientAgency"
                    outerRadius={100}
                    stroke="#0F1115"
                    strokeWidth={2}
                  >
                    {stats.disseminationsByAgency.map((_, index) => (
                      <Cell
                        key={`cell-${index}`}
                        fill={SERIES_PALETTE[index % SERIES_PALETTE.length]}
                      />
                    ))}
                  </Pie>
                  <Tooltip contentStyle={tooltipStyle} labelStyle={{ color: MUTED }} />
                </PieChart>
              </ResponsiveContainer>
            </div>
          )}
        </Section>

        <Section label="Case outcomes" description="Status breakdown across the case ledger.">
          <div className="h-72">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={stats.caseOutcomes}
                  dataKey="count"
                  nameKey="status"
                  outerRadius={100}
                  stroke="#0F1115"
                  strokeWidth={2}
                >
                  {stats.caseOutcomes.map((_, index) => (
                    <Cell
                      key={`cell-${index}`}
                      fill={SERIES_PALETTE[index % SERIES_PALETTE.length]}
                    />
                  ))}
                </Pie>
                <Tooltip contentStyle={tooltipStyle} labelStyle={{ color: MUTED }} />
              </PieChart>
            </ResponsiveContainer>
          </div>
        </Section>
      </div>

      <Section
        label="Average time-to-review"
        description="Hours between submission and review, by report type."
      >
        {stats.timeToReview.length === 0 ? (
          <p className="font-mono text-[11px] uppercase tracking-[0.22em] text-muted-foreground">
            No reviewed reports yet
          </p>
        ) : (
          <div className="grid gap-0 border border-border md:grid-cols-3 [&>div]:border-r [&>div]:border-b [&>div]:border-border md:[&>div:nth-child(3n)]:border-r-0">
            {stats.timeToReview.map((row) => (
              <div key={row.reportType} className="flex flex-col gap-3 p-5">
                <p className="font-mono text-[10px] uppercase tracking-[0.28em] text-muted-foreground">
                  {row.reportType.replaceAll("_", " ")}
                </p>
                <p className="font-mono text-3xl tabular-nums text-foreground">
                  {row.averageHours.toFixed(1)}
                  <span className="ml-1 text-sm text-muted-foreground">h</span>
                </p>
                <p className="font-mono text-[10px] uppercase tracking-[0.22em] text-muted-foreground">
                  <span className="tabular-nums text-foreground">{row.sampleSize}</span> report
                  {row.sampleSize === 1 ? "" : "s"} reviewed
                </p>
              </div>
            ))}
          </div>
        )}
      </Section>

      <p className="font-mono text-[10px] uppercase tracking-[0.22em] text-muted-foreground">
        Generated {new Date(stats.generatedAt).toLocaleString()}
      </p>
    </div>
  );
}
