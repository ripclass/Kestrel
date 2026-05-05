"use client";

import { useEffect, useState } from "react";

interface StatusComponent {
  component: string;
  status: "up" | "degraded" | "down" | "unknown";
  latency_ms: number | null;
  detail: string | null;
  observed_at: string | null;
  uptime_30d: number;
  uptime_90d: number;
}

interface StatusIncident {
  id: string;
  started_at: string | null;
  ended_at: string | null;
  severity: "minor" | "major" | "outage";
  component: string;
  summary: string;
  message: string | null;
  is_active: boolean;
}

interface StatusSummary {
  status: "up" | "degraded" | "down";
  components: StatusComponent[];
  incidents: StatusIncident[];
  overall_uptime_30d: number;
  generated_at: string;
}

const REFRESH_MS = 60_000;

const COMPONENT_LABEL: Record<string, string> = {
  auth: "Authentication",
  database: "Database",
  redis: "Redis",
  storage: "Storage",
  worker: "Worker",
  ai: "AI providers",
};

function statusTone(status: string): string {
  if (status === "up") return "text-landing-foreground";
  if (status === "degraded") return "text-landing-accent";
  if (status === "down") return "text-red-500";
  return "text-landing-foreground/40";
}

function statusBadge(status: string): string {
  if (status === "up") return "Operational";
  if (status === "degraded") return "Degraded";
  if (status === "down") return "Outage";
  return "Unknown";
}

function severityTone(severity: string): string {
  if (severity === "outage") return "text-red-500";
  if (severity === "major") return "text-landing-accent";
  return "text-landing-foreground/70";
}

function fmtPct(value: number): string {
  if (!Number.isFinite(value)) return "—";
  return `${(value * 100).toFixed(2)}%`;
}

function fmtRelative(iso: string | null): string {
  if (!iso) return "never";
  try {
    const dt = new Date(iso);
    const diff = Date.now() - dt.getTime();
    if (diff < 0) return "just now";
    const minutes = Math.round(diff / 60_000);
    if (minutes < 1) return "just now";
    if (minutes < 60) return `${minutes}m ago`;
    const hours = Math.round(minutes / 60);
    if (hours < 24) return `${hours}h ago`;
    const days = Math.round(hours / 24);
    return `${days}d ago`;
  } catch {
    return iso;
  }
}

function fmtDate(iso: string | null): string {
  if (!iso) return "—";
  try {
    return new Date(iso).toLocaleString("en-GB", {
      day: "2-digit",
      month: "short",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return iso;
  }
}

export function StatusBoard() {
  const [data, setData] = useState<StatusSummary | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    const fetchData = () => {
      fetch(`/api/status/summary`, { cache: "no-store" })
        .then(async (r) => {
          const json = await r.json();
          if (!r.ok) throw new Error(json.detail ?? "status");
          if (!cancelled) setData(json as StatusSummary);
        })
        .catch((err: Error) => {
          if (!cancelled) setError(err.message || "Unable to load status.");
        })
        .finally(() => {
          if (!cancelled) setLoading(false);
        });
    };
    fetchData();
    const handle = window.setInterval(fetchData, REFRESH_MS);
    return () => {
      cancelled = true;
      window.clearInterval(handle);
    };
  }, []);

  if (loading && !data) {
    return (
      <p className="font-mono text-xs uppercase tracking-[0.22em] text-landing-foreground/60">
        ┼ Loading status…
      </p>
    );
  }
  if (error && !data) {
    return (
      <p className="font-mono text-xs uppercase tracking-[0.22em] text-red-500">
        ┼ ERROR · {error}
      </p>
    );
  }
  if (!data) return null;

  return (
    <div className="space-y-12">
      <section className="border border-landing-foreground/10 p-8">
        <p className="font-mono text-[10px] uppercase tracking-[0.32em] text-landing-foreground/60">
          <span aria-hidden className="mr-2 text-landing-accent">┼</span>
          Overall
        </p>
        <p className={`mt-4 text-4xl font-semibold tracking-tight ${statusTone(data.status)}`}>
          {statusBadge(data.status)}
        </p>
        <p className="mt-2 font-mono text-xs uppercase tracking-[0.22em] text-landing-foreground/60">
          30-day uptime · {fmtPct(data.overall_uptime_30d)} · last refresh {fmtRelative(data.generated_at)}
        </p>
      </section>

      <section className="space-y-px border border-landing-foreground/10 bg-landing-foreground/10">
        {data.components.map((c) => (
          <article key={c.component} className="grid grid-cols-12 items-center gap-4 bg-landing-bg px-6 py-5">
            <div className="col-span-3">
              <p className="font-mono text-sm text-landing-foreground">
                {COMPONENT_LABEL[c.component] ?? c.component}
              </p>
              <p className="font-mono text-[10px] uppercase tracking-[0.22em] text-landing-foreground/60">
                last ping {fmtRelative(c.observed_at)}
              </p>
            </div>
            <div className={`col-span-2 font-mono text-sm uppercase tracking-[0.18em] ${statusTone(c.status)}`}>
              {statusBadge(c.status)}
            </div>
            <div className="col-span-2 font-mono text-sm text-landing-foreground/70 tabular-nums">
              {fmtPct(c.uptime_30d)} <span className="text-landing-foreground/40">· 30d</span>
            </div>
            <div className="col-span-2 font-mono text-sm text-landing-foreground/70 tabular-nums">
              {fmtPct(c.uptime_90d)} <span className="text-landing-foreground/40">· 90d</span>
            </div>
            <div className="col-span-3 font-mono text-[11px] uppercase tracking-[0.18em] text-landing-foreground/60 truncate">
              {c.detail ?? "—"}
            </div>
          </article>
        ))}
      </section>

      <section>
        <p className="font-mono text-[10px] uppercase tracking-[0.32em] text-landing-foreground/60">
          <span aria-hidden className="mr-2 text-landing-accent">┼</span>
          Recent incidents · {data.incidents.length}
        </p>
        {data.incidents.length === 0 ? (
          <p className="mt-3 font-mono text-xs uppercase tracking-[0.22em] text-landing-foreground/60">
            No recent incidents reported.
          </p>
        ) : (
          <ul className="mt-4 space-y-3">
            {data.incidents.map((i) => (
              <li key={i.id} className="border border-landing-foreground/10 p-5">
                <div className="flex flex-wrap items-center gap-3">
                  <span className={`font-mono text-[11px] uppercase tracking-[0.22em] ${severityTone(i.severity)}`}>
                    {i.severity}
                  </span>
                  <span className="font-mono text-[11px] uppercase tracking-[0.22em] text-landing-foreground/60">
                    {i.component}
                  </span>
                  <span
                    className={`font-mono text-[10px] uppercase tracking-[0.22em] ${
                      i.is_active ? "text-landing-accent" : "text-landing-foreground/40"
                    }`}
                  >
                    {i.is_active ? "active" : "resolved"}
                  </span>
                </div>
                <p className="mt-3 text-base text-landing-foreground">{i.summary}</p>
                {i.message ? (
                  <p className="mt-2 whitespace-pre-line font-mono text-xs text-landing-foreground/70">
                    {i.message}
                  </p>
                ) : null}
                <p className="mt-3 font-mono text-[10px] uppercase tracking-[0.22em] text-landing-foreground/40">
                  Started {fmtDate(i.started_at)}
                  {i.ended_at ? ` · resolved ${fmtDate(i.ended_at)}` : ""}
                </p>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}
