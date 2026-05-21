"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import Link from "next/link";

import type { PredicateOffence } from "@/types/domain";
import { PREDICATE_OFFENCE_LABELS } from "@/types/domain";

type TbmlAlert = {
  id: string;
  alert_type: string;
  title: string;
  severity: "critical" | "high" | "medium" | "low";
  risk_score: number;
  status: string;
  bfiu_avenue_ref: string | null;
  predicate_offences: PredicateOffence[];
  linked_trade_id: string | null;
  created_at: string | null;
};

type MultiInvoicingGroup = {
  match_kind: "bl" | "lc";
  match_key: string;
  distinct_orgs_count: number;
  involved_orgs: string[];
  trade_count: number;
  aggregate_invoice_value: number;
  currency: string;
  sample_trade_refs: string[];
};

type CountryHeatmapRow = {
  country: string;
  trade_count: number;
  flagged_count: number;
  total_value: number;
};

type TbmlSummary = {
  window_days: number;
  persona_view: "bank" | "regulator";
  stats: {
    total_alerts: number;
    critical_alerts: number;
    high_alerts: number;
    flagged_trades: number;
    multi_invoicing_clusters: number;
  };
  multi_invoicing: MultiInvoicingGroup[];
  country_pair_heatmap: CountryHeatmapRow[];
  recent_alerts: TbmlAlert[];
};

const WINDOWS = [
  { value: 7, label: "7d" },
  { value: 30, label: "30d" },
  { value: 90, label: "90d" },
];

function formatBdt(value: number, currency: string): string {
  const symbol = currency === "USD" ? "USD" : currency;
  return `${symbol} ${value.toLocaleString(undefined, { maximumFractionDigits: 0 })}`;
}

function severityToneClass(severity: string): string {
  switch (severity) {
    case "critical":
      return "text-destructive";
    case "high":
      return "text-accent";
    case "medium":
      return "text-foreground";
    default:
      return "text-muted-foreground";
  }
}

export function TbmlDashboard() {
  const [windowDays, setWindowDays] = useState(30);
  const [summary, setSummary] = useState<TbmlSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const reload = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const resp = await fetch(`/api/intelligence/tbml?window_days=${windowDays}`, { cache: "no-store" });
      const body = await resp.json();
      if (!resp.ok) {
        setError(typeof body?.detail === "string" ? body.detail : "Unable to load TBML summary.");
        return;
      }
      setSummary(body as TbmlSummary);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Network error loading TBML summary.");
    } finally {
      setLoading(false);
    }
  }, [windowDays]);

  useEffect(() => {
    void reload();
    const handle = setInterval(() => void reload(), 60_000);
    return () => clearInterval(handle);
  }, [reload]);

  const stats = summary?.stats;
  const recent = useMemo(() => summary?.recent_alerts ?? [], [summary]);
  const multi = useMemo(() => summary?.multi_invoicing ?? [], [summary]);
  const heatmap = useMemo(() => summary?.country_pair_heatmap ?? [], [summary]);
  const maxFlagged = useMemo(
    () => Math.max(1, ...heatmap.map((row) => row.flagged_count)),
    [heatmap],
  );

  return (
    <div className="space-y-8">
      <header className="border border-border">
        <div className="flex flex-col gap-3 border-b border-border px-6 py-5 md:flex-row md:items-center md:justify-between">
          <div className="space-y-1">
            <p className="font-mono text-[10px] uppercase tracking-[0.28em] text-muted-foreground">
              <span aria-hidden className="mr-2 text-accent">┼</span>
              Filters · {summary?.persona_view === "regulator" ? "Regulator view" : "Bank view"}
            </p>
            <h1 className="text-2xl font-semibold text-foreground">TBML detection</h1>
            <p className="text-sm text-muted-foreground">
              Trade-based money laundering coverage aligned to BFIU TBML Guidelines 2019.
              Each alert auto-cites the §2.4.x.y avenue and MLPA §2(cc) predicate offences.
            </p>
          </div>
          <div className="flex items-center gap-2">
            <span className="font-mono text-[10px] uppercase tracking-[0.22em] text-muted-foreground">
              Window
            </span>
            <div className="flex border border-border">
              {WINDOWS.map((option) => (
                <button
                  key={option.value}
                  type="button"
                  onClick={() => setWindowDays(option.value)}
                  className={`px-4 py-2 font-mono text-[11px] uppercase tracking-[0.22em] transition ${
                    windowDays === option.value
                      ? "bg-foreground text-background"
                      : "text-muted-foreground hover:text-foreground"
                  }`}
                >
                  {option.label}
                </button>
              ))}
            </div>
          </div>
        </div>

        {error ? (
          <p className="border-b border-destructive/40 px-6 py-3 font-mono text-xs uppercase tracking-[0.18em] text-destructive">
            <span aria-hidden className="mr-2">┼</span>ERROR · {error}
          </p>
        ) : null}

        <div className="grid grid-cols-2 gap-px bg-border md:grid-cols-5">
          <Tile label="Total TBML alerts" value={stats?.total_alerts ?? 0} loading={loading} />
          <Tile label="Critical" value={stats?.critical_alerts ?? 0} loading={loading} tone="text-destructive" />
          <Tile label="High" value={stats?.high_alerts ?? 0} loading={loading} tone="text-accent" />
          <Tile label="Flagged trades" value={stats?.flagged_trades ?? 0} loading={loading} />
          <Tile label="Multi-invoice clusters" value={stats?.multi_invoicing_clusters ?? 0} loading={loading} />
        </div>
      </header>

      <section className="border border-border">
        <div className="border-b border-border px-6 py-5">
          <p className="font-mono text-[10px] uppercase tracking-[0.28em] text-muted-foreground">
            <span aria-hidden className="mr-2 text-accent">┼</span>
            Section · Multi-invoicing clusters
          </p>
          <h2 className="mt-2 text-lg font-semibold text-foreground">
            Same B/L or LC reference across institutions
          </h2>
          <p className="text-sm text-muted-foreground">
            Trades sharing a Bill of Lading or LC reference at two or more banks — BFIU Alert #18 + the cross-bank intelligence dimension.
          </p>
        </div>
        {multi.length === 0 ? (
          <p className="px-6 py-5 font-mono text-xs uppercase tracking-[0.18em] text-muted-foreground">
            ┼ No multi-invoicing clusters in this window.
          </p>
        ) : (
          <ul className="divide-y divide-border">
            {multi.map((group) => (
              <li
                key={`${group.match_kind}:${group.match_key}`}
                className="grid grid-cols-1 gap-3 px-6 py-4 md:grid-cols-[1fr_auto_auto] md:items-center"
              >
                <div className="space-y-1">
                  <p className="font-mono text-xs uppercase tracking-[0.18em] text-muted-foreground">
                    {group.match_kind === "bl" ? "B/L" : "LC"} · {group.match_key}
                  </p>
                  <p className="text-sm text-foreground">{group.involved_orgs.join(" · ")}</p>
                  <p className="font-mono text-[10px] uppercase tracking-[0.18em] text-muted-foreground">
                    {group.sample_trade_refs.join(" · ")}
                  </p>
                </div>
                <div className="text-right">
                  <p className="font-mono text-xs uppercase tracking-[0.18em] text-muted-foreground">
                    {group.distinct_orgs_count} banks · {group.trade_count} trades
                  </p>
                </div>
                <div className="text-right font-mono text-sm tabular-nums text-foreground">
                  {formatBdt(group.aggregate_invoice_value, group.currency)}
                </div>
              </li>
            ))}
          </ul>
        )}
      </section>

      <section className="border border-border">
        <div className="border-b border-border px-6 py-5">
          <p className="font-mono text-[10px] uppercase tracking-[0.28em] text-muted-foreground">
            <span aria-hidden className="mr-2 text-accent">┼</span>
            Section · Country-pair heatmap
          </p>
          <h2 className="mt-2 text-lg font-semibold text-foreground">Trade volume by counterparty country</h2>
          <p className="text-sm text-muted-foreground">
            Flagged-trade overlay surfaces which jurisdictions concentrate TBML risk.
          </p>
        </div>
        {heatmap.length === 0 ? (
          <p className="px-6 py-5 font-mono text-xs uppercase tracking-[0.18em] text-muted-foreground">
            ┼ No trade transactions recorded in this window.
          </p>
        ) : (
          <ul className="divide-y divide-border">
            {heatmap.map((row) => {
              const intensity = Math.min(1, row.flagged_count / maxFlagged);
              return (
                <li key={row.country} className="grid grid-cols-[auto_1fr_auto_auto] items-center gap-4 px-6 py-3">
                  <p className="font-mono text-sm uppercase tracking-[0.18em] text-foreground">{row.country}</p>
                  <div className="h-2 bg-border">
                    <div
                      className="h-full bg-accent transition-all"
                      style={{ width: `${Math.round(intensity * 100)}%` }}
                    />
                  </div>
                  <p className="font-mono text-xs uppercase tracking-[0.18em] text-muted-foreground">
                    {row.trade_count} trades · {row.flagged_count} flagged
                  </p>
                  <p className="font-mono text-sm tabular-nums text-foreground">
                    {formatBdt(row.total_value, "USD")}
                  </p>
                </li>
              );
            })}
          </ul>
        )}
      </section>

      <section className="border border-border">
        <div className="border-b border-border px-6 py-5">
          <p className="font-mono text-[10px] uppercase tracking-[0.28em] text-muted-foreground">
            <span aria-hidden className="mr-2 text-accent">┼</span>
            Section · Recent TBML alerts
          </p>
          <h2 className="mt-2 text-lg font-semibold text-foreground">
            Last {recent.length || 0} alerts on the wire
          </h2>
        </div>
        {recent.length === 0 ? (
          <p className="px-6 py-5 font-mono text-xs uppercase tracking-[0.18em] text-muted-foreground">
            ┼ No TBML alerts in this window.
          </p>
        ) : (
          <ul className="divide-y divide-border">
            {recent.map((alert) => (
              <li key={alert.id} className="space-y-2 px-6 py-4">
                <div className="flex items-start justify-between gap-3">
                  <div className="space-y-1">
                    <Link
                      href={`/alerts/${alert.id}`}
                      className="block font-mono text-xs uppercase tracking-[0.18em] text-foreground hover:text-accent"
                    >
                      {alert.title}
                    </Link>
                    <p className="font-mono text-[10px] uppercase tracking-[0.22em] text-muted-foreground">
                      {alert.alert_type}
                      {alert.bfiu_avenue_ref ? (
                        <span className="ml-2 text-accent">┼ BFIU §{alert.bfiu_avenue_ref}</span>
                      ) : null}
                    </p>
                  </div>
                  <p className={`font-mono text-xs uppercase tracking-[0.18em] ${severityToneClass(alert.severity)}`}>
                    {alert.severity} · {alert.risk_score}/100
                  </p>
                </div>
                {alert.predicate_offences.length > 0 ? (
                  <div className="flex flex-wrap gap-2">
                    {alert.predicate_offences.map((code) => (
                      <span
                        key={code}
                        className="border border-accent/40 px-2 py-0.5 font-mono text-[10px] uppercase tracking-[0.18em] text-accent"
                      >
                        {PREDICATE_OFFENCE_LABELS[code]}
                      </span>
                    ))}
                  </div>
                ) : null}
              </li>
            ))}
          </ul>
        )}
      </section>

      {summary?.persona_view === "bank" ? (
        <footer className="border-t border-border px-6 py-4">
          <p className="font-mono text-[10px] uppercase tracking-[0.22em] text-muted-foreground">
            ┼ Bank view · peer-institution names anonymised · match-key tails redacted to last 4 characters.
          </p>
        </footer>
      ) : null}
    </div>
  );
}

function Tile({
  label,
  value,
  loading,
  tone,
}: {
  label: string;
  value: number;
  loading: boolean;
  tone?: string;
}) {
  return (
    <div className="bg-background px-5 py-4">
      <p className="font-mono text-[10px] uppercase tracking-[0.22em] text-muted-foreground">{label}</p>
      <p className={`mt-2 font-mono text-2xl tabular-nums ${tone ?? "text-foreground"}`}>
        {loading ? "…" : value.toLocaleString()}
      </p>
    </div>
  );
}
