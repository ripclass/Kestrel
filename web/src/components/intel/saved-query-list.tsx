"use client";

import { useEffect, useState } from "react";

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { detailFromPayload, readResponsePayload } from "@/lib/http";
import type { SavedQuerySummary, SavedQueryType, Viewer } from "@/types/domain";

const QUERY_TYPES: { value: SavedQueryType; label: string }[] = [
  { value: "entity_search", label: "Entity search" },
  { value: "transaction_search", label: "Transaction search" },
  { value: "str_filter", label: "STR filter" },
  { value: "alert_filter", label: "Alert filter" },
  { value: "case_filter", label: "Case filter" },
  { value: "custom", label: "Custom" },
];

export function SavedQueryList({ viewer }: { viewer: Viewer }) {
  const [records, setRecords] = useState<SavedQuerySummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [queryType, setQueryType] = useState<SavedQueryType>("entity_search");
  const [definition, setDefinition] = useState('{"filters":{}}');
  const [isShared, setIsShared] = useState(false);
  const [creating, setCreating] = useState(false);

  async function load() {
    setLoading(true);
    try {
      const response = await fetch("/api/saved-queries", { cache: "no-store" });
      const payload = (await readResponsePayload<{ savedQueries: SavedQuerySummary[] }>(response)) as
        | { savedQueries: SavedQuerySummary[] }
        | { detail?: string };
      if (!response.ok) {
        setError(detailFromPayload(payload, "Unable to load saved queries."));
        return;
      }
      setRecords((payload as { savedQueries: SavedQuerySummary[] }).savedQueries);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to load saved queries.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void load();
  }, []);

  async function create() {
    setCreating(true);
    setError(null);
    try {
      let parsedDefinition: Record<string, unknown>;
      try {
        parsedDefinition = definition.trim() ? JSON.parse(definition) : {};
      } catch {
        setError("Query definition must be valid JSON.");
        return;
      }
      const response = await fetch("/api/saved-queries", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name,
          description: description || null,
          queryType,
          queryDefinition: parsedDefinition,
          isShared,
        }),
      });
      const result = (await readResponsePayload<unknown>(response)) as { detail?: string };
      if (!response.ok) {
        setError(detailFromPayload(result, "Unable to save query."));
        return;
      }
      setName("");
      setDescription("");
      setDefinition('{"filters":{}}');
      setIsShared(false);
      void load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to save query.");
    } finally {
      setCreating(false);
    }
  }

  async function removeQuery(id: string) {
    const response = await fetch(`/api/saved-queries/${id}`, { method: "DELETE" });
    if (response.ok) {
      void load();
    }
  }

  const canMutate = viewer.role !== "viewer";

  return (
    <div className="space-y-6">
      {canMutate ? (
        <Card>
          <CardHeader>
            <CardTitle>New saved query</CardTitle>
            <CardDescription>
              Save a reusable filter. Mark as shared to expose it to your whole organization; otherwise only you see it.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
              <div className="space-y-2">
                <label className="text-xs uppercase tracking-[0.18em] text-muted-foreground">Name</label>
                <Input value={name} onChange={(event) => setName(event.target.value)} placeholder="High-value cash-outs" />
              </div>
              <div className="space-y-2">
                <label className="text-xs uppercase tracking-[0.18em] text-muted-foreground">Query type</label>
                <select
                  className="h-11 w-full rounded-xl border border-input bg-background/60 px-4 text-sm outline-none focus:border-primary"
                  value={queryType}
                  onChange={(event) => setQueryType(event.target.value as SavedQueryType)}
                >
                  {QUERY_TYPES.map((type) => (
                    <option key={type.value} value={type.value}>
                      {type.label}
                    </option>
                  ))}
                </select>
              </div>
              <div className="space-y-2 md:col-span-2">
                <label className="text-xs uppercase tracking-[0.18em] text-muted-foreground">Description</label>
                <Input
                  value={description}
                  onChange={(event) => setDescription(event.target.value)}
                  placeholder="Optional — when to use this query."
                />
              </div>
            </div>
            <div className="space-y-2">
              <label className="text-xs uppercase tracking-[0.18em] text-muted-foreground">Query definition (JSON)</label>
              <Textarea
                value={definition}
                onChange={(event) => setDefinition(event.target.value)}
                rows={5}
                className="font-mono text-xs"
              />
              <p className="text-xs text-muted-foreground">
                Shape is free-form per query type — the UI that consumes the saved query parses it.
              </p>
            </div>
            <div className="flex items-center gap-3">
              <label className="flex items-center gap-2 text-sm">
                <input
                  type="checkbox"
                  checked={isShared}
                  onChange={(event) => setIsShared(event.target.checked)}
                />
                Share with organization
              </label>
              <div className="flex-1" />
              <Button type="button" disabled={creating || !name.trim()} onClick={() => void create()}>
                {creating ? "Saving…" : "Save query"}
              </Button>
            </div>
            {error ? <p className="text-sm text-red-300">{error}</p> : null}
          </CardContent>
        </Card>
      ) : null}

      <Card>
        <CardHeader>
          <CardTitle>Saved queries</CardTitle>
          <CardDescription>Your personal queries and the queries shared by your organization.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          {loading ? (
            <p className="text-sm text-muted-foreground">Loading saved queries…</p>
          ) : records.length === 0 ? (
            <p className="text-sm text-muted-foreground">No saved queries yet. Save your first one above.</p>
          ) : (
            records.map((record) => (
              <div key={record.id} className="rounded-2xl border border-border/80 bg-background/50 p-4">
                <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
                  <div className="space-y-1">
                    <div className="flex flex-wrap items-center gap-3">
                      <p className="font-medium">{record.name}</p>
                      <span className="inline-flex items-center rounded-full border border-border px-2 py-0.5 text-[10px] font-semibold uppercase tracking-widest text-muted-foreground">
                        {record.queryType.replaceAll("_", " ")}
                      </span>
                      {record.isShared ? (
                        <span className="inline-flex items-center rounded-full border border-primary/40 bg-primary/10 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-widest text-primary">
                          Shared
                        </span>
                      ) : null}
                    </div>
                    {record.description ? (
                      <p className="text-sm text-muted-foreground">{record.description}</p>
                    ) : null}
                    <p className="text-xs text-muted-foreground">
                      Run {record.runCount} time{record.runCount === 1 ? "" : "s"}
                      {record.lastRunAt ? ` · last run ${new Date(record.lastRunAt).toLocaleString()}` : ""}
                    </p>
                  </div>
                  {viewer.id === record.userId ? (
                    <Button
                      type="button"
                      variant="ghost"
                      onClick={() => void removeQuery(record.id)}
                      className="text-red-300 hover:text-red-200"
                    >
                      Delete
                    </Button>
                  ) : null}
                </div>
              </div>
            ))
          )}
        </CardContent>
      </Card>
    </div>
  );
}
