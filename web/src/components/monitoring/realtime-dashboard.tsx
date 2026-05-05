"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

import { EmptyState } from "@/components/common/empty-state";
import { ErrorState } from "@/components/common/error-state";
import { LoadingState } from "@/components/common/loading";
import type { Viewer } from "@/types/domain";

const WINDOW_OPTIONS = [
  { label: "1h", value: 1 },
  { label: "24h", value: 24 },
  { label: "7d", value: 168 },
];

const REFRESH_MS = 30_000;

interface DecisionDistribution {
  approve: number;
  review: number;
  hold: number;
  reject: number;
}

interface LatencyPercentiles {
  p50: number;
  p95: number;
  p99: number;
  avg: number;
}

interface TopRecentRow {
  id: string;
  transaction_external_id: string;
  score: number;
  decision: string;
  cross_bank_flag: boolean;
  latency_ms: number;
  created_at: string | null;
}

interface RecentRow {
  id: string;
  transaction_external_id: string;
  score: number;
  decision: string;
  cross_bank_flag: boolean;
  latency_ms: number;
  feedback_received: boolean;
  feedback_outcome: string | null;
  created_at: string | null;
}

interface MetricsPayload {
  window_hours: number;
  total: number;
  decisions: DecisionDistribution;
  cross_bank_flag_count: number;
  latency_ms: LatencyPercentiles;
  top_recent: TopRecentRow[];
  persona_view: "bank" | "regulator";
  generated_at: string;
}

const DECISION_ORDER: Array<{ key: keyof DecisionDistribution; label: string }> = [
  { key: "approve", label: "APPROVE" },
  { key: "review", label: "REVIEW" },
  { key: "hold", label: "HOLD" },
  { key: "reject", label: "REJECT" },
];

function decisionTone(decision: string): string {
  const value = decision.toLowerCase();
  if (value === "reject") return "text-destructive";
  if (value === "hold") return "text-accent";
  if (value === "review") return "text-foreground";
  return "text-muted-foreground";
}

function fmtMs(value: number): string {
  if (!Number.isFinite(value)) return "—";
  if (value >= 1000) return `${(value / 1000).toFixed(2)} s`;
  return `${Math.round(value)} ms`;
}

function fmtTime(iso: string | null): string {
  if (!iso) return "—";
  try {
    const dt = new Date(iso);
    return dt.toLocaleTimeString("en-GB", { hour12: false });
  } catch {
    return iso;
  }
}

function Eyebrow({ children }: { children: React.ReactNode }) {
  return (
    <p className="font-mono text-[10px] uppercase tracking-[0.28em] text-muted-foreground">
      <span aria-hidden className="mr-2 text-accent">┼</span>
      {children}
    </p>
  );
}

function Section({ eyebrow, children }: { eyebrow: string; children: React.ReactNode }) {
  return (
    <section className="border border-border">
      <div className="border-b border-border px-6 py-5">
        <Eyebrow>{eyebrow}</Eyebrow>
      </div>
      {children}
    </section>
  );
}

function StatTile({ label, value, hint }: { label: string; value: string | number; hint?: string }) {
  return (
    <div className="flex flex-col gap-2 border border-border p-5">
      <p className="font-mono text-[10px] uppercase tracking-[0.28em] text-muted-foreground">{label}</p>
      <p className="font-mono text-3xl tabular-nums text-foreground">{value}</p>
      {hint ? (
        <p className="font-mono text-[10px] uppercase tracking-[0.22em] text-muted-foreground">{hint}</p>
      ) : null}
    </div>
  );
}

interface DashboardData {
  metrics: MetricsPayload;
  recent: RecentRow[];
}

export function RealtimeMonitoringDashboard({ viewer }: { viewer: Viewer }) {
  const [windowHours, setWindowHours] = useState<number>(24);
  const [data, setData] = useState<DashboardData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [lastRefreshed, setLastRefreshed] = useState<string | null>(null);

  const handleWindowChange = (value: number) => {
    setLoading(true);
    setError(null);
    setWindowHours(value);
  };

  const fetchData = useCallback(async () => {
    const metricsParams = new URLSearchParams();
    metricsParams.set("window_hours", String(windowHours));
    metricsParams.set("top_limit", "8");

    try {
      const [metricsResponse, recentResponse] = await Promise.all([
        fetch(`/api/realtime/score/metrics?${metricsParams.toString()}`, { cache: "no-store" }),
        fetch(`/api/realtime/score/recent?limit=25`, { cache: "no-store" }),
      ]);
      const metricsJson = await metricsResponse.json();
      const recentJson = await recentResponse.json();
      if (!metricsResponse.ok) throw new Error(metricsJson.detail ?? "metrics");
      if (!recentResponse.ok) throw new Error(recentJson.detail ?? "recent");
      setData({
        metrics: metricsJson.metrics as MetricsPayload,
        recent: (recentJson.rows ?? []) as RecentRow[],
      });
      setLastRefreshed(new Date().toLocaleTimeString("en-GB", { hour12: false }));
    } catch (err) {
      const message = err instanceof Error ? err.message : "Unable to load realtime monitoring.";
      setError(message);
    } finally {
      setLoading(false);
    }
  }, [windowHours]);

  useEffect(() => {
    fetchData();
    const handle = window.setInterval(fetchData, REFRESH_MS);
    return () => window.clearInterval(handle);
  }, [fetchData]);

  const personaView = data?.metrics.persona_view ?? "bank";
  const isRegulator = viewer.persona === "bfiu_director" || viewer.persona === "bfiu_analyst";

  const decisionMax = useMemo(() => {
    if (!data) return 1;
    return Math.max(1, ...DECISION_ORDER.map((d) => data.metrics.decisions[d.key] ?? 0));
  }, [data]);

  return (
    <div className="space-y-8">
      <Section eyebrow={`Filters · ${personaView === "regulator" ? "Regulator view" : "Bank view"}`}>
        <div className="flex flex-wrap items-center gap-6 px-6 py-5">
          <div className="flex items-center gap-2">
            <span className="font-mono text-[10px] uppercase tracking-[0.22em] text-muted-foreground">Window</span>
            <div className="flex border border-border">
              {WINDOW_OPTIONS.map((opt) => (
                <button
                  key={opt.value}
                  type="button"
                  onClick={() => handleWindowChange(opt.value)}
                  className={`px-3 py-1.5 font-mono text-[11px] uppercase tracking-[0.22em] transition ${
                    windowHours === opt.value
                      ? "bg-foreground text-background"
                      : "text-muted-foreground hover:text-foreground"
                  }`}
                >
                  {opt.label}
                </button>
              ))}
            </div>
          </div>

          <div className="ml-auto flex items-center gap-3">
            <span className="font-mono text-[10px] uppercase tracking-[0.22em] text-muted-foreground">
              Auto-refresh · 30 s
            </span>
            {lastRefreshed ? (
              <span className="font-mono text-[10px] uppercase tracking-[0.22em] text-muted-foreground">
                Last · {lastRefreshed}
              </span>
            ) : null}
            <button
              type="button"
              onClick={() => fetchData()}
              className="border border-border px-3 py-1.5 font-mono text-[11px] uppercase tracking-[0.22em] text-foreground transition hover:bg-foreground hover:text-background"
            >
              Refresh now
            </button>
          </div>
        </div>
      </Section>

      {loading && !data ? (
        <LoadingState label="Resolving real-time monitoring" />
      ) : error && !data ? (
        <ErrorState title="Unable to load real-time monitoring" description={error} />
      ) : !data || data.metrics.total === 0 ? (
        <EmptyState
          title="No scoring activity yet"
          description="Once your core-banking integration starts calling POST /transactions/score, decisions stream into this dashboard within 30 seconds."
        />
      ) : (
        <>
          <div className="grid grid-cols-1 gap-px border border-border bg-border md:grid-cols-2 lg:grid-cols-4">
            <StatTile
              label="Calls in window"
              value={data.metrics.total.toLocaleString("en-IN")}
              hint={`Window: ${data.metrics.window_hours}h`}
            />
            <StatTile
              label="Latency · p50 / p95 / p99"
              value={`${fmtMs(data.metrics.latency_ms.p50)} · ${fmtMs(data.metrics.latency_ms.p95)} · ${fmtMs(data.metrics.latency_ms.p99)}`}
              hint={`Average ${fmtMs(data.metrics.latency_ms.avg)}`}
            />
            <StatTile
              label="Cross-bank flagged"
              value={data.metrics.cross_bank_flag_count}
              hint={`${
                data.metrics.total
                  ? Math.round((data.metrics.cross_bank_flag_count / data.metrics.total) * 100)
                  : 0
              }% of calls`}
            />
            <StatTile
              label="Reject rate"
              value={`${
                data.metrics.total
                  ? Math.round((data.metrics.decisions.reject / data.metrics.total) * 100)
                  : 0
              }%`}
              hint={`${data.metrics.decisions.reject} of ${data.metrics.total}`}
            />
          </div>

          <Section eyebrow="Decision distribution">
            <ul className="divide-y divide-border">
              {DECISION_ORDER.map(({ key, label }) => {
                const count = data.metrics.decisions[key] ?? 0;
                const ratio = count / decisionMax;
                const pct = data.metrics.total
                  ? Math.round((count / data.metrics.total) * 100)
                  : 0;
                return (
                  <li key={key} className="grid grid-cols-12 items-center gap-4 px-6 py-4">
                    <div className={`col-span-2 font-mono text-sm tracking-[0.18em] ${decisionTone(key)}`}>
                      {label}
                    </div>
                    <div className="col-span-7">
                      <div aria-hidden className="h-3 border border-border bg-background">
                        <div
                          className={`h-full ${
                            key === "reject"
                              ? "bg-destructive"
                              : key === "hold"
                                ? "bg-accent"
                                : "bg-foreground"
                          }`}
                          style={{ width: `${Math.max(2, ratio * 100)}%` }}
                        />
                      </div>
                    </div>
                    <div className="col-span-2 text-right font-mono text-sm tabular-nums text-foreground">
                      {count.toLocaleString("en-IN")}
                    </div>
                    <div className="col-span-1 text-right font-mono text-[11px] uppercase tracking-[0.22em] text-muted-foreground">
                      {pct}%
                    </div>
                  </li>
                );
              })}
            </ul>
          </Section>

          <Section eyebrow={`Top scored · last hour · ${data.metrics.top_recent.length}`}>
            {data.metrics.top_recent.length === 0 ? (
              <p className="px-6 py-6 font-mono text-xs uppercase tracking-[0.22em] text-muted-foreground">
                No scoring activity in the last hour
              </p>
            ) : (
              <ul className="divide-y divide-border">
                {data.metrics.top_recent.map((row) => (
                  <li
                    key={row.id}
                    className="grid grid-cols-12 items-center gap-4 px-6 py-4"
                  >
                    <div className="col-span-4 font-mono text-sm text-foreground">
                      {row.transaction_external_id}
                    </div>
                    <div className="col-span-2 text-right font-mono text-sm tabular-nums text-foreground">
                      {row.score}
                    </div>
                    <div className={`col-span-2 font-mono text-[11px] uppercase tracking-[0.22em] ${decisionTone(row.decision)}`}>
                      {row.decision}
                    </div>
                    <div className="col-span-2 font-mono text-[11px] uppercase tracking-[0.22em] text-muted-foreground">
                      {row.cross_bank_flag ? <span className="text-accent">Cross-bank</span> : "Single-bank"}
                    </div>
                    <div className="col-span-2 text-right font-mono text-[11px] uppercase tracking-[0.22em] text-muted-foreground">
                      {fmtMs(row.latency_ms)} · {fmtTime(row.created_at)}
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </Section>

          <Section eyebrow={`Recent stream · ${data.recent.length} rows`}>
            {data.recent.length === 0 ? (
              <p className="px-6 py-6 font-mono text-xs uppercase tracking-[0.22em] text-muted-foreground">
                No recent activity
              </p>
            ) : (
              <ul className="divide-y divide-border">
                {data.recent.map((row) => (
                  <li
                    key={row.id}
                    className="grid grid-cols-12 items-center gap-4 px-6 py-3 text-sm"
                  >
                    <div className="col-span-4 font-mono text-foreground truncate">
                      {row.transaction_external_id}
                    </div>
                    <div className="col-span-1 text-right font-mono tabular-nums text-foreground">
                      {row.score}
                    </div>
                    <div className={`col-span-2 font-mono text-[11px] uppercase tracking-[0.22em] ${decisionTone(row.decision)}`}>
                      {row.decision}
                    </div>
                    <div className="col-span-2 font-mono text-[11px] uppercase tracking-[0.22em] text-muted-foreground">
                      {row.cross_bank_flag ? <span className="text-accent">┼ Cross-bank</span> : "—"}
                    </div>
                    <div className="col-span-1 text-right font-mono text-[11px] uppercase tracking-[0.22em] text-muted-foreground">
                      {fmtMs(row.latency_ms)}
                    </div>
                    <div className="col-span-2 text-right font-mono text-[11px] uppercase tracking-[0.22em] text-muted-foreground">
                      {row.feedback_received && row.feedback_outcome ? (
                        <span className={
                          row.feedback_outcome === "fraud"
                            ? "text-destructive"
                            : row.feedback_outcome === "legitimate"
                              ? "text-foreground"
                              : "text-muted-foreground"
                        }>
                          ┼ {row.feedback_outcome}
                        </span>
                      ) : (
                        fmtTime(row.created_at)
                      )}
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </Section>

          {!isRegulator ? (
            <p className="font-mono text-[10px] uppercase tracking-[0.22em] text-muted-foreground">
              ┼ Bank view · this stream is scoped to your institution. Regulator persona sees the cross-system aggregate.
            </p>
          ) : (
            <p className="font-mono text-[10px] uppercase tracking-[0.22em] text-muted-foreground">
              ┼ Regulator view · cross-system aggregate. Each scoring call is attributed to the issuing bank in audit_log.
            </p>
          )}
        </>
      )}
    </div>
  );
}
