"use client";

import { useEffect, useState } from "react";

import { EmptyState } from "@/components/common/empty-state";
import { ErrorState } from "@/components/common/error-state";
import { LoadingState } from "@/components/common/loading";

interface TaskAccuracy {
  task_name: string;
  total: number;
  corrections: number;
  correction_rate: number;
  avg_latency_ms: number;
}

interface ProviderRow {
  provider: string;
  count: number;
}

interface DashboardPayload {
  window_days: number;
  total_invocations: number;
  total_corrections: number;
  correction_rate: number;
  by_task: TaskAccuracy[];
  by_provider: ProviderRow[];
  outcome_labels: Record<string, number>;
  persona_view: "bank" | "regulator";
  generated_at: string;
}

interface OutcomeRow {
  id: string;
  task_name: string;
  provider: string;
  model: string;
  confidence: number | null;
  outcome_label: string | null;
  has_correction: boolean;
  latency_ms: number;
  prompt_tokens: number | null;
  completion_tokens: number | null;
  fallback_from_provider: string | null;
  request_id: string | null;
  created_at: string | null;
}

const WINDOW_OPTIONS = [
  { label: "7d", value: 7 },
  { label: "30d", value: 30 },
  { label: "90d", value: 90 },
];

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

function fmtPct(value: number): string {
  if (!Number.isFinite(value)) return "—";
  return `${(value * 100).toFixed(1)}%`;
}

function fmtTime(iso: string | null): string {
  if (!iso) return "—";
  try {
    return new Date(iso).toLocaleString("en-GB", {
      day: "2-digit",
      month: "short",
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return iso;
  }
}

export function AIOutcomesDashboard() {
  const [windowDays, setWindowDays] = useState<number>(30);
  const [data, setData] = useState<DashboardPayload | null>(null);
  const [recent, setRecent] = useState<OutcomeRow[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [onlyCorrected, setOnlyCorrected] = useState(false);

  const handleWindowChange = (value: number) => {
    setLoading(true);
    setError(null);
    setWindowDays(value);
  };

  const handleOnlyCorrectedToggle = () => {
    setLoading(true);
    setError(null);
    setOnlyCorrected((prev) => !prev);
  };

  useEffect(() => {
    let cancelled = false;
    Promise.all([
      fetch(`/api/ai/outcomes/dashboard?window_days=${windowDays}`, { cache: "no-store" }),
      fetch(
        `/api/ai/outcomes/recent?limit=50${onlyCorrected ? "&only_corrected=true" : ""}`,
        { cache: "no-store" },
      ),
    ])
      .then(async ([dashRes, recentRes]) => {
        const dashJson = await dashRes.json();
        const recentJson = await recentRes.json();
        if (!dashRes.ok) throw new Error(dashJson.detail ?? "dashboard");
        if (!recentRes.ok) throw new Error(recentJson.detail ?? "recent");
        if (cancelled) return;
        setData(dashJson as DashboardPayload);
        setRecent((recentJson.rows ?? []) as OutcomeRow[]);
      })
      .catch((err: Error) => {
        if (!cancelled) setError(err.message || "Unable to load AI outcomes.");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [windowDays, onlyCorrected]);

  if (loading && !data) return <LoadingState label="Resolving AI outcome corpus" />;
  if (error && !data) return <ErrorState title="Unable to load AI outcomes" description={error} />;
  if (!data) return null;

  return (
    <div className="space-y-8">
      <Section eyebrow={`Filters · ${data.persona_view === "regulator" ? "Regulator view" : "Bank view"}`}>
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
                    windowDays === opt.value
                      ? "bg-foreground text-background"
                      : "text-muted-foreground hover:text-foreground"
                  }`}
                >
                  {opt.label}
                </button>
              ))}
            </div>
          </div>
          <button
            type="button"
            onClick={handleOnlyCorrectedToggle}
            className={`border border-border px-3 py-1.5 font-mono text-[11px] uppercase tracking-[0.22em] transition ${
              onlyCorrected
                ? "bg-foreground text-background"
                : "text-muted-foreground hover:text-foreground"
            }`}
          >
            {onlyCorrected ? "Only corrected · ON" : "Only corrected · OFF"}
          </button>
        </div>
      </Section>

      {data.total_invocations === 0 ? (
        <EmptyState
          title="No AI invocations yet in this window"
          description="ai_outcome_log starts populating as soon as any AI surface is exercised. Run an AI call from /alerts or /strs (Draft narrative) and refresh."
        />
      ) : (
        <>
          <div className="grid grid-cols-1 gap-px border border-border bg-border md:grid-cols-2 lg:grid-cols-4">
            <StatTile
              label="AI invocations"
              value={data.total_invocations.toLocaleString("en-IN")}
              hint={`Window: ${data.window_days}d`}
            />
            <StatTile
              label="Analyst corrections"
              value={data.total_corrections.toLocaleString("en-IN")}
              hint={`Correction rate ${fmtPct(data.correction_rate)}`}
            />
            <StatTile
              label="Tasks tracked"
              value={data.by_task.length}
              hint={data.by_task.map((t) => t.task_name).slice(0, 3).join(", ") || "—"}
            />
            <StatTile
              label="Providers"
              value={data.by_provider.length}
              hint={data.by_provider.map((p) => `${p.provider} (${p.count})`).join(" · ") || "—"}
            />
          </div>

          <Section eyebrow="By task · accuracy proxy">
            {data.by_task.length === 0 ? (
              <p className="px-6 py-6 font-mono text-xs uppercase tracking-[0.22em] text-muted-foreground">
                No task data in this window.
              </p>
            ) : (
              <ul className="divide-y divide-border">
                {data.by_task.map((row) => (
                  <li key={row.task_name} className="grid grid-cols-12 items-center gap-4 px-6 py-4">
                    <div className="col-span-3 font-mono text-sm text-foreground">{row.task_name}</div>
                    <div className="col-span-2 text-right font-mono text-sm tabular-nums text-foreground">
                      {row.total.toLocaleString("en-IN")} calls
                    </div>
                    <div className="col-span-2 text-right font-mono text-sm tabular-nums text-foreground">
                      {row.corrections} corrections
                    </div>
                    <div
                      className={`col-span-2 text-right font-mono text-sm tabular-nums ${
                        row.correction_rate >= 0.3
                          ? "text-destructive"
                          : row.correction_rate >= 0.15
                            ? "text-accent"
                            : "text-foreground"
                      }`}
                    >
                      {fmtPct(row.correction_rate)}
                    </div>
                    <div className="col-span-3 text-right font-mono text-[11px] uppercase tracking-[0.22em] text-muted-foreground">
                      avg {row.avg_latency_ms} ms
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </Section>

          <Section eyebrow={`Recent · ${recent?.length ?? 0}`}>
            {!recent || recent.length === 0 ? (
              <p className="px-6 py-6 font-mono text-xs uppercase tracking-[0.22em] text-muted-foreground">
                No recent activity matches the filter.
              </p>
            ) : (
              <ul className="divide-y divide-border">
                {recent.map((row) => (
                  <li key={row.id} className="grid grid-cols-12 items-center gap-4 px-6 py-3 text-sm">
                    <div className="col-span-3 font-mono text-foreground">{row.task_name}</div>
                    <div className="col-span-2 font-mono text-[11px] uppercase tracking-[0.22em] text-muted-foreground">
                      {row.provider}
                    </div>
                    <div className="col-span-2 font-mono text-[11px] uppercase tracking-[0.22em] text-muted-foreground truncate">
                      {row.model}
                    </div>
                    <div className="col-span-2 text-right font-mono text-[11px] uppercase tracking-[0.22em] text-muted-foreground">
                      {row.latency_ms} ms
                    </div>
                    <div className="col-span-1 text-right">
                      {row.has_correction ? (
                        <span className="font-mono text-[11px] uppercase tracking-[0.22em] text-accent">
                          ┼ {row.outcome_label ?? "edited"}
                        </span>
                      ) : (
                        <span className="font-mono text-[11px] uppercase tracking-[0.22em] text-muted-foreground">—</span>
                      )}
                    </div>
                    <div className="col-span-2 text-right font-mono text-[11px] uppercase tracking-[0.22em] text-muted-foreground">
                      {fmtTime(row.created_at)}
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </Section>
        </>
      )}

      <p className="font-mono text-[10px] uppercase tracking-[0.22em] text-muted-foreground">
        ┼ Generated {fmtTime(data.generated_at)} · {data.persona_view} view ·
        {" "}corpus exports for V3 phase 4 fine-tune harness will read from this same table.
      </p>
    </div>
  );
}
