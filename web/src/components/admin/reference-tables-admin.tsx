"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { detailFromPayload, readResponsePayload } from "@/lib/http";
import type {
  OrgType,
  ReferenceEntry,
  ReferenceTableMeta,
  ReferenceTableName,
  Role,
} from "@/types/domain";

const TABLE_NAMES: { value: ReferenceTableName; label: string }[] = [
  { value: "banks", label: "Banks & MFS" },
  { value: "channels", label: "Channels" },
  { value: "categories", label: "Categories" },
  { value: "countries", label: "Countries" },
  { value: "currencies", label: "Currencies" },
  { value: "agencies", label: "Agencies" },
  { value: "branches", label: "Branches" },
];

type EntriesResponse = { entries: ReferenceEntry[] };
type CountsResponse = { tables: ReferenceTableMeta[] };

export function ReferenceTablesAdmin({
  viewerRole,
  orgType,
}: {
  viewerRole: Role;
  orgType: OrgType;
}) {
  const [active, setActive] = useState<ReferenceTableName>("banks");
  const [entries, setEntries] = useState<ReferenceEntry[]>([]);
  const [counts, setCounts] = useState<ReferenceTableMeta[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const [newCode, setNewCode] = useState("");
  const [newValue, setNewValue] = useState("");
  const [newDescription, setNewDescription] = useState("");
  const [creating, setCreating] = useState(false);

  const canMutate = useMemo(
    () => orgType === "regulator" && ["admin", "superadmin"].includes(viewerRole),
    [orgType, viewerRole],
  );

  const loadEntries = useCallback(async () => {
    setLoading(true);
    try {
      const response = await fetch(
        `/api/reference-tables?table_name=${active}&include_inactive=true`,
        { cache: "no-store" },
      );
      const payload = (await readResponsePayload<EntriesResponse>(response)) as
        | EntriesResponse
        | { detail?: string };
      if (!response.ok) {
        setError(detailFromPayload(payload, "Unable to load reference entries."));
        return;
      }
      setEntries((payload as EntriesResponse).entries);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to load reference entries.");
    } finally {
      setLoading(false);
    }
  }, [active]);

  const loadCounts = useCallback(async () => {
    const response = await fetch("/api/reference-tables/tables", { cache: "no-store" });
    if (response.ok) {
      const payload = (await readResponsePayload<CountsResponse>(response)) as CountsResponse;
      setCounts(payload.tables);
    }
  }, []);

  useEffect(() => {
    void loadEntries();
  }, [loadEntries]);

  useEffect(() => {
    void loadCounts();
  }, [loadCounts]);

  async function create() {
    if (!newCode.trim() || !newValue.trim()) {
      setError("Code and value are required.");
      return;
    }
    setCreating(true);
    setError(null);
    try {
      const response = await fetch("/api/reference-tables", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          tableName: active,
          code: newCode.trim(),
          value: newValue.trim(),
          description: newDescription || null,
        }),
      });
      const payload = (await readResponsePayload<unknown>(response)) as { detail?: string };
      if (!response.ok) {
        setError(detailFromPayload(payload, "Unable to add entry."));
        return;
      }
      setNewCode("");
      setNewValue("");
      setNewDescription("");
      setNotice("Entry added.");
      void loadEntries();
      void loadCounts();
    } finally {
      setCreating(false);
    }
  }

  async function toggleActive(entry: ReferenceEntry) {
    const response = await fetch(`/api/reference-tables/${entry.id}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ isActive: !entry.isActive }),
    });
    if (response.ok) {
      void loadEntries();
      void loadCounts();
    }
  }

  async function remove(entry: ReferenceEntry) {
    const response = await fetch(`/api/reference-tables/${entry.id}`, { method: "DELETE" });
    if (response.ok) {
      void loadEntries();
      void loadCounts();
    }
  }

  const countFor = (name: ReferenceTableName) =>
    counts.find((c) => c.tableName === name)?.activeCount ?? 0;

  return (
    <div className="space-y-6">
      <section className="border border-border">
        <div className="border-b border-border px-6 py-5">
          <p className="font-mono text-[10px] uppercase tracking-[0.28em] text-muted-foreground">
            <span aria-hidden className="mr-2 text-accent">┼</span>
            Section · Lookup masters
          </p>
          <p className="mt-2 text-sm leading-relaxed text-muted-foreground">
            Choose a table to inspect.{" "}
            {canMutate
              ? "As a regulator admin you can add, toggle, or remove entries."
              : "Regulator admins maintain this data — your view is read-only."}
          </p>
        </div>
        <div className="space-y-4 p-6">
          <div className="flex flex-wrap gap-0 border border-border">
            {TABLE_NAMES.map((table) => (
              <button
                key={table.value}
                type="button"
                onClick={() => setActive(table.value)}
                className={`border-r border-border px-4 py-2 font-mono text-[11px] uppercase tracking-[0.22em] transition last:border-r-0 ${
                  active === table.value
                    ? "bg-foreground text-background"
                    : "text-muted-foreground hover:bg-foreground/[0.04] hover:text-foreground"
                }`}
              >
                {table.label}{" "}
                <span className="tabular-nums opacity-70">({countFor(table.value)})</span>
              </button>
            ))}
          </div>
          {canMutate ? (
            <div className="grid gap-3 border border-border bg-card/40 p-4 md:grid-cols-4">
              <Input value={newCode} onChange={(event) => setNewCode(event.target.value)} placeholder="Code" />
              <Input value={newValue} onChange={(event) => setNewValue(event.target.value)} placeholder="Value" />
              <Input
                value={newDescription}
                onChange={(event) => setNewDescription(event.target.value)}
                placeholder="Description (optional)"
              />
              <Button type="button" disabled={creating} onClick={() => void create()}>
                {creating ? "Adding…" : "Add entry"}
              </Button>
            </div>
          ) : null}
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
        </div>
      </section>

      <section className="border border-border">
        <div className="border-b border-border px-6 py-5">
          <p className="font-mono text-[10px] uppercase tracking-[0.28em] text-muted-foreground">
            <span aria-hidden className="mr-2 text-accent">┼</span>
            Section · {TABLE_NAMES.find((t) => t.value === active)?.label ?? active}
          </p>
          <p className="mt-2 text-sm leading-relaxed text-muted-foreground">
            <span className="tabular-nums text-foreground">{entries.length}</span> entries in scope.
          </p>
        </div>
        <div className="p-6">
          {loading ? (
            <p className="font-mono text-[11px] uppercase tracking-[0.22em] text-muted-foreground">
              Loading…
            </p>
          ) : entries.length === 0 ? (
            <p className="font-mono text-[11px] uppercase tracking-[0.22em] text-muted-foreground">
              No entries yet
            </p>
          ) : (
            <ul className="divide-y divide-border border border-border">
              {entries.map((entry) => (
                <li
                  key={entry.id}
                  className={`flex flex-col gap-2 px-4 py-3 lg:flex-row lg:items-center lg:justify-between ${
                    entry.isActive ? "" : "opacity-60"
                  }`}
                >
                  <div className="flex flex-wrap items-center gap-3">
                    <span className="font-mono text-sm text-foreground">{entry.code}</span>
                    <span className="text-sm text-foreground">{entry.value}</span>
                    {entry.description ? (
                      <span className="text-xs text-muted-foreground">{entry.description}</span>
                    ) : null}
                    {!entry.isActive ? (
                      <span className="font-mono text-[10px] uppercase tracking-[0.22em] text-muted-foreground">
                        inactive
                      </span>
                    ) : null}
                  </div>
                  {canMutate ? (
                    <div className="flex flex-wrap gap-2">
                      <Button type="button" variant="ghost" onClick={() => void toggleActive(entry)}>
                        {entry.isActive ? "Deactivate" : "Activate"}
                      </Button>
                      <Button
                        type="button"
                        variant="ghost"
                        className="text-destructive hover:text-destructive"
                        onClick={() => void remove(entry)}
                      >
                        Delete
                      </Button>
                    </div>
                  ) : null}
                </li>
              ))}
            </ul>
          )}
        </div>
      </section>
    </div>
  );
}
