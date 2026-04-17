"use client";

import { useEffect, useState } from "react";

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
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
      setRecords((payload as { matchDefinitions: MatchDefinitionSummary[] }).matchDefinitions);
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
      <Card>
        <CardHeader>
          <CardTitle>New match definition</CardTitle>
          <CardDescription>
            Define a JSON policy. v1 records executions but does not yet run the evaluator against live transactions
            — the 8 system rules still cover detection in production.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid gap-4 md:grid-cols-2">
            <div className="space-y-2">
              <label className="text-xs uppercase tracking-[0.18em] text-muted-foreground">Name</label>
              <Input value={name} onChange={(event) => setName(event.target.value)} placeholder="High-value border district transfers" />
            </div>
            <div className="space-y-2">
              <label className="text-xs uppercase tracking-[0.18em] text-muted-foreground">Description</label>
              <Input value={description} onChange={(event) => setDescription(event.target.value)} />
            </div>
          </div>
          <div className="space-y-2">
            <label className="text-xs uppercase tracking-[0.18em] text-muted-foreground">Definition (JSON)</label>
            <Textarea
              value={definition}
              onChange={(event) => setDefinition(event.target.value)}
              rows={10}
              className="font-mono text-xs"
            />
          </div>
          {error ? <p className="text-sm text-red-300">{error}</p> : null}
          {notice ? <p className="text-sm text-primary/80">{notice}</p> : null}
          <div className="flex justify-end">
            <Button type="button" disabled={creating || !name.trim()} onClick={() => void create()}>
              {creating ? "Creating…" : "Create match definition"}
            </Button>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Active definitions</CardTitle>
          <CardDescription>Run a definition to record an execution; toggle active to pause.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          {loading ? (
            <p className="text-sm text-muted-foreground">Loading…</p>
          ) : records.length === 0 ? (
            <p className="text-sm text-muted-foreground">No match definitions yet.</p>
          ) : (
            records.map((record) => (
              <div key={record.id} className="rounded-2xl border border-border/80 bg-background/50 p-4">
                <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
                  <div className="space-y-1">
                    <div className="flex flex-wrap items-center gap-3">
                      <p className="font-medium">{record.name}</p>
                      <span
                        className={`inline-flex items-center rounded-full border px-2 py-0.5 text-[10px] font-semibold uppercase tracking-widest ${
                          record.isActive
                            ? "border-primary/40 bg-primary/10 text-primary"
                            : "border-border text-muted-foreground"
                        }`}
                      >
                        {record.isActive ? "Active" : "Inactive"}
                      </span>
                    </div>
                    {record.description ? (
                      <p className="text-sm text-muted-foreground">{record.description}</p>
                    ) : null}
                    <p className="text-xs text-muted-foreground">
                      {record.totalHits} hit{record.totalHits === 1 ? "" : "s"}
                      {record.lastExecutionAt ? ` · last run ${new Date(record.lastExecutionAt).toLocaleString()}` : ""}
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
                      className="text-red-300 hover:text-red-200"
                      onClick={() => void remove(record)}
                    >
                      Delete
                    </Button>
                  </div>
                </div>
              </div>
            ))
          )}
        </CardContent>
      </Card>

      {selected ? (
        <Card>
          <CardHeader>
            <CardTitle>{selected.name}</CardTitle>
            <CardDescription>Definition JSON + recent execution history.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <pre className="overflow-x-auto rounded-xl border border-border/70 bg-background/60 p-4 text-xs font-mono">
              {JSON.stringify(selected.definition, null, 2)}
            </pre>
            <div className="space-y-2">
              <p className="text-xs uppercase tracking-[0.18em] text-muted-foreground">Recent executions</p>
              {selected.recentExecutions.length === 0 ? (
                <p className="text-sm text-muted-foreground">No executions recorded yet.</p>
              ) : (
                selected.recentExecutions.map((execution) => (
                  <div key={execution.id} className="rounded-xl border border-border/70 bg-background/40 p-3">
                    <div className="flex flex-wrap items-center gap-3 text-sm">
                      <span>{new Date(execution.executedAt).toLocaleString()}</span>
                      <span className="text-muted-foreground">status: {execution.executionStatus}</span>
                      <span className="text-muted-foreground">hits: {execution.hitCount}</span>
                    </div>
                  </div>
                ))
              )}
            </div>
          </CardContent>
        </Card>
      ) : null}
    </div>
  );
}
