"use client";

import { useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { detailFromPayload, readResponsePayload } from "@/lib/http";
import type { MatchDefinitionDetail, MatchDefinitionSummary } from "@/types/domain";

const EXAMPLE_DEFINITION = `{
  "conditions": {
    "trigger": "amount_gt",
    "params": { "amount_bdt": 5000000 }
  },
  "scoring": { "base": 60 },
  "severity_thresholds": { "high": 70, "critical": 90 }
}`;

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label className="flex flex-col gap-2">
      <span className="font-mono text-[10px] uppercase tracking-[0.28em] text-muted-foreground">
        {label}
      </span>
      {children}
    </label>
  );
}

export function MatchDefinitionsAdmin() {
  const [records, setRecords] = useState<MatchDefinitionSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [definition, setDefinition] = useState(EXAMPLE_DEFINITION);
  const [creating, setCreating] = useState(false);

  const [selected, setSelected] = useState<MatchDefinitionDetail | null>(null);
  const [pending, setPending] = useState<string | null>(null);

  async function loadList() {
    setLoading(true);
    try {
      const response = await fetch("/api/match-definitions", { cache: "no-store" });
      const payload = (await readResponsePayload<{ matchDefinitions: MatchDefinitionSummary[] }>(response)) as
        | { matchDefinitions: MatchDefinitionSummary[] }
        | { detail?: string };
      if (!response.ok) {
        setError(detailFromPayload(payload, "Unable to load match definitions."));
        return;
      }
      setRecords(
        (payload as { matchDefinitions: MatchDefinitionSummary[] }).matchDefinitions,
      );
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to load match definitions.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void loadList();
  }, []);

  async function create() {
    setError(null);
    setNotice(null);
    setCreating(true);
    try {
      let parsed: Record<string, unknown>;
      try {
        parsed = JSON.parse(definition);
      } catch {
        setError("Definition must be valid JSON.");
        return;
      }
      const response = await fetch("/api/match-definitions", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name, description: description || null, definition: parsed, isActive: true }),
      });
      const payload = (await readResponsePayload<unknown>(response)) as { detail?: string };
      if (!response.ok) {
        setError(detailFromPayload(payload, "Unable to create match definition."));
        return;
      }
      setNotice("Match definition created.");
      setName("");
      setDescription("");
      setDefinition(EXAMPLE_DEFINITION);
      void loadList();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to create match definition.");
    } finally {
      setCreating(false);
    }
  }

  async function openDetail(id: string) {
    const response = await fetch(`/api/match-definitions/${id}`, { cache: "no-store" });
    if (response.ok) {
      const payload = (await readResponsePayload<MatchDefinitionDetail>(response)) as MatchDefinitionDetail;
      setSelected(payload);
    }
  }

  async function executeDefinition(id: string) {
    setPending(id);
    setError(null);
    try {
      const response = await fetch(`/api/match-definitions/${id}/execute`, { method: "POST" });
      const payload = (await readResponsePayload<{ matchDefinition: MatchDefinitionDetail }>(response)) as
        | { matchDefinition: MatchDefinitionDetail }
        | { detail?: string };
      if (!response.ok) {
        setError(detailFromPayload(payload, "Unable to execute match definition."));
        return;
      }
      setNotice(`Execution recorded for ${id}.`);
      setSelected((payload as { matchDefinition: MatchDefinitionDetail }).matchDefinition);
      void loadList();
    } finally {
      setPending(null);
    }
  }

  async function toggleActive(record: MatchDefinitionSummary) {
    setPending(record.id);
    try {
      const response = await fetch(`/api/match-definitions/${record.id}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ isActive: !record.isActive }),
      });
      if (response.ok) {
        void loadList();
        if (selected?.id === record.id) void openDetail(record.id);
      }
    } finally {
      setPending(null);
    }
  }

  async function remove(record: MatchDefinitionSummary) {
    const response = await fetch(`/api/match-definitions/${record.id}`, { method: "DELETE" });
    if (response.ok) {
      if (selected?.id === record.id) setSelected(null);
      void loadList();
    }
  }

  return (
    <div className="space-y-6">
      <section className="border border-border">
        <div className="border-b border-border px-6 py-5">
          <p className="font-mono text-[10px] uppercase tracking-[0.28em] text-muted-foreground">
            <span aria-hidden className="mr-2 text-accent">┼</span>
            Section · New match definition
          </p>
          <p className="mt-2 text-sm leading-relaxed text-muted-foreground">
            Define a JSON policy. v1 records executions but does not yet run the evaluator against live
            transactions — the 8 system rules still cover detection in production.
          </p>
        </div>
        <div className="space-y-5 p-6">
          <div className="grid gap-4 md:grid-cols-2">
            <Field label="Name">
              <Input
                value={name}
                onChange={(event) => setName(event.target.value)}
                placeholder="High-value border district transfers"
              />
            </Field>
            <Field label="Description">
              <Input value={description} onChange={(event) => setDescription(event.target.value)} />
            </Field>
          </div>
          <Field label="Definition (JSON)">
            <Textarea
              value={definition}
              onChange={(event) => setDefinition(event.target.value)}
              rows={10}
              className="font-mono text-xs"
            />
          </Field>
          {error ? (
            <p className="font-mono text-xs uppercase tracking-[0.18em] text-destructive">
              <span aria-hidden className="mr-2">┼</span>ERROR · {error}
            </p>
          ) : null}
          {notice ? (
            <p className="font-mono text-xs uppercase tracking-[0.18em] text-accent">
              <span aria-hidden className="mr-2">┼</span>
              {notice}
            </p>
          ) : null}
          <div className="flex justify-end border-t border-border pt-4">
            <Button type="button" disabled={creating || !name.trim()} onClick={() => void create()}>
              {creating ? "Creating…" : "Create match definition"}
            </Button>
          </div>
        </div>
      </section>

      <section className="border border-border">
        <div className="border-b border-border px-6 py-5">
          <p className="font-mono text-[10px] uppercase tracking-[0.28em] text-muted-foreground">
            <span aria-hidden className="mr-2 text-accent">┼</span>
            Section · Active definitions
          </p>
          <p className="mt-2 text-sm leading-relaxed text-muted-foreground">
            Run a definition to record an execution · toggle active to pause.
          </p>
        </div>
        <div className="space-y-3 p-6">
          {loading ? (
            <p className="font-mono text-[11px] uppercase tracking-[0.22em] text-muted-foreground">
              Loading…
            </p>
          ) : records.length === 0 ? (
            <p className="font-mono text-[11px] uppercase tracking-[0.22em] text-muted-foreground">
              No match definitions yet
            </p>
          ) : (
            records.map((record) => (
              <div key={record.id} className="border border-border bg-card px-5 py-4">
                <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
                  <div className="space-y-2">
                    <div className="flex flex-wrap items-center gap-3">
                      <p className="font-semibold text-foreground">{record.name}</p>
                      <span
                        className={`border px-2.5 py-0.5 font-mono text-[10px] uppercase tracking-[0.22em] ${
                          record.isActive
                            ? "border-accent/40 bg-accent/10 text-accent"
                            : "border-border text-muted-foreground"
                        }`}
                      >
                        {record.isActive ? "Active" : "Inactive"}
                      </span>
                    </div>
                    {record.description ? (
                      <p className="text-sm leading-relaxed text-muted-foreground">{record.description}</p>
                    ) : null}
                    <p className="font-mono text-[10px] uppercase tracking-[0.22em] text-muted-foreground">
                      <span className="tabular-nums text-foreground">{record.totalHits}</span> hit
                      {record.totalHits === 1 ? "" : "s"}
                      {record.lastExecutionAt
                        ? ` · last run ${new Date(record.lastExecutionAt).toLocaleString()}`
                        : ""}
                    </p>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    <Button
                      type="button"
                      variant="outline"
                      disabled={pending === record.id || !record.isActive}
                      onClick={() => void executeDefinition(record.id)}
                    >
                      {pending === record.id ? "Running…" : "Run now"}
                    </Button>
                    <Button type="button" variant="ghost" onClick={() => void openDetail(record.id)}>
                      Details
                    </Button>
                    <Button type="button" variant="ghost" onClick={() => void toggleActive(record)}>
                      {record.isActive ? "Pause" : "Activate"}
                    </Button>
                    <Button
                      type="button"
                      variant="ghost"
                      className="text-destructive hover:text-destructive"
                      onClick={() => void remove(record)}
                    >
                      Delete
                    </Button>
                  </div>
                </div>
              </div>
            ))
          )}
        </div>
      </section>

      {selected ? (
        <section className="border border-border">
          <div className="border-b border-border px-6 py-5">
            <p className="font-mono text-[10px] uppercase tracking-[0.28em] text-muted-foreground">
              <span aria-hidden className="mr-2 text-accent">┼</span>
              Section · {selected.name}
            </p>
            <p className="mt-2 text-sm leading-relaxed text-muted-foreground">
              Definition JSON + recent execution history.
            </p>
          </div>
          <div className="space-y-5 p-6">
            <pre className="overflow-x-auto border border-border bg-card p-4 font-mono text-xs text-foreground">
              {JSON.stringify(selected.definition, null, 2)}
            </pre>
            <div className="space-y-2">
              <p className="font-mono text-[10px] uppercase tracking-[0.28em] text-muted-foreground">
                Recent executions
              </p>
              {selected.recentExecutions.length === 0 ? (
                <p className="font-mono text-[11px] uppercase tracking-[0.22em] text-muted-foreground">
                  No executions recorded yet
                </p>
              ) : (
                <ul className="divide-y divide-border border border-border">
                  {selected.recentExecutions.map((execution) => (
                    <li key={execution.id} className="px-4 py-3">
                      <div className="flex flex-wrap items-center gap-3 font-mono text-[11px] uppercase tracking-[0.22em]">
                        <span className="text-foreground">
                          {new Date(execution.executedAt).toLocaleString()}
                        </span>
                        <span className="text-muted-foreground">
                          status · {execution.executionStatus}
                        </span>
                        <span className="text-muted-foreground">
                          hits · <span className="tabular-nums text-foreground">{execution.hitCount}</span>
                        </span>
                      </div>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </div>
        </section>
      ) : null}
    </div>
  );
}
