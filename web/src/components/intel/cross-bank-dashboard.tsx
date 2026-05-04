"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

import { EmptyState } from "@/components/common/empty-state";
import { ErrorState } from "@/components/common/error-state";
import { LoadingState } from "@/components/common/loading";
import { RiskScore } from "@/components/common/risk-score";
import { SeverityPill } from "@/components/common/severity-pill";
import type {
  CrossBankEntityRow,
  CrossBankHeatmap,
  CrossBankMatchView,
  CrossBankSummary,
  Viewer,
} from "@/types/domain";

const WINDOW_OPTIONS = [
  { label: "7d", value: 7 },
  { label: "30d", value: 30 },
  { label: "90d", value: 90 },
];

const SEVERITY_OPTIONS: Array<{ label: string; value: string }> = [
  { label: "ALL", value: "" },
  { label: "CRITICAL", value: "critical" },
  { label: "HIGH", value: "high" },
  { label: "MEDIUM", value: "medium" },
  { label: "LOW", value: "low" },
];

function fmtBdt(n: number): string {
  if (!Number.isFinite(n)) return "—";
  if (n === 0) return "BDT 0";
  if (n >= 1e7) return `BDT ${(n / 1e7).toFixed(2)} cr`;
  if (n >= 1e5) return `BDT ${(n / 1e5).toFixed(2)} lakh`;
  return `BDT ${n.toLocaleString("en-IN")}`;
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
  summary: CrossBankSummary;
  matches: CrossBankMatchView[];
  heatmap: CrossBankHeatmap;
  entities: CrossBankEntityRow[];
}

export function CrossBankDashboard({ viewer }: { viewer: Viewer }) {
  const [windowDays, setWindowDays] = useState<number>(30);
  const [severity, setSeverity] = useState<string>("");
  const [data, setData] = useState<DashboardData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);

    const params = new URLSearchParams();
    params.set("window_days", String(windowDays));
    const matchesParams = new URLSearchParams(params);
    if (severity) matchesParams.set("severity", severity);

    Promise.all([
      fetch(`/api/intelligence/cross-bank/summary?${params.toString()}`, { cache: "no-store" }),
      fetch(`/api/intelligence/cross-bank/matches?${matchesParams.toString()}`, { cache: "no-store" }),
      fetch(`/api/intelligence/cross-bank/heatmap?${params.toString()}`, { cache: "no-store" }),
      fetch(`/api/intelligence/cross-bank/top-entities?${params.toString()}`, { cache: "no-store" }),
    ])
      .then(async ([s, m, h, e]) => {
        const [sj, mj, hj, ej] = await Promise.all([s.json(), m.json(), h.json(), e.json()]);
        if (!s.ok) throw new Error(sj.detail ?? "summary");
        if (!m.ok) throw new Error(mj.detail ?? "matches");
        if (!h.ok) throw new Error(hj.detail ?? "heatmap");
        if (!e.ok) throw new Error(ej.detail ?? "top-entities");
        if (cancelled) return;
        setData({
          summary: sj.summary as CrossBankSummary,
          matches: mj.matches as CrossBankMatchView[],
          heatmap: hj.heatmap as CrossBankHeatmap,
          entities: ej.entities as CrossBankEntityRow[],
        });
      })
      .catch((err: Error) => {
        if (cancelled) return;
        setError(err.message || "Unable to load cross-bank intelligence.");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [windowDays, severity]);

  const personaView = data?.summary.personaView ?? "bank";
  const isRegulator = viewer.persona === "bfiu_director" || viewer.persona === "bfiu_analyst";
  const heatmapMax = useMemo(() => {
    return Math.max(1, ...(data?.heatmap.buckets.map((b) => b.matchCount) ?? [0]));
  }, [data?.heatmap.buckets]);

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
                  onClick={() => setWindowDays(opt.value)}
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

          <div className="flex items-center gap-2">
            <span className="font-mono text-[10px] uppercase tracking-[0.22em] text-muted-foreground">Severity</span>
            <div className="flex border border-border">
              {SEVERITY_OPTIONS.map((opt) => (
                <button
                  key={opt.value || "all"}
                  type="button"
                  onClick={() => setSeverity(opt.value)}
                  className={`px-3 py-1.5 font-mono text-[11px] uppercase tracking-[0.22em] transition ${
                    severity === opt.value
                      ? "bg-foreground text-background"
                      : "text-muted-foreground hover:text-foreground"
                  }`}
                >
                  {opt.label}
                </button>
              ))}
            </div>
          </div>
        </div>
      </Section>

      {loading ? (
        <LoadingState label="Resolving cross-bank intelligence" />
      ) : error ? (
        <ErrorState title="Unable to load cross-bank intelligence" description={error} />
      ) : !data ? (
        <EmptyState
          title="No cross-bank intelligence yet"
          description="No matches resolved in the selected window."
        />
      ) : (
        <>
          <div className="grid grid-cols-1 gap-px border border-border bg-border md:grid-cols-2 lg:grid-cols-4">
            <StatTile
              label="Entities flagged across institutions"
              value={data.summary.entitiesFlaggedAcrossBanks}
              hint={`Across ${data.summary.visibleMatchesCount} match clusters`}
            />
            <StatTile
              label="New cross-bank flags · 7d"
              value={data.summary.newThisWeek}
              hint={`Window: ${data.summary.windowDays}d`}
            />
            <StatTile
              label="High-risk cross-institution"
              value={data.summary.highRiskCrossInstitution}
              hint="Risk ≥ 70 · ≥ 2 banks"
            />
            <StatTile
              label="Aggregate exposure"
              value={fmtBdt(data.summary.totalExposure)}
              hint={`${data.summary.crossBankAlertsCount} cross-bank alerts`}
            />
          </div>

          <Section
            eyebrow={`Heatmap · ${
              personaView === "regulator" ? "By institution" : "Your institution vs peers"
            }`}
          >
            {data.heatmap.buckets.length === 0 ? (
              <p className="px-6 py-6 font-mono text-xs uppercase tracking-[0.22em] text-muted-foreground">
                No cross-bank activity in the selected window
              </p>
            ) : (
              <ul className="divide-y divide-border">
                {data.heatmap.buckets.map((bucket) => {
                  const ratio = bucket.matchCount / heatmapMax;
                  return (
                    <li key={bucket.label} className="grid grid-cols-12 items-center gap-4 px-6 py-4">
                      <div className="col-span-4 font-mono text-sm text-foreground">{bucket.label}</div>
                      <div className="col-span-6">
                        <div
                          aria-hidden
                          className="h-3 border border-border bg-background"
                        >
                          <div
                            className="h-full bg-accent"
                            style={{ width: `${Math.max(2, ratio * 100)}%` }}
                          />
                        </div>
                        <div className="mt-1 flex gap-3 font-mono text-[10px] uppercase tracking-[0.18em] text-muted-foreground">
                          {(["critical", "high", "medium", "low"] as const).map((sev) => {
                            const v = bucket.severityBreakdown[sev];
                            if (!v) return null;
                            return (
                              <span key={sev}>
                                {sev}: <span className="tabular-nums text-foreground">{v}</span>
                              </span>
                            );
                          })}
                        </div>
                      </div>
                      <div className="col-span-2 text-right font-mono text-sm tabular-nums text-foreground">
                        {bucket.matchCount}
                      </div>
                    </li>
                  );
                })}
              </ul>
            )}
          </Section>

          <Section eyebrow={`Recent cross-bank matches · ${data.matches.length}`}>
            {data.matches.length === 0 ? (
              <p className="px-6 py-6 font-mono text-xs uppercase tracking-[0.22em] text-muted-foreground">
                No matches in the selected window
              </p>
            ) : (
              <ul className="divide-y divide-border">
                {data.matches.map((match) => (
                  <li key={match.id}>
                    <Link
                      href={match.entityId ? `/investigate/entity/${match.entityId}` : "/intelligence/matches"}
                      className="grid grid-cols-12 items-center gap-4 px-6 py-4 transition hover:bg-foreground/[0.03]"
                    >
                      <div className="col-span-4 flex flex-col gap-1">
                        <p className="font-mono text-sm text-foreground">{match.matchKey || "—"}</p>
                        <p className="font-mono text-[10px] uppercase tracking-[0.22em] text-muted-foreground">
                          {match.matchType}
                        </p>
                      </div>
                      <div className="col-span-4 font-mono text-[11px] uppercase tracking-[0.22em] text-muted-foreground">
                        {match.involvedOrgs.join(" · ")}
                      </div>
                      <div className="col-span-2 font-mono text-[11px] uppercase tracking-[0.22em] text-foreground">
                        {match.bankCount} banks · {match.matchCount} hits
                      </div>
                      <div className="col-span-1">
                        <SeverityPill severity={match.severity} />
                      </div>
                      <div className="col-span-1 text-right">
                        <RiskScore score={match.riskScore} severity={match.severity} />
                      </div>
                    </Link>
                  </li>
                ))}
              </ul>
            )}
          </Section>

          <Section eyebrow="Top cross-flagged entities">
            {data.entities.length === 0 ? (
              <p className="px-6 py-6 font-mono text-xs uppercase tracking-[0.22em] text-muted-foreground">
                No flagged entities reach the threshold (risk + ≥ 2 banks)
              </p>
            ) : (
              <ul className="divide-y divide-border">
                {data.entities.map((entity) => (
                  <li key={entity.entityId}>
                    <Link
                      href={`/investigate/entity/${entity.entityId}`}
                      className="grid grid-cols-12 items-center gap-4 px-6 py-4 transition hover:bg-foreground/[0.03]"
                    >
                      <div className="col-span-5 flex flex-col gap-1">
                        <p className="font-mono text-sm text-foreground">{entity.display}</p>
                        <p className="font-mono text-[10px] uppercase tracking-[0.22em] text-muted-foreground">
                          {entity.entityType}
                        </p>
                      </div>
                      <div className="col-span-4 font-mono text-[11px] uppercase tracking-[0.22em] text-muted-foreground">
                        {entity.involvedOrgs.join(" · ")}
                      </div>
                      <div className="col-span-1 font-mono text-[11px] uppercase tracking-[0.22em] text-foreground">
                        {entity.bankCount} banks
                      </div>
                      <div className="col-span-1">
                        <SeverityPill severity={entity.severity} />
                      </div>
                      <div className="col-span-1 text-right">
                        <RiskScore score={entity.riskScore} severity={entity.severity} />
                      </div>
                    </Link>
                  </li>
                ))}
              </ul>
            )}
          </Section>

          {!isRegulator ? (
            <p className="font-mono text-[10px] uppercase tracking-[0.22em] text-muted-foreground">
              ┼ Bank view · peer-institution names are anonymised. Match-key tails redacted to last 4 characters.
            </p>
          ) : null}
        </>
      )}
    </div>
  );
}
