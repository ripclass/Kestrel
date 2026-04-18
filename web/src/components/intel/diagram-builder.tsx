"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import {
  applyEdgeChanges,
  applyNodeChanges,
  Background,
  Controls,
  MiniMap,
  ReactFlow,
  addEdge,
  type Connection,
  type Edge,
  type EdgeChange,
  type Node,
  type NodeChange,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { detailFromPayload, readResponsePayload } from "@/lib/http";
import type { DiagramSummary, EntitySummary } from "@/types/domain";

type EntitySearchResponse = { results: EntitySummary[] };

const NODE_FG = "#EAE6DA";
const NODE_BG = "#15171C";
const NODE_BG_ALARM = "rgba(255, 56, 35, 0.10)";
const NODE_BORDER = "rgba(234, 230, 218, 0.18)";
const NODE_BORDER_ALARM = "#FF3823";

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

export function DiagramBuilder() {
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [linkedCaseId, setLinkedCaseId] = useState("");
  const [linkedStrId, setLinkedStrId] = useState("");

  const [nodes, setNodes] = useState<Node[]>([]);
  const [edges, setEdges] = useState<Edge[]>([]);

  const [searchTerm, setSearchTerm] = useState("");
  const [searchResults, setSearchResults] = useState<EntitySummary[]>([]);
  const [searching, setSearching] = useState(false);

  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [existing, setExisting] = useState<DiagramSummary[]>([]);

  useEffect(() => {
    void (async () => {
      const response = await fetch("/api/diagrams", { cache: "no-store" });
      const payload = (await readResponsePayload<{ diagrams: DiagramSummary[] }>(response)) as
        | { diagrams: DiagramSummary[] }
        | { detail?: string };
      if (response.ok) {
        setExisting((payload as { diagrams: DiagramSummary[] }).diagrams);
      }
    })();
  }, []);

  async function runSearch() {
    if (!searchTerm.trim()) return;
    setSearching(true);
    try {
      const response = await fetch(
        `/api/investigate/search?q=${encodeURIComponent(searchTerm)}`,
        { cache: "no-store" },
      );
      const payload = (await readResponsePayload<EntitySearchResponse>(response)) as
        | EntitySearchResponse
        | { detail?: string };
      if (response.ok) {
        setSearchResults((payload as EntitySearchResponse).results ?? []);
      }
    } finally {
      setSearching(false);
    }
  }

  const onNodesChange = useCallback(
    (changes: NodeChange[]) => setNodes((ns) => applyNodeChanges(changes, ns)),
    [],
  );
  const onEdgesChange = useCallback(
    (changes: EdgeChange[]) => setEdges((es) => applyEdgeChanges(changes, es)),
    [],
  );
  const onConnect = useCallback(
    (connection: Connection) => setEdges((es) => addEdge({ ...connection, label: "link" }, es)),
    [],
  );

  function addEntityNode(entity: EntitySummary) {
    if (nodes.some((node) => node.id === entity.id)) return;
    const index = nodes.length;
    const isAlarm = entity.riskScore >= 70;
    setNodes((ns) => [
      ...ns,
      {
        id: entity.id,
        position: { x: (index % 3) * 240 + 40, y: Math.floor(index / 3) * 160 + 40 },
        data: {
          label: `${entity.displayName ?? entity.displayValue}\n${entity.entityType}`,
        },
        style: {
          width: 200,
          padding: 12,
          borderRadius: 0,
          border: `1px solid ${isAlarm ? NODE_BORDER_ALARM : NODE_BORDER}`,
          background: isAlarm ? NODE_BG_ALARM : NODE_BG,
          color: NODE_FG,
          whiteSpace: "pre-wrap",
          fontFamily: "var(--font-plex-mono), ui-monospace, monospace",
          fontSize: 12,
          letterSpacing: "0.02em",
        },
      },
    ]);
  }

  async function save() {
    if (!title.trim()) {
      setError("Title is required.");
      return;
    }
    setSaving(true);
    setError(null);
    setNotice(null);
    try {
      const response = await fetch("/api/diagrams", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          title,
          description: description || null,
          graphDefinition: { nodes, edges },
          linkedCaseId: linkedCaseId || null,
          linkedStrId: linkedStrId || null,
        }),
      });
      const payload = (await readResponsePayload<unknown>(response)) as { detail?: string };
      if (!response.ok) {
        setError(detailFromPayload(payload, "Unable to save diagram."));
        return;
      }
      setNotice("Diagram saved.");
      setTitle("");
      setDescription("");
      setLinkedCaseId("");
      setLinkedStrId("");
      setNodes([]);
      setEdges([]);
      const listResponse = await fetch("/api/diagrams", { cache: "no-store" });
      if (listResponse.ok) {
        const listPayload = (await readResponsePayload<{ diagrams: DiagramSummary[] }>(listResponse)) as {
          diagrams: DiagramSummary[];
        };
        setExisting(listPayload.diagrams);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to save diagram.");
    } finally {
      setSaving(false);
    }
  }

  const canSave = useMemo(() => title.trim().length > 0 && nodes.length > 0, [title, nodes.length]);

  return (
    <div className="space-y-6">
      <section className="border border-border">
        <div className="border-b border-border px-6 py-5">
          <p className="font-mono text-[10px] uppercase tracking-[0.28em] text-muted-foreground">
            <span aria-hidden className="mr-2 text-accent">┼</span>
            Section · New diagram
          </p>
          <p className="mt-2 text-sm leading-relaxed text-muted-foreground">
            Search for entities, drop them on the canvas, drag to connect, then save. Link to a case or
            STR to attach as evidence.
          </p>
        </div>
        <div className="space-y-5 p-6">
          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
            <Field label="Title">
              <Input
                value={title}
                onChange={(event) => setTitle(event.target.value)}
                placeholder="Shell company ring A"
              />
            </Field>
            <Field label="Linked case ID">
              <Input
                value={linkedCaseId}
                onChange={(event) => setLinkedCaseId(event.target.value)}
                placeholder="UUID — optional"
              />
            </Field>
            <Field label="Linked STR ID">
              <Input
                value={linkedStrId}
                onChange={(event) => setLinkedStrId(event.target.value)}
                placeholder="UUID — optional"
              />
            </Field>
          </div>
          <Field label="Description">
            <Textarea
              value={description}
              onChange={(event) => setDescription(event.target.value)}
            />
          </Field>
          <div className="space-y-3 border border-border bg-card/40 p-4">
            <div className="flex gap-2">
              <Input
                value={searchTerm}
                onChange={(event) => setSearchTerm(event.target.value)}
                onKeyDown={(event) => {
                  if (event.key === "Enter") {
                    event.preventDefault();
                    void runSearch();
                  }
                }}
                placeholder="Search entities to add…"
              />
              <Button type="button" onClick={() => void runSearch()} disabled={searching}>
                {searching ? "Searching…" : "Search"}
              </Button>
            </div>
            {searchResults.length > 0 ? (
              <div className="flex flex-wrap gap-2">
                {searchResults.map((entity) => (
                  <button
                    key={entity.id}
                    type="button"
                    onClick={() => addEntityNode(entity)}
                    className="border border-border bg-card px-3 py-1 font-mono text-[11px] uppercase tracking-[0.22em] text-foreground transition hover:border-foreground"
                  >
                    + {entity.displayName ?? entity.displayValue}
                  </button>
                ))}
              </div>
            ) : null}
          </div>
          <div className="h-[480px] overflow-hidden border border-border bg-[var(--background)]">
            <ReactFlow
              nodes={nodes}
              edges={edges}
              onNodesChange={onNodesChange}
              onEdgesChange={onEdgesChange}
              onConnect={onConnect}
              fitView
              proOptions={{ hideAttribution: true }}
            >
              <Background color="rgba(234, 230, 218, 0.06)" gap={16} size={1} />
              <Controls showInteractive={false} />
              <MiniMap
                maskColor="rgba(15, 17, 21, 0.85)"
                nodeColor={NODE_FG}
                nodeStrokeColor="transparent"
                style={{ background: NODE_BG, border: `1px solid ${NODE_BORDER}` }}
              />
            </ReactFlow>
          </div>
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
            <Button type="button" onClick={() => void save()} disabled={saving || !canSave}>
              {saving ? "Saving…" : "Save diagram"}
            </Button>
          </div>
        </div>
      </section>

      <section className="border border-border">
        <div className="border-b border-border px-6 py-5">
          <p className="font-mono text-[10px] uppercase tracking-[0.28em] text-muted-foreground">
            <span aria-hidden className="mr-2 text-accent">┼</span>
            Section · Saved diagrams
          </p>
          <p className="mt-2 text-sm leading-relaxed text-muted-foreground">
            Diagrams authored by your organisation.
          </p>
        </div>
        <div className="space-y-3 p-6">
          {existing.length === 0 ? (
            <p className="font-mono text-[11px] uppercase tracking-[0.22em] text-muted-foreground">
              No diagrams yet
            </p>
          ) : (
            existing.map((diagram) => (
              <div key={diagram.id} className="border border-border bg-card px-5 py-4">
                <div className="flex flex-wrap items-center gap-3">
                  <p className="text-sm font-semibold text-foreground">{diagram.title}</p>
                  {diagram.linkedCaseId ? (
                    <span className="font-mono text-[11px] uppercase tracking-[0.22em] text-accent">
                      → case {diagram.linkedCaseId.slice(0, 8)}
                    </span>
                  ) : null}
                  {diagram.linkedStrId ? (
                    <span className="font-mono text-[11px] uppercase tracking-[0.22em] text-accent">
                      → STR {diagram.linkedStrId.slice(0, 8)}
                    </span>
                  ) : null}
                </div>
                {diagram.description ? (
                  <p className="mt-2 text-sm leading-relaxed text-muted-foreground">
                    {diagram.description}
                  </p>
                ) : null}
                <p className="mt-2 font-mono text-[10px] uppercase tracking-[0.22em] text-muted-foreground">
                  Updated {new Date(diagram.updatedAt).toLocaleString()}
                </p>
              </div>
            ))
          )}
        </div>
      </section>
    </div>
  );
}
