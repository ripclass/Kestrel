"use client";

import { useCallback, useEffect, useState } from "react";

import { ErrorState } from "@/components/common/error-state";
import { LoadingState } from "@/components/common/loading";
import { provisionTenant } from "@/app/actions/provision-tenant";

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
const ORG_TYPES = ["bank", "mfs", "nbfi", "regulator"];
const PLAN_IDS = ["starter", "professional", "enterprise", "filing_only"];

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

const fieldClass =
  "border border-border bg-background px-3 py-2 font-mono text-sm text-foreground";
const labelClass =
  "font-mono text-[10px] uppercase tracking-[0.22em] text-muted-foreground";

function ProvisionForm({ onProvisioned }: { onProvisioned: () => void }) {
  const [open, setOpen] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [form, setForm] = useState({
    orgName: "",
    orgType: "bank",
    planId: "professional",
    tenantKind: "pilot" as TenantKind,
    adminName: "",
    adminEmail: "",
    adminDesignation: "",
    seedDemoData: true,
  });

  function update<K extends keyof typeof form>(key: K, value: (typeof form)[K]) {
    setForm((current) => ({ ...current, [key]: value }));
    setNotice(null);
  }

  async function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSubmitting(true);
    setError(null);
    setNotice(null);
    try {
      const result = await provisionTenant(form);
      if (!result.success) {
        setError(result.message ?? "Provisioning failed.");
        return;
      }
      setNotice(`Tenant provisioned — admin invite sent to ${form.adminEmail.trim()}.`);
      setForm({
        orgName: "",
        orgType: "bank",
        planId: "professional",
        tenantKind: "pilot",
        adminName: "",
        adminEmail: "",
        adminDesignation: "",
        seedDemoData: true,
      });
      onProvisioned();
    } catch {
      setError("Provisioning failed — unexpected error.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <section className="border border-border">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="flex w-full items-center justify-between px-6 py-5 text-left"
      >
        <Eyebrow>Provision tenant</Eyebrow>
        <span className="font-mono text-[11px] uppercase tracking-[0.22em] text-accent">
          {open ? "− close" : "+ new tenant"}
        </span>
      </button>

      {open ? (
        <form className="space-y-5 border-t border-border px-6 py-6" onSubmit={submit}>
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
            <label className="flex flex-col gap-2">
              <span className={labelClass}>Organization name *</span>
              <input
                type="text"
                value={form.orgName}
                onChange={(e) => update("orgName", e.target.value)}
                placeholder="Agrani Bank PLC"
                required
                className={fieldClass}
              />
            </label>
            <label className="flex flex-col gap-2">
              <span className={labelClass}>Organization type</span>
              <select
                value={form.orgType}
                onChange={(e) => update("orgType", e.target.value)}
                className={fieldClass}
              >
                {ORG_TYPES.map((t) => (
                  <option key={t} value={t}>{t}</option>
                ))}
              </select>
            </label>
            <label className="flex flex-col gap-2">
              <span className={labelClass}>Plan</span>
              <select
                value={form.planId}
                onChange={(e) => update("planId", e.target.value)}
                className={fieldClass}
              >
                {PLAN_IDS.map((p) => (
                  <option key={p} value={p}>{p}</option>
                ))}
              </select>
            </label>
            <div className="flex flex-col gap-2">
              <span className={labelClass}>Classification</span>
              <div className="flex border border-border">
                {KINDS.map((kind) => (
                  <button
                    key={kind}
                    type="button"
                    onClick={() => update("tenantKind", kind)}
                    className={`flex-1 px-3 py-2 font-mono text-[10px] uppercase tracking-[0.22em] transition ${
                      form.tenantKind === kind
                        ? "bg-foreground text-background"
                        : "text-muted-foreground hover:text-foreground"
                    }`}
                  >
                    {kind}
                  </button>
                ))}
              </div>
            </div>
            <label className="flex flex-col gap-2">
              <span className={labelClass}>First admin — full name *</span>
              <input
                type="text"
                value={form.adminName}
                onChange={(e) => update("adminName", e.target.value)}
                placeholder="Mahbubur Rahman"
                required
                className={fieldClass}
              />
            </label>
            <label className="flex flex-col gap-2">
              <span className={labelClass}>First admin — email *</span>
              <input
                type="email"
                value={form.adminEmail}
                onChange={(e) => update("adminEmail", e.target.value)}
                placeholder="camlco@agranibank.org"
                required
                className={fieldClass}
              />
            </label>
            <label className="flex flex-col gap-2 md:col-span-2">
              <span className={labelClass}>First admin — designation</span>
              <input
                type="text"
                value={form.adminDesignation}
                onChange={(e) => update("adminDesignation", e.target.value)}
                placeholder="Chief AML Compliance Officer"
                className={fieldClass}
              />
            </label>
          </div>

          <label className="flex items-center gap-3">
            <input
              type="checkbox"
              checked={form.seedDemoData}
              onChange={(e) => update("seedDemoData", e.target.checked)}
              className="h-4 w-4 accent-[var(--accent)]"
            />
            <span className="font-mono text-[11px] uppercase tracking-[0.18em] text-muted-foreground">
              Seed demo data — populates the workspace within ~10 min so the admin lands on a live-looking demo
            </span>
          </label>

          {error ? (
            <p className="font-mono text-xs uppercase tracking-[0.18em] text-destructive">
              ┼ ERROR · {error}
            </p>
          ) : null}
          {notice ? (
            <p className="font-mono text-xs uppercase tracking-[0.18em] text-accent">
              ┼ {notice}
            </p>
          ) : null}

          <div className="flex justify-end">
            <button
              type="submit"
              disabled={submitting}
              className="border border-foreground bg-foreground px-5 py-2 font-mono text-[11px] uppercase tracking-[0.22em] text-background transition hover:bg-background hover:text-foreground disabled:opacity-50"
            >
              {submitting ? "Provisioning…" : "Provision tenant"}
            </button>
          </div>
        </form>
      ) : null}
    </section>
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

      <ProvisionForm onProvisioned={refresh} />

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
        ┼ Provisioning creates the organization and emails the first admin a
        magic-link invite. Add further seats via the bootstrap script.
      </p>
    </div>
  );
}
