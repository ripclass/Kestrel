"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
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
      <Card>
        <CardHeader>
          <CardTitle>Lookup masters</CardTitle>
          <CardDescription>
            Choose a table to inspect. {canMutate
              ? "As a regulator admin you can add, toggle, or remove entries."
              : "Regulator admins maintain this data — your view is read-only."}
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex flex-wrap gap-2">
            {TABLE_NAMES.map((table) => (
              <button
                key={table.value}
                type="button"
                onClick={() => setActive(table.value)}
                className={`rounded-full border px-3 py-1 text-xs font-medium transition ${
                  active === table.value
                    ? "border-primary bg-primary/15 text-primary"
                    : "border-border text-muted-foreground hover:border-primary/40"
                }`}
              >
                {table.label} ({countFor(table.value)})
              </button>
            ))}
          </div>
          {canMutate ? (
            <div className="grid gap-3 rounded-2xl border border-border/80 bg-background/40 p-4 md:grid-cols-4">
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
          {error ? <p className="text-sm text-red-300">{error}</p> : null}
          {notice ? <p className="text-sm text-primary/80">{notice}</p> : null}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>{TABLE_NAMES.find((t) => t.value === active)?.label ?? active}</CardTitle>
          <CardDescription>{entries.length} entries in scope.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-2">
          {loading ? (
            <p className="text-sm text-muted-foreground">Loading…</p>
          ) : entries.length === 0 ? (
            <p className="text-sm text-muted-foreground">No entries yet.</p>
          ) : (
            entries.map((entry) => (
              <div
                key={entry.id}
                className={`rounded-xl border px-4 py-3 ${
                  entry.isActive ? "border-border/70 bg-background/60" : "border-border/40 bg-background/30 opacity-60"
                }`}
              >
                <div className="flex flex-col gap-2 lg:flex-row lg:items-center lg:justify-between">
                  <div className="flex flex-wrap items-center gap-3">
                    <span className="font-mono text-sm">{entry.code}</span>
                    <span className="text-sm">{entry.value}</span>
                    {entry.description ? (
                      <span className="text-xs text-muted-foreground">{entry.description}</span>
                    ) : null}
                    {!entry.isActive ? (
                      <span className="text-xs uppercase tracking-widest text-muted-foreground">inactive</span>
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
                        className="text-red-300 hover:text-red-200"
                        onClick={() => void remove(entry)}
                      >
                        Delete
                      </Button>
                    </div>
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
