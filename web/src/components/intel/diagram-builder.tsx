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
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { detailFromPayload, readResponsePayload } from "@/lib/http";
import type { DiagramSummary, EntitySummary } from "@/types/domain";

type EntitySearchResponse = {
  results: EntitySummary[];
};

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
    setNodes((ns) => [
      ...ns,
      {
        id: entity.id,
        position: { x: (index % 3) * 240 + 40, y: Math.floor(index / 3) * 160 + 40 },
        data: { label: `${entity.displayName ?? entity.displayValue}\n${entity.entityType}` },
        style: {
          width: 200,
          padding: 12,
          borderRadius: 14,
          border: "1px solid rgba(88, 166, 166, 0.45)",
          background: entity.riskScore >= 70 ? "#381318" : "#101b2b",
          color: "#ecf2ff",
          whiteSpace: "pre-wrap",
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
      // Re-pull list
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
      <Card>
        <CardHeader>
          <CardTitle>New diagram</CardTitle>
          <CardDescription>
            Search for entities, drop them on the canvas, drag to connect, then save. Link to a case or STR to attach as evidence.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
            <div className="space-y-2">
              <label className="text-xs uppercase tracking-[0.18em] text-muted-foreground">Title</label>
              <Input value={title} onChange={(event) => setTitle(event.target.value)} placeholder="Shell company ring A" />
            </div>
            <div className="space-y-2">
              <label className="text-xs uppercase tracking-[0.18em] text-muted-foreground">Linked case ID</label>
              <Input value={linkedCaseId} onChange={(event) => setLinkedCaseId(event.target.value)} placeholder="UUID — optional" />
            </div>
            <div className="space-y-2">
              <label className="text-xs uppercase tracking-[0.18em] text-muted-foreground">Linked STR ID</label>
              <Input value={linkedStrId} onChange={(event) => setLinkedStrId(event.target.value)} placeholder="UUID — optional" />
            </div>
          </div>
          <div className="space-y-2">
            <label className="text-xs uppercase tracking-[0.18em] text-muted-foreground">Description</label>
            <Textarea value={description} onChange={(event) => setDescription(event.target.value)} />
          </div>
          <div className="space-y-3 rounded-2xl border border-border/80 bg-background/40 p-4">
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
                    className="rounded-full border border-border bg-background/60 px-3 py-1 text-xs hover:border-primary/50"
                  >
                    + {entity.displayName ?? entity.displayValue}
                  </button>
                ))}
              </div>
            ) : null}
          </div>
          <div className="h-[480px] overflow-hidden rounded-2xl border border-border/70">
            <ReactFlow
              nodes={nodes}
              edges={edges}
              onNodesChange={onNodesChange}
              onEdgesChange={onEdgesChange}
              onConnect={onConnect}
              fitView
            >
              <Background />
              <Controls />
              <MiniMap />
            </ReactFlow>
          </div>
          {error ? <p className="text-sm text-red-300">{error}</p> : null}
          {notice ? <p className="text-sm text-primary/80">{notice}</p> : null}
          <div className="flex justify-end">
            <Button type="button" onClick={() => void save()} disabled={saving || !canSave}>
              {saving ? "Saving…" : "Save diagram"}
            </Button>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Saved diagrams</CardTitle>
          <CardDescription>Diagrams authored by your organization.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          {existing.length === 0 ? (
            <p className="text-sm text-muted-foreground">No diagrams yet.</p>
          ) : (
            existing.map((diagram) => (
              <div key={diagram.id} className="rounded-2xl border border-border/80 bg-background/50 p-4">
                <div className="flex flex-wrap items-center gap-3">
                  <p className="font-medium">{diagram.title}</p>
                  {diagram.linkedCaseId ? (
                    <span className="text-xs text-primary">→ case {diagram.linkedCaseId.slice(0, 8)}</span>
                  ) : null}
                  {diagram.linkedStrId ? (
                    <span className="text-xs text-primary">→ STR {diagram.linkedStrId.slice(0, 8)}</span>
                  ) : null}
                </div>
                {diagram.description ? (
                  <p className="mt-1 text-sm text-muted-foreground">{diagram.description}</p>
                ) : null}
                <p className="mt-1 text-xs text-muted-foreground">
                  Updated {new Date(diagram.updatedAt).toLocaleString()}
                </p>
              </div>
            ))
          )}
        </CardContent>
      </Card>
    </div>
  );
}
