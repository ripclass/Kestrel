"use client";

import { useCallback, useEffect, useState } from "react";

import { ErrorState } from "@/components/common/error-state";
import { LoadingState } from "@/components/common/loading";

type Engagement = "active" | "idle" | "dormant" | "never";
type TenantKind = "demo" | "pilot" | "live";

interface Tenant {
  org_id: string;
  org_name: string;
  org_type: string;
  plan_id: string;
  tenant_kind: TenantKind;
  created_at: string | null;
  seats: number;
  seats_logged_in: number;
  last_activity_at: string | null;
  engagement: Engagement;
}

const KINDS: TenantKind[] = ["demo", "pilot", "live"];

function engagementTone(engagement: Engagement): string {
  if (engagement === "never" || engagement === "dormant") return "text-accent";
  if (engagement === "idle") return "text-muted-foreground";
  return "text-foreground";
}

function relativeTime(iso: string | null): string {
  if (!iso) return "never";
  const then = new Date(iso).getTime();
  if (Number.isNaN(then)) return "—";
  const days = Math.floor((Date.now() - then) / 86_400_000);
  if (days <= 0) return "today";
  return `${days}d ago`;
}

function Eyebrow({ children }: { children: React.ReactNode }) {
  return (
    <p className="font-mono text-[10px] uppercase tracking-[0.28em] text-muted-foreground">
      <span aria-hidden className="mr-2 text-accent">┼</span>
      {children}
    </p>
  );
}

export function TenantManagement() {
  const [tenants, setTenants] = useState<Tenant[] | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    setError(null);
    try {
      const r = await fetch(`/api/platform/tenants`, { cache: "no-store" });
      const json = await r.json();
      if (!r.ok) throw new Error(json.detail ?? "tenants");
      setTenants((json.tenants ?? []) as Tenant[]);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to load tenants.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const classify = async (orgId: string, kind: TenantKind) => {
    setSaving(orgId);
    setError(null);
    try {
      const r = await fetch(`/api/platform/tenants/${encodeURIComponent(orgId)}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ tenant_kind: kind }),
      });
      const json = await r.json();
      if (!r.ok) throw new Error(json.detail ?? "classify");
      setTenants((prev) =>
        prev
          ? prev.map((t) => (t.org_id === orgId ? { ...t, tenant_kind: kind } : t))
          : prev,
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to update tenant.");
    } finally {
      setSaving(null);
    }
  };

  if (loading && !tenants) {
    return <LoadingState label="Loading tenants" />;
  }
  if (!tenants) {
    return <ErrorState title="Unable to load tenants" description={error ?? "—"} />;
  }

  return (
    <div className="space-y-6">
      {error ? (
        <p className="font-mono text-xs uppercase tracking-[0.18em] text-destructive">
          ┼ ERROR · {error}
        </p>
      ) : null}

      <section className="border border-border">
        <div className="border-b border-border px-6 py-5">
          <Eyebrow>Tenants · {tenants.length}</Eyebrow>
        </div>
        <ul className="divide-y divide-border">
          {tenants.map((t) => (
            <li key={t.org_id} className="px-6 py-5">
              <div className="flex flex-wrap items-baseline gap-x-4 gap-y-2">
                <span className="text-sm text-foreground">{t.org_name}</span>
                <span className="font-mono text-[10px] uppercase tracking-[0.2em] text-muted-foreground">
                  {t.org_type}
                </span>
                <span className="font-mono text-[10px] uppercase tracking-[0.2em] text-muted-foreground">
                  {t.plan_id}
                </span>
                <span
                  className={`font-mono text-[10px] uppercase tracking-[0.2em] ${engagementTone(
                    t.engagement,
                  )}`}
                >
                  ● {t.engagement}
                </span>
                <span className="ml-auto font-mono text-[10px] uppercase tracking-[0.18em] text-muted-foreground">
                  seats {t.seats_logged_in}/{t.seats} · activity{" "}
                  {relativeTime(t.last_activity_at)}
                </span>
              </div>
              <div className="mt-3 flex items-center gap-3">
                <span className="font-mono text-[10px] uppercase tracking-[0.22em] text-muted-foreground">
                  Classification
                </span>
                <div className="flex border border-border">
                  {KINDS.map((kind) => (
                    <button
                      key={kind}
                      type="button"
                      disabled={saving === t.org_id || t.tenant_kind === kind}
                      onClick={() => classify(t.org_id, kind)}
                      className={`px-4 py-1.5 font-mono text-[10px] uppercase tracking-[0.22em] transition ${
                        t.tenant_kind === kind
                          ? "bg-foreground text-background"
                          : "text-muted-foreground hover:text-foreground disabled:opacity-40"
                      }`}
                    >
                      {kind}
                    </button>
                  ))}
                </div>
                {saving === t.org_id ? (
                  <span className="font-mono text-[10px] uppercase tracking-[0.2em] text-muted-foreground">
                    saving…
                  </span>
                ) : null}
              </div>
            </li>
          ))}
        </ul>
      </section>

      <p className="font-mono text-[10px] uppercase tracking-[0.18em] text-muted-foreground">
        ┼ Provisioning new tenants, plan changes and seat management are managed
        via the bootstrap script — console-native provisioning is a planned module.
      </p>
    </div>
  );
}
