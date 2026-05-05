"use client";

import Link from "next/link";
import { useState } from "react";

interface EvidenceItem {
  hop: number;
  tool: string;
  args: Record<string, unknown>;
  result: Record<string, unknown>;
  error: string | null;
}

interface InvestigationResult {
  id: string;
  entity_id: string | null;
  prompt: string;
  status: string;
  hypothesis: string | null;
  evidence: EvidenceItem[];
  suggested_actions: string[];
  confidence: number | null;
  hops_used: number;
  latency_ms: number;
  error: string | null;
}

const SUGGESTED_ACTION_LABEL: Record<string, string> = {
  draft_str: "Draft STR",
  open_case: "Open case",
  request_str_supplement: "Request STR supplement",
  monitor: "Monitor",
};

function statusTone(status: string): string {
  if (status === "completed") return "text-foreground";
  if (status === "exhausted") return "text-accent";
  if (status === "failed" || status === "cancelled") return "text-destructive";
  return "text-muted-foreground";
}

function fmtMs(ms: number): string {
  if (!Number.isFinite(ms)) return "—";
  if (ms >= 1000) return `${(ms / 1000).toFixed(1)} s`;
  return `${Math.round(ms)} ms`;
}

function summariseResult(result: Record<string, unknown>): string {
  if (!result || typeof result !== "object") return "—";
  if ("matches" in result && Array.isArray(result.matches)) {
    return `${result.matches.length} watchlist match${result.matches.length === 1 ? "" : "es"}`;
  }
  if ("neighbours" in result && Array.isArray(result.neighbours)) {
    return `${result.neighbours.length} connected entit${result.neighbours.length === 1 ? "y" : "ies"}`;
  }
  if ("alerts" in result && Array.isArray(result.alerts)) {
    return `${result.alerts.length} recent alert${result.alerts.length === 1 ? "" : "s"}`;
  }
  if ("strs" in result && Array.isArray(result.strs)) {
    return `${result.strs.length} prior STR${result.strs.length === 1 ? "" : "s"}`;
  }
  if ("display_name" in result || "display_value" in result) {
    return String(result.display_name ?? result.display_value ?? "—");
  }
  if ("narrative_seed" in result && typeof result.narrative_seed === "string") {
    return result.narrative_seed.length > 80 ? result.narrative_seed.slice(0, 80) + "…" : result.narrative_seed;
  }
  return "—";
}

export function InvestigationPanel({ entityId, entityName }: { entityId: string; entityName: string }) {
  const [prompt, setPrompt] = useState(
    `Investigate this subject (${entityName}) and surface any cross-bank exposure, sanctions hits, or recent alerts.`,
  );
  const [running, setRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<InvestigationResult | null>(null);

  const run = async () => {
    if (!prompt.trim()) {
      setError("Prompt is required.");
      return;
    }
    setRunning(true);
    setError(null);
    setResult(null);
    try {
      const response = await fetch(`/api/agents/investigate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ entity_id: entityId, prompt: prompt.trim() }),
      });
      const json = await response.json();
      if (!response.ok) throw new Error(json.detail ?? "investigation failed");
      setResult(json as InvestigationResult);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to run investigation.");
    } finally {
      setRunning(false);
    }
  };

  const promoteToStr = () => {
    if (!result) return;
    if (typeof window !== "undefined") {
      try {
        sessionStorage.setItem(
          `kestrel:investigation:${entityId}`,
          JSON.stringify({
            entity_id: result.entity_id,
            entity_name: entityName,
            hypothesis: result.hypothesis,
            evidence: result.evidence,
            suggested_actions: result.suggested_actions,
            confidence: result.confidence,
          }),
        );
      } catch {
        // sessionStorage unavailable (private mode etc.); proceed without prefill.
      }
    }
    // Navigate via location so the STR form picks up the prefill.
    if (typeof window !== "undefined") {
      window.location.href = `/strs/new?investigation=${encodeURIComponent(result.id)}&entity=${encodeURIComponent(entityId)}`;
    }
  };

  const canPromote = result && result.status === "completed";

  return (
    <section className="border border-border">
      <div className="border-b border-border px-6 py-5">
        <p className="font-mono text-[10px] uppercase tracking-[0.28em] text-muted-foreground">
          <span aria-hidden className="mr-2 text-accent">┼</span>
          Investigate this entity (AI)
        </p>
      </div>
      <div className="space-y-5 px-6 py-6">
        <label className="flex flex-col gap-2">
          <span className="font-mono text-[10px] uppercase tracking-[0.22em] text-muted-foreground">
            Prompt
          </span>
          <textarea
            value={prompt}
            onChange={(event) => setPrompt(event.target.value)}
            rows={3}
            className="border border-border bg-background px-3 py-2 font-mono text-xs text-foreground"
          />
        </label>
        <div className="flex flex-wrap items-center gap-3">
          <button
            type="button"
            onClick={run}
            disabled={running}
            className="border border-foreground bg-foreground px-5 py-2 font-mono text-[11px] uppercase tracking-[0.22em] text-background transition hover:bg-background hover:text-foreground disabled:opacity-50"
          >
            {running ? "Running agent…" : "Run investigation"}
          </button>
          <span className="font-mono text-[10px] uppercase tracking-[0.22em] text-muted-foreground">
            Bounded · max 8 hops · 60s wall-clock
          </span>
        </div>
        {error ? (
          <p className="font-mono text-xs uppercase tracking-[0.18em] text-destructive">
            ┼ ERROR · {error}
          </p>
        ) : null}

        {result ? (
          <div className="space-y-5 border-t border-border pt-5">
            <div className="grid grid-cols-1 gap-px border border-border bg-border md:grid-cols-4">
              <Tile label="Status" value={result.status.toUpperCase()} tone={statusTone(result.status)} />
              <Tile
                label="Confidence"
                value={result.confidence !== null ? result.confidence.toFixed(2) : "—"}
                tone="text-foreground"
              />
              <Tile label="Hops used" value={String(result.hops_used)} tone="text-foreground" />
              <Tile label="Latency" value={fmtMs(result.latency_ms)} tone="text-muted-foreground" />
            </div>

            {result.hypothesis ? (
              <div className="space-y-2">
                <p className="font-mono text-[10px] uppercase tracking-[0.22em] text-muted-foreground">
                  Hypothesis
                </p>
                <p className="text-sm text-foreground">{result.hypothesis}</p>
              </div>
            ) : null}

            {result.suggested_actions.length > 0 ? (
              <div className="space-y-2">
                <p className="font-mono text-[10px] uppercase tracking-[0.22em] text-muted-foreground">
                  Suggested actions
                </p>
                <ul className="flex flex-wrap gap-2">
                  {result.suggested_actions.map((action) => (
                    <li
                      key={action}
                      className="border border-border px-3 py-1.5 font-mono text-[11px] uppercase tracking-[0.22em] text-foreground"
                    >
                      {SUGGESTED_ACTION_LABEL[action] ?? action}
                    </li>
                  ))}
                </ul>
              </div>
            ) : null}

            {result.evidence.length > 0 ? (
              <div className="space-y-2">
                <p className="font-mono text-[10px] uppercase tracking-[0.22em] text-muted-foreground">
                  Evidence trail · {result.evidence.length} hops
                </p>
                <ul className="divide-y divide-border border border-border">
                  {result.evidence.map((item) => (
                    <li
                      key={`${item.hop}-${item.tool}`}
                      className="grid grid-cols-12 items-center gap-3 px-4 py-2.5"
                    >
                      <div className="col-span-1 font-mono text-[10px] uppercase tracking-[0.22em] text-muted-foreground">
                        #{item.hop}
                      </div>
                      <div className="col-span-3 font-mono text-[11px] uppercase tracking-[0.22em] text-foreground">
                        {item.tool}
                      </div>
                      <div className="col-span-7 font-mono text-[11px] text-muted-foreground truncate">
                        {item.error ? (
                          <span className="text-destructive">{item.error}</span>
                        ) : (
                          summariseResult(item.result)
                        )}
                      </div>
                      <div className="col-span-1 text-right font-mono text-[10px] uppercase tracking-[0.18em] text-muted-foreground">
                        {item.error ? "err" : "ok"}
                      </div>
                    </li>
                  ))}
                </ul>
              </div>
            ) : null}

            <div className="flex flex-wrap items-center justify-end gap-3 border-t border-border pt-4">
              {canPromote ? (
                <button
                  type="button"
                  onClick={promoteToStr}
                  className="border border-foreground bg-foreground px-4 py-2 font-mono text-[11px] uppercase tracking-[0.22em] text-background transition hover:bg-background hover:text-foreground"
                >
                  Promote to STR draft
                </button>
              ) : null}
              <Link
                href="/strs"
                className="border border-border px-4 py-2 font-mono text-[11px] uppercase tracking-[0.22em] text-foreground transition hover:bg-foreground hover:text-background"
              >
                Open STR queue
              </Link>
            </div>
          </div>
        ) : null}
      </div>
    </section>
  );
}

function Tile({ label, value, tone }: { label: string; value: string; tone: string }) {
  return (
    <div className="flex flex-col gap-1 border border-border p-4">
      <p className="font-mono text-[10px] uppercase tracking-[0.28em] text-muted-foreground">{label}</p>
      <p className={`font-mono text-2xl tabular-nums ${tone}`}>{value}</p>
    </div>
  );
}
