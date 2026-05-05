"use client";

import { useEffect, useState } from "react";

import { ErrorState } from "@/components/common/error-state";
import { LoadingState } from "@/components/common/loading";

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

const SEVERITY_OPTIONS: Array<{ label: string; value: "minor" | "major" | "outage" }> = [
  { label: "MINOR", value: "minor" },
  { label: "MAJOR", value: "major" },
  { label: "OUTAGE", value: "outage" },
];

const COMPONENT_OPTIONS = [
  "overall",
  "auth",
  "database",
  "redis",
  "storage",
  "worker",
  "ai",
  "web",
  "engine",
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

function severityTone(severity: string): string {
  if (severity === "outage") return "text-destructive";
  if (severity === "major") return "text-accent";
  return "text-muted-foreground";
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

export function AdminStatusPanel() {
  const [component, setComponent] = useState("overall");
  const [severity, setSeverity] = useState<"minor" | "major" | "outage">("minor");
  const [summary, setSummary] = useState("");
  const [message, setMessage] = useState("");
  const [resolveMessage, setResolveMessage] = useState<Record<string, string>>({});
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [incidents, setIncidents] = useState<StatusIncident[] | null>(null);
  const [loading, setLoading] = useState(true);

  const refresh = async () => {
    setError(null);
    try {
      const r = await fetch(`/api/admin/status/incidents?limit=50`, { cache: "no-store" });
      const json = await r.json();
      if (!r.ok) throw new Error(json.detail ?? "incidents");
      setIncidents((json.rows ?? []) as StatusIncident[]);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to load incidents.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    refresh();
  }, []);

  const submit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!summary.trim()) {
      setError("Summary is required.");
      return;
    }
    setSubmitting(true);
    setError(null);
    try {
      const r = await fetch(`/api/admin/status/incidents`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          component,
          severity,
          summary: summary.trim(),
          message: message.trim() || undefined,
        }),
      });
      const json = await r.json();
      if (!r.ok) throw new Error(json.detail ?? "post incident");
      setSummary("");
      setMessage("");
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to post incident.");
    } finally {
      setSubmitting(false);
    }
  };

  const resolve = async (id: string) => {
    setSubmitting(true);
    setError(null);
    try {
      const r = await fetch(`/api/admin/status/incidents/${encodeURIComponent(id)}/resolve`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: resolveMessage[id]?.trim() || undefined }),
      });
      const json = await r.json();
      if (!r.ok) throw new Error(json.detail ?? "resolve");
      setResolveMessage({ ...resolveMessage, [id]: "" });
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to resolve incident.");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="space-y-8">
      <Section eyebrow="Post incident">
        <form className="space-y-5 px-6 py-6" onSubmit={submit}>
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
            <label className="flex flex-col gap-2">
              <span className="font-mono text-[10px] uppercase tracking-[0.22em] text-muted-foreground">
                Component
              </span>
              <select
                value={component}
                onChange={(e) => setComponent(e.target.value)}
                className="border border-border bg-background px-3 py-2 font-mono text-sm text-foreground"
              >
                {COMPONENT_OPTIONS.map((c) => (
                  <option key={c} value={c}>{c}</option>
                ))}
              </select>
            </label>
            <div className="flex flex-col gap-2">
              <span className="font-mono text-[10px] uppercase tracking-[0.22em] text-muted-foreground">
                Severity
              </span>
              <div className="flex border border-border">
                {SEVERITY_OPTIONS.map((opt) => (
                  <button
                    key={opt.value}
                    type="button"
                    onClick={() => setSeverity(opt.value)}
                    className={`px-4 py-2 font-mono text-[11px] uppercase tracking-[0.22em] transition ${
                      severity === opt.value ? "bg-foreground text-background" : "text-muted-foreground hover:text-foreground"
                    }`}
                  >
                    {opt.label}
                  </button>
                ))}
              </div>
            </div>
          </div>
          <label className="flex flex-col gap-2">
            <span className="font-mono text-[10px] uppercase tracking-[0.22em] text-muted-foreground">
              Summary *
            </span>
            <input
              type="text"
              value={summary}
              onChange={(e) => setSummary(e.target.value)}
              placeholder="Engine deploy in progress; brief 30-second hold."
              required
              className="border border-border bg-background px-3 py-2 font-mono text-sm text-foreground"
            />
          </label>
          <label className="flex flex-col gap-2">
            <span className="font-mono text-[10px] uppercase tracking-[0.22em] text-muted-foreground">
              Detail (optional)
            </span>
            <textarea
              value={message}
              onChange={(e) => setMessage(e.target.value)}
              rows={4}
              className="border border-border bg-background px-3 py-2 font-mono text-sm text-foreground"
            />
          </label>
          {error ? (
            <p className="font-mono text-xs uppercase tracking-[0.18em] text-destructive">
              ┼ ERROR · {error}
            </p>
          ) : null}
          <div className="flex justify-end">
            <button
              type="submit"
              disabled={submitting}
              className="border border-foreground bg-foreground px-5 py-2 font-mono text-[11px] uppercase tracking-[0.22em] text-background transition hover:bg-background hover:text-foreground disabled:opacity-50"
            >
              {submitting ? "Posting…" : "Post incident"}
            </button>
          </div>
        </form>
      </Section>

      {loading && !incidents ? (
        <LoadingState label="Loading incidents" />
      ) : !incidents ? (
        <ErrorState title="Unable to load incidents" description={error ?? "—"} />
      ) : (
        <Section eyebrow={`Incidents · ${incidents.length}`}>
          {incidents.length === 0 ? (
            <p className="px-6 py-6 font-mono text-xs uppercase tracking-[0.22em] text-muted-foreground">
              No incidents posted.
            </p>
          ) : (
            <ul className="divide-y divide-border">
              {incidents.map((inc) => (
                <li key={inc.id} className="space-y-3 px-6 py-5">
                  <div className="flex flex-wrap items-center gap-3">
                    <span className={`font-mono text-[11px] uppercase tracking-[0.22em] ${severityTone(inc.severity)}`}>
                      {inc.severity}
                    </span>
                    <span className="font-mono text-[11px] uppercase tracking-[0.22em] text-muted-foreground">
                      {inc.component}
                    </span>
                    <span
                      className={`font-mono text-[10px] uppercase tracking-[0.22em] ${
                        inc.is_active ? "text-accent" : "text-muted-foreground"
                      }`}
                    >
                      {inc.is_active ? "active" : "resolved"}
                    </span>
                    <span className="ml-auto font-mono text-[10px] uppercase tracking-[0.22em] text-muted-foreground">
                      {fmtDate(inc.started_at)}
                    </span>
                  </div>
                  <p className="text-sm text-foreground">{inc.summary}</p>
                  {inc.message ? (
                    <p className="whitespace-pre-line font-mono text-xs text-muted-foreground">{inc.message}</p>
                  ) : null}
                  {inc.is_active ? (
                    <div className="flex flex-wrap items-end gap-3 border-t border-border pt-3">
                      <input
                        type="text"
                        value={resolveMessage[inc.id] ?? ""}
                        onChange={(e) =>
                          setResolveMessage({ ...resolveMessage, [inc.id]: e.target.value })
                        }
                        placeholder="Resolution note (optional)"
                        className="flex-1 border border-border bg-background px-3 py-1.5 font-mono text-xs text-foreground"
                      />
                      <button
                        type="button"
                        onClick={() => resolve(inc.id)}
                        disabled={submitting}
                        className="border border-foreground px-3 py-1.5 font-mono text-[11px] uppercase tracking-[0.22em] text-foreground transition hover:bg-foreground hover:text-background disabled:opacity-50"
                      >
                        Resolve
                      </button>
                    </div>
                  ) : null}
                </li>
              ))}
            </ul>
          )}
        </Section>
      )}
    </div>
  );
}
