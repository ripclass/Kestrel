"use client";

import { useMemo } from "react";
import { Background, Controls, MiniMap, ReactFlow, type Edge, type Node } from "@xyflow/react";
import "@xyflow/react/dist/style.css";

import { NetworkControls } from "@/components/investigate/network-controls";
import { NodeInspector } from "@/components/investigate/node-inspector";
import { useGraphStore } from "@/stores/graph";
import type { NetworkGraph } from "@/types/domain";

const NODE_FG = "#EAE6DA";
const NODE_BG = "#15171C";
const NODE_BG_ALARM = "rgba(255, 56, 35, 0.10)";
const NODE_BORDER = "rgba(234, 230, 218, 0.18)";
const NODE_BORDER_ALARM = "#FF3823";
const EDGE_STROKE = "rgba(234, 230, 218, 0.25)";
const EDGE_STROKE_HOT = "#FF3823";

export function NetworkCanvas({ graph }: { graph: NetworkGraph }) {
  const { selectedNodeId, setSelectedNodeId, showSuspiciousOnly } = useGraphStore();

  const nodes = useMemo<Node[]>(
    () =>
      graph.nodes
        .filter((node) => !showSuspiciousOnly || node.riskScore >= 70)
        .map((node, index) => {
          const isAlarm = node.riskScore >= 90;
          const isSelected = node.id === selectedNodeId;
          return {
            id: node.id,
            position: { x: (index % 3) * 260, y: Math.floor(index / 3) * 180 },
            data: { label: `${node.label}\n${node.subtitle ?? ""}`.trim() },
            style: {
              width: 220,
              padding: 14,
              borderRadius: 0,
              border: `1px solid ${isAlarm ? NODE_BORDER_ALARM : isSelected ? NODE_FG : NODE_BORDER}`,
              background: isAlarm ? NODE_BG_ALARM : NODE_BG,
              color: NODE_FG,
              whiteSpace: "pre-wrap",
              fontFamily: "var(--font-plex-mono), ui-monospace, monospace",
              fontSize: 12,
              letterSpacing: "0.02em",
            },
          };
        }),
    [graph.nodes, showSuspiciousOnly, selectedNodeId],
  );

  const edges = useMemo<Edge[]>(
    () =>
      graph.edges
        .filter(
          (edge) => !showSuspiciousOnly || (edge.amount ?? 0) > 4_000_000 || edge.relation === "co_reported",
        )
        .map((edge) => {
          const isHot = (edge.amount ?? 0) > 4_000_000 || edge.relation === "co_reported";
          return {
            id: edge.id,
            source: edge.source,
            target: edge.target,
            label: edge.label,
            style: {
              stroke: isHot ? EDGE_STROKE_HOT : EDGE_STROKE,
              strokeWidth: isHot ? 1.75 : 1,
              strokeDasharray: isHot ? "4 4" : undefined,
            },
            labelStyle: {
              fontFamily: "var(--font-plex-mono), ui-monospace, monospace",
              fontSize: 10,
              fill: NODE_FG,
              letterSpacing: "0.08em",
              textTransform: "uppercase",
            },
            labelBgStyle: {
              fill: NODE_BG,
            },
            labelBgPadding: [4, 4] as [number, number],
          };
        }),
    [graph.edges, showSuspiciousOnly],
  );

  const activeNode = graph.nodes.find((node) => node.id === selectedNodeId) ?? graph.nodes[0];

  if (!activeNode || nodes.length === 0) {
    return (
      <section className="border border-border">
        <div className="border-b border-border px-6 py-5">
          <p className="font-mono text-[10px] uppercase tracking-[0.28em] text-muted-foreground">
            <span aria-hidden className="mr-2 text-accent">┼</span>
            Section · Network graph
          </p>
        </div>
        <p className="px-6 py-6 font-mono text-xs uppercase tracking-[0.22em] text-muted-foreground">
          No linked graph context is available for this record yet
        </p>
      </section>
    );
  }

  return (
    <div className="grid gap-6 xl:grid-cols-[1.25fr_0.55fr]">
      <section className="border border-border">
        <div className="flex items-center justify-between border-b border-border px-6 py-4">
          <p className="font-mono text-[10px] uppercase tracking-[0.28em] text-muted-foreground">
            <span aria-hidden className="mr-2 text-accent">┼</span>
            Section · Network graph
          </p>
          <NetworkControls />
        </div>
        <div className="h-[460px] overflow-hidden border-t border-border bg-[var(--background)]">
          <ReactFlow
            nodes={nodes}
            edges={edges}
            fitView
            onNodeClick={(_, node) => setSelectedNodeId(node.id)}
            proOptions={{ hideAttribution: true }}
          >
            <Background color="rgba(234, 230, 218, 0.06)" gap={16} size={1} />
            <Controls showInteractive={false} />
            <MiniMap
              maskColor="rgba(15, 17, 21, 0.85)"
              nodeColor={(n) => {
                const match = graph.nodes.find((x) => x.id === n.id);
                return match && match.riskScore >= 90 ? EDGE_STROKE_HOT : NODE_FG;
              }}
              nodeStrokeColor="transparent"
              style={{ background: NODE_BG, border: `1px solid ${NODE_BORDER}` }}
            />
          </ReactFlow>
        </div>
      </section>
      <NodeInspector node={activeNode} />
    </div>
  );
}
