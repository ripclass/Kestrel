"use client";

import { useCallback, useEffect, useState } from "react";

import { ErrorState } from "@/components/common/error-state";
import { LoadingState } from "@/components/common/loading";

type Engagement = "active" | "idle" | "dormant" | "never";
type Trend = "rising" | "falling" | "flat" | "new";
type TenantKind = "demo" | "pilot" | "live";

interface PilotCard {
  org_id: string;
  org_name: string;
  org_type: string;
  plan_id: string;
  tenant_kind: TenantKind;
  created_at: string | null;
  seats: number;
  seats_logged_in: number;
  last_login_at: string | null;
  last_activity_at: string | null;
  engagement: Engagement;
  actions_7d: number;
  actions_prev_7d: number;
  actions_30d: number;
  trend: Trend;
  active_users_7d: number;
  strs: number;
  alerts: number;
  cases: number;
  scans: number;
}

interface PlatformSummary {
  tenants_total: number;
  tenants_bank: number;
  tenants_active_7d: number;
  seats_total: number;
  seats_logged_in: number;
  actions_7d: number;
  strs_total: number;
  alerts_total: number;
  cases_total: number;
  generated_at: string;
}

interface Overview {
  summary: PlatformSummary;
  pilots: PilotCard[];
}

interface PilotUser {
  user_id: string;
  full_name: string | null;
  role: string | null;
  persona: string | null;
  designation: string | null;
  last_login_at: string | null;
  last_activity_at: string | null;
  actions_7d: number;
  actions_30d: number;
  engagement: Engagement;
}

interface AuditEntry {
  created_at: string | null;
  action: string;
  resource_type: string | null;
  user_id: string | null;
}

interface PilotDetail {
  card: PilotCard;
  users: PilotUser[];
  recent_actions: AuditEntry[];
  action_breakdown: Record<string, number>;
}

const REFRESH_MS = 60_000;

function Eyebrow({ children }: { children: React.ReactNode }) {
  return (
    <p className="font-mono text-[10px] uppercase tracking-[0.28em] text-muted-foreground">
      <span aria-hidden className="mr-2 text-accent">
        ┼
      </span>
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

/** Engagement tone — accent (vermillion) is the alarm: dormant + never are
 *  what the operator needs to spot. idle is muted; active is normal. */
function engagementTone(engagement: Engagement): string {
  if (engagement === "never" || engagement === "dormant") return "text-accent";
  if (engagement === "idle") return "text-muted-foreground";
  return "text-foreground";
}

function kindTone(kind: TenantKind): string {
  if (kind === "live") return "text-foreground";
  if (kind === "pilot") return "text-foreground";
  return "text-muted-foreground/60";
}

function trendGlyph(trend: Trend): string {
  if (trend === "rising") return "▲";
  if (trend === "falling") return "▼";
  if (trend === "new") return "✦";
  return "—";
}

function trendTone(trend: Trend): string {
  if (trend === "falling") return "text-accent";
  if (trend === "rising" || trend === "new") return "text-foreground";
  return "text-muted-foreground";
}

function relativeTime(iso: string | null): string {
  if (!iso) return "never";
  const then = new Date(iso).getTime();
  if (Number.isNaN(then)) return "—";
  const seconds = Math.max(0, Math.floor((Date.now() - then) / 1000));
  if (seconds < 90) return "just now";
  const minutes = Math.floor(seconds / 60);
  if (minutes < 90) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 36) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  return `${days}d ago`;
}

function Stat({ label, value, sub }: { label: string; value: string; sub?: string }) {
  return (
    <div className="border border-border px-5 py-4">
      <p className="font-mono text-[10px] uppercase tracking-[0.22em] text-muted-foreground">
        {label}
      </p>
      <p className="mt-2 font-mono text-2xl tabular-nums text-foreground">{value}</p>
      {sub ? (
        <p className="mt-1 font-mono text-[10px] uppercase tracking-[0.18em] text-muted-foreground">
          {sub}
        </p>
      ) : null}
    </div>
  );
}

function Chip({ children, tone }: { children: React.ReactNode; tone: string }) {
  return (
    <span className={`font-mono text-[10px] uppercase tracking-[0.2em] ${tone}`}>
      {children}
    </span>
  );
}

function TenantRow({
  p,
  expanded,
  detail,
  detailError,
  onToggle,
}: {
  p: PilotCard;
  expanded: boolean;
  detail: PilotDetail | undefined;
  detailError: string | undefined;
  onToggle: (orgId: string) => void;
}) {
  return (
    <li>
      <button
        type="button"
        onClick={() => onToggle(p.org_id)}
        className="w-full px-6 py-5 text-left transition hover:bg-foreground/[0.03]"
      >
        <div className="flex flex-wrap items-baseline gap-x-4 gap-y-2">
          <span className="text-sm text-foreground">{p.org_name}</span>
          <Chip tone="text-muted-foreground">{p.org_type}</Chip>
          <Chip tone="text-muted-foreground">{p.plan_id}</Chip>
          <Chip tone={kindTone(p.tenant_kind)}>{p.tenant_kind}</Chip>
          <Chip tone={engagementTone(p.engagement)}>● {p.engagement}</Chip>
          <span className="ml-auto font-mono text-[10px] uppercase tracking-[0.18em] text-muted-foreground">
            activity {relativeTime(p.last_activity_at)}
          </span>
        </div>
        <div className="mt-3 flex flex-wrap gap-x-6 gap-y-1 font-mono text-[11px] tabular-nums text-muted-foreground">
          <span>
            seats <span className="text-foreground">{p.seats_logged_in}/{p.seats}</span> live
          </span>
          <span>
            actions 7d <span className="text-foreground">{p.actions_7d}</span>{" "}
            <span className={trendTone(p.trend)}>{trendGlyph(p.trend)}</span>
          </span>
          <span>
            users active <span className="text-foreground">{p.active_users_7d}</span>
          </span>
          <span>
            STR <span className="text-foreground">{p.strs}</span>
          </span>
          <span>
            alerts <span className="text-foreground">{p.alerts}</span>
          </span>
          <span>
            cases <span className="text-foreground">{p.cases}</span>
          </span>
          <span>
            scans <span className="text-foreground">{p.scans}</span>
          </span>
        </div>
      </button>
      {expanded ? <PilotDetailPanel detail={detail} error={detailError} /> : null}
    </li>
  );
}

export function PilotHealthBoard() {
  const [data, setData] = useState<Overview | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [expanded, setExpanded] = useState<string | null>(null);
  const [detail, setDetail] = useState<Record<string, PilotDetail>>({});
  const [detailError, setDetailError] = useState<Record<string, string>>({});

  const refresh = useCallback(async () => {
    setError(null);
    try {
      const r = await fetch(`/api/platform/pilots`, { cache: "no-store" });
      const json = await r.json();
      if (!r.ok) throw new Error(json.detail ?? "pilot health");
      setData(json as Overview);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to load pilot health.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refresh();
    const timer = setInterval(refresh, REFRESH_MS);
    return () => clearInterval(timer);
  }, [refresh]);

  const toggle = async (orgId: string) => {
    if (expanded === orgId) {
      setExpanded(null);
      return;
    }
    setExpanded(orgId);
    if (detail[orgId]) return;
    try {
      const r = await fetch(`/api/platform/pilots/${encodeURIComponent(orgId)}`, {
        cache: "no-store",
      });
      const json = await r.json();
      if (!r.ok) throw new Error(json.detail ?? "tenant detail");
      setDetail((prev) => ({ ...prev, [orgId]: json as PilotDetail }));
    } catch (err) {
      setDetailError((prev) => ({
        ...prev,
        [orgId]: err instanceof Error ? err.message : "Unable to load detail.",
      }));
    }
  };

  if (loading && !data) {
    return <LoadingState label="Loading pilot health" />;
  }
  if (!data) {
    return <ErrorState title="Unable to load pilot health" description={error ?? "—"} />;
  }

  const { summary, pilots } = data;
  const realTenants = pilots.filter((p) => p.tenant_kind !== "demo");
  const demoTenants = pilots.filter((p) => p.tenant_kind === "demo");
  const stalling = realTenants.filter(
    (p) => p.engagement === "dormant" || p.engagement === "never",
  );

  const renderRow = (p: PilotCard) => (
    <TenantRow
      key={p.org_id}
      p={p}
      expanded={expanded === p.org_id}
      detail={detail[p.org_id]}
      detailError={detailError[p.org_id]}
      onToggle={toggle}
    />
  );

  return (
    <div className="space-y-8">
      {error ? (
        <p className="font-mono text-xs uppercase tracking-[0.18em] text-destructive">
          ┼ ERROR · {error}
        </p>
      ) : null}

      <div className="grid grid-cols-2 gap-px md:grid-cols-3 lg:grid-cols-6">
        <Stat
          label="Pilots & live"
          value={String(realTenants.length)}
          sub={`${demoTenants.length} demo`}
        />
        <Stat
          label="Active · 7d"
          value={String(summary.tenants_active_7d)}
          sub="did real work"
        />
        <Stat
          label="Seats live"
          value={`${summary.seats_logged_in}/${summary.seats_total}`}
          sub="signed in ever"
        />
        <Stat label="Actions · 7d" value={String(summary.actions_7d)} sub="across all tenants" />
        <Stat label="STRs" value={String(summary.strs_total)} sub="incl. seed data" />
        <Stat label="Alerts" value={String(summary.alerts_total)} sub="incl. seed data" />
      </div>

      {stalling.length > 0 ? (
        <div className="border border-accent/50 px-6 py-4">
          <p className="font-mono text-[11px] uppercase tracking-[0.2em] text-accent">
            ┼ {stalling.length} pilot{stalling.length === 1 ? "" : "s"} stalling ·{" "}
            {stalling.map((p) => p.org_name).join(" · ")}
          </p>
        </div>
      ) : null}

      <Section eyebrow={`Pilots & live · ${realTenants.length}`}>
        {realTenants.length === 0 ? (
          <p className="px-6 py-6 font-mono text-xs uppercase tracking-[0.22em] text-muted-foreground">
            No pilot or live tenants. Classify a tenant under Tenants.
          </p>
        ) : (
          <ul className="divide-y divide-border">{realTenants.map(renderRow)}</ul>
        )}
      </Section>

      {demoTenants.length > 0 ? (
        <Section eyebrow={`Demo / sandbox · ${demoTenants.length}`}>
          <ul className="divide-y divide-border opacity-70">
            {demoTenants.map(renderRow)}
          </ul>
        </Section>
      ) : null}
    </div>
  );
}

function PilotDetailPanel({
  detail,
  error,
}: {
  detail: PilotDetail | undefined;
  error: string | undefined;
}) {
  if (error) {
    return (
      <div className="border-t border-border bg-foreground/[0.02] px-6 py-4">
        <p className="font-mono text-xs uppercase tracking-[0.18em] text-destructive">
          ┼ ERROR · {error}
        </p>
      </div>
    );
  }
  if (!detail) {
    return (
      <div className="border-t border-border bg-foreground/[0.02] px-6 py-4">
        <p className="font-mono text-[11px] uppercase tracking-[0.2em] text-muted-foreground">
          Loading detail…
        </p>
      </div>
    );
  }

  const breakdown = Object.entries(detail.action_breakdown).sort((a, b) => b[1] - a[1]);

  return (
    <div className="space-y-6 border-t border-border bg-foreground/[0.02] px-6 py-5">
      <div>
        <Eyebrow>Seats · {detail.users.length}</Eyebrow>
        {detail.users.length === 0 ? (
          <p className="mt-3 font-mono text-[11px] uppercase tracking-[0.2em] text-muted-foreground">
            No seats provisioned.
          </p>
        ) : (
          <ul className="mt-3 divide-y divide-border border border-border">
            {detail.users.map((u) => (
              <li
                key={u.user_id}
                className="flex flex-wrap items-baseline gap-x-4 gap-y-1 px-4 py-3"
              >
                <span className="text-sm text-foreground">{u.full_name ?? "—"}</span>
                <Chip tone="text-muted-foreground">{u.role ?? "—"}</Chip>
                <Chip tone={engagementTone(u.engagement)}>● {u.engagement}</Chip>
                <span className="ml-auto font-mono text-[10px] uppercase tracking-[0.18em] text-muted-foreground">
                  login {relativeTime(u.last_login_at)} · activity{" "}
                  {relativeTime(u.last_activity_at)} · {u.actions_7d} act/7d
                </span>
              </li>
            ))}
          </ul>
        )}
      </div>

      {breakdown.length > 0 ? (
        <div>
          <Eyebrow>Action breakdown · 30d</Eyebrow>
          <div className="mt-3 flex flex-wrap gap-2">
            {breakdown.map(([resource, count]) => (
              <span
                key={resource}
                className="border border-border px-3 py-1 font-mono text-[10px] uppercase tracking-[0.18em] text-muted-foreground"
              >
                {resource} <span className="text-foreground tabular-nums">{count}</span>
              </span>
            ))}
          </div>
        </div>
      ) : null}

      <div>
        <Eyebrow>Recent actions · {detail.recent_actions.length}</Eyebrow>
        {detail.recent_actions.length === 0 ? (
          <p className="mt-3 font-mono text-[11px] uppercase tracking-[0.2em] text-muted-foreground">
            No recorded actions.
          </p>
        ) : (
          <ul className="mt-3 divide-y divide-border border border-border">
            {detail.recent_actions.map((a, idx) => (
              <li
                key={`${a.action}-${idx}`}
                className="flex flex-wrap items-baseline gap-x-4 px-4 py-2 font-mono text-[11px]"
              >
                <span className="text-foreground">{a.action}</span>
                {a.resource_type ? (
                  <span className="text-muted-foreground">{a.resource_type}</span>
                ) : null}
                <span className="ml-auto uppercase tracking-[0.18em] text-muted-foreground">
                  {relativeTime(a.created_at)}
                </span>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
