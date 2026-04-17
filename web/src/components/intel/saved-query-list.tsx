"use client";

import { useEffect, useState } from "react";

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

const selectClass =
  "h-11 w-full rounded-none border border-input bg-card px-4 text-sm outline-none focus:border-foreground";

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
    if (response.ok) void load();
  }

  const canMutate = viewer.role !== "viewer";

  return (
    <div className="space-y-6">
      {canMutate ? (
        <section className="border border-border">
          <div className="border-b border-border px-6 py-5">
            <p className="font-mono text-[10px] uppercase tracking-[0.28em] text-muted-foreground">
              <span aria-hidden className="mr-2 text-accent">┼</span>
              Section · New saved query
            </p>
            <p className="mt-2 text-sm leading-relaxed text-muted-foreground">
              Save a reusable filter. Mark as shared to expose it to your whole organisation; otherwise
              only you see it.
            </p>
          </div>
          <div className="space-y-5 p-6">
            <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
              <Field label="Name">
                <Input
                  value={name}
                  onChange={(event) => setName(event.target.value)}
                  placeholder="High-value cash-outs"
                />
              </Field>
              <Field label="Query type">
                <select
                  className={selectClass}
                  value={queryType}
                  onChange={(event) => setQueryType(event.target.value as SavedQueryType)}
                >
                  {QUERY_TYPES.map((type) => (
                    <option key={type.value} value={type.value}>
                      {type.label}
                    </option>
                  ))}
                </select>
              </Field>
              <div className="md:col-span-2">
                <Field label="Description">
                  <Input
                    value={description}
                    onChange={(event) => setDescription(event.target.value)}
                    placeholder="Optional — when to use this query."
                  />
                </Field>
              </div>
            </div>
            <Field label="Query definition (JSON)">
              <Textarea
                value={definition}
                onChange={(event) => setDefinition(event.target.value)}
                rows={5}
                className="font-mono text-xs"
              />
            </Field>
            <p className="font-mono text-[10px] uppercase tracking-[0.22em] text-muted-foreground">
              Shape is free-form per query type — the UI that consumes the saved query parses it
            </p>
            <div className="flex items-center gap-3 border-t border-border pt-4">
              <label className="flex items-center gap-2 font-mono text-[11px] uppercase tracking-[0.22em] text-muted-foreground">
                <input
                  type="checkbox"
                  checked={isShared}
                  onChange={(event) => setIsShared(event.target.checked)}
                />
                Share with organisation
              </label>
              <div className="flex-1" />
              <Button type="button" disabled={creating || !name.trim()} onClick={() => void create()}>
                {creating ? "Saving…" : "Save query"}
              </Button>
            </div>
            {error ? (
              <p className="font-mono text-xs uppercase tracking-[0.18em] text-destructive">
                <span aria-hidden className="mr-2">┼</span>ERROR · {error}
              </p>
            ) : null}
          </div>
        </section>
      ) : null}

      <section className="border border-border">
        <div className="border-b border-border px-6 py-5">
          <p className="font-mono text-[10px] uppercase tracking-[0.28em] text-muted-foreground">
            <span aria-hidden className="mr-2 text-accent">┼</span>
            Section · Saved queries
          </p>
          <p className="mt-2 text-sm leading-relaxed text-muted-foreground">
            Your personal queries and the queries shared by your organisation.
          </p>
        </div>
        <div className="space-y-3 p-6">
          {loading ? (
            <p className="font-mono text-[11px] uppercase tracking-[0.22em] text-muted-foreground">
              Loading saved queries…
            </p>
          ) : records.length === 0 ? (
            <p className="font-mono text-[11px] uppercase tracking-[0.22em] text-muted-foreground">
              No saved queries yet · save your first one above
            </p>
          ) : (
            records.map((record) => (
              <div key={record.id} className="border border-border bg-card px-5 py-4">
                <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
                  <div className="space-y-2">
                    <div className="flex flex-wrap items-center gap-3">
                      <p className="font-semibold text-foreground">{record.name}</p>
                      <span className="border border-border px-2.5 py-0.5 font-mono text-[10px] uppercase tracking-[0.22em] text-muted-foreground">
                        {record.queryType.replaceAll("_", " ")}
                      </span>
                      {record.isShared ? (
                        <span className="border border-accent/40 bg-accent/10 px-2.5 py-0.5 font-mono text-[10px] uppercase tracking-[0.22em] text-accent">
                          Shared
                        </span>
                      ) : null}
                    </div>
                    {record.description ? (
                      <p className="text-sm leading-relaxed text-muted-foreground">{record.description}</p>
                    ) : null}
                    <p className="font-mono text-[10px] uppercase tracking-[0.22em] text-muted-foreground">
                      Run <span className="tabular-nums text-foreground">{record.runCount}</span> time
                      {record.runCount === 1 ? "" : "s"}
                      {record.lastRunAt
                        ? ` · last run ${new Date(record.lastRunAt).toLocaleString()}`
                        : ""}
                    </p>
                  </div>
                  {viewer.id === record.userId ? (
                    <Button
                      type="button"
                      variant="ghost"
                      onClick={() => void removeQuery(record.id)}
                      className="text-destructive hover:text-destructive"
                    >
                      Delete
                    </Button>
                  ) : null}
                </div>
              </div>
            ))
          )}
        </div>
      </section>
    </div>
  );
}
