"use client";

import { useCallback, useEffect, useState } from "react";

import { ErrorState } from "@/components/common/error-state";
import { LoadingState } from "@/components/common/loading";

interface Component {
  name: string;
  status: string;
  required: boolean;
  detail: string | null;
}

interface UptimeComponent {
  component: string;
  status: string;
  uptime_30d: number;
  uptime_90d: number;
}

interface Incident {
  id: string;
  severity: string;
  component: string;
  summary: string;
  is_active: boolean;
  started_at: string | null;
}

interface SystemHealth {
  status: string;
  version: string;
  environment: string;
  components: Component[];
  uptime: {
    overall_status?: string;
    overall_uptime_30d?: number;
    components?: UptimeComponent[];
    incidents?: Incident[];
  };
  generated_at: string;
}

const REFRESH_MS = 60_000;

/** ok → normal, error → alarm, everything else (missing_config / skipped /
 *  degraded / unknown) → muted. */
function tone(status: string): string {
  const s = status.toLowerCase();
  if (s === "ok" || s === "up" || s === "ready") return "text-foreground";
  if (s === "error" || s === "down" || s === "not_ready") return "text-accent";
  return "text-muted-foreground";
}

function pct(value: number | undefined): string {
  if (typeof value !== "number") return "—";
  return `${(value * 100).toFixed(2)}%`;
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

export function SystemHealthPanel() {
  const [data, setData] = useState<SystemHealth | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    setError(null);
    try {
      const r = await fetch(`/api/platform/system-health`, { cache: "no-store" });
      const json = await r.json();
      if (!r.ok) throw new Error(json.detail ?? "system health");
      setData(json as SystemHealth);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to load system health.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refresh();
    const timer = setInterval(refresh, REFRESH_MS);
    return () => clearInterval(timer);
  }, [refresh]);

  if (loading && !data) {
    return <LoadingState label="Loading system health" />;
  }
  if (!data) {
    return <ErrorState title="Unable to load system health" description={error ?? "—"} />;
  }

  const uptimeComponents = data.uptime.components ?? [];
  const incidents = (data.uptime.incidents ?? []).filter((i) => i.is_active);

  return (
    <div className="space-y-8">
      {error ? (
        <p className="font-mono text-xs uppercase tracking-[0.18em] text-destructive">
          ┼ ERROR · {error}
        </p>
      ) : null}

      <div className="grid grid-cols-2 gap-px md:grid-cols-4">
        <div className="border border-border px-5 py-4">
          <p className="font-mono text-[10px] uppercase tracking-[0.22em] text-muted-foreground">
            Readiness
          </p>
          <p className={`mt-2 font-mono text-2xl uppercase ${tone(data.status)}`}>
            {data.status}
          </p>
        </div>
        <div className="border border-border px-5 py-4">
          <p className="font-mono text-[10px] uppercase tracking-[0.22em] text-muted-foreground">
            Uptime · 30d
          </p>
          <p className="mt-2 font-mono text-2xl tabular-nums text-foreground">
            {pct(data.uptime.overall_uptime_30d)}
          </p>
        </div>
        <div className="border border-border px-5 py-4">
          <p className="font-mono text-[10px] uppercase tracking-[0.22em] text-muted-foreground">
            Environment
          </p>
          <p className="mt-2 font-mono text-lg text-foreground">{data.environment}</p>
        </div>
        <div className="border border-border px-5 py-4">
          <p className="font-mono text-[10px] uppercase tracking-[0.22em] text-muted-foreground">
            Version
          </p>
          <p className="mt-2 font-mono text-lg text-foreground">{data.version}</p>
        </div>
      </div>

      <Section eyebrow={`Live component probes · ${data.components.length}`}>
        <ul className="divide-y divide-border">
          {data.components.map((c) => (
            <li
              key={c.name}
              className="flex flex-wrap items-baseline gap-x-4 gap-y-1 px-6 py-4"
            >
              <span className="font-mono text-sm text-foreground">{c.name}</span>
              <span className={`font-mono text-[11px] uppercase tracking-[0.2em] ${tone(c.status)}`}>
                ● {c.status}
              </span>
              {!c.required ? (
                <span className="font-mono text-[10px] uppercase tracking-[0.2em] text-muted-foreground">
                  optional
                </span>
              ) : null}
              {c.detail ? (
                <span className="ml-auto max-w-xl text-right font-mono text-[11px] text-muted-foreground">
                  {c.detail}
                </span>
              ) : null}
            </li>
          ))}
        </ul>
      </Section>

      {uptimeComponents.length > 0 ? (
        <Section eyebrow="Uptime by component · 30d / 90d">
          <ul className="divide-y divide-border">
            {uptimeComponents.map((c) => (
              <li
                key={c.component}
                className="flex flex-wrap items-baseline gap-x-4 px-6 py-3 font-mono text-[12px]"
              >
                <span className="text-foreground">{c.component}</span>
                <span className={`text-[11px] uppercase tracking-[0.2em] ${tone(c.status)}`}>
                  ● {c.status}
                </span>
                <span className="ml-auto tabular-nums text-muted-foreground">
                  30d <span className="text-foreground">{pct(c.uptime_30d)}</span> · 90d{" "}
                  <span className="text-foreground">{pct(c.uptime_90d)}</span>
                </span>
              </li>
            ))}
          </ul>
        </Section>
      ) : null}

      <Section eyebrow={`Active incidents · ${incidents.length}`}>
        {incidents.length === 0 ? (
          <p className="px-6 py-5 font-mono text-xs uppercase tracking-[0.22em] text-muted-foreground">
            No active incidents.
          </p>
        ) : (
          <ul className="divide-y divide-border">
            {incidents.map((i) => (
              <li key={i.id} className="space-y-1 px-6 py-4">
                <div className="flex flex-wrap items-center gap-3">
                  <span className="font-mono text-[11px] uppercase tracking-[0.2em] text-accent">
                    {i.severity}
                  </span>
                  <span className="font-mono text-[11px] uppercase tracking-[0.2em] text-muted-foreground">
                    {i.component}
                  </span>
                </div>
                <p className="text-sm text-foreground">{i.summary}</p>
              </li>
            ))}
          </ul>
        )}
      </Section>
    </div>
  );
}
