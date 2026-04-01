"use client";

import { useMemo } from "react";
import { Background, Controls, MiniMap, ReactFlow, type Edge, type Node } from "@xyflow/react";
import "@xyflow/react/dist/style.css";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { NetworkControls } from "@/components/investigate/network-controls";
import { NodeInspector } from "@/components/investigate/node-inspector";
import { useGraphStore } from "@/stores/graph";
import type { NetworkGraph } from "@/types/domain";

export function NetworkCanvas({ graph }: { graph: NetworkGraph }) {
  const { selectedNodeId, setSelectedNodeId, showSuspiciousOnly } = useGraphStore();

  const nodes = useMemo<Node[]>(
    () =>
      graph.nodes
        .filter((node) => !showSuspiciousOnly || node.riskScore >= 70)
        .map((node, index) => ({
          id: node.id,
          position: { x: (index % 3) * 260, y: Math.floor(index / 3) * 180 },
          data: { label: `${node.label}\n${node.subtitle}` },
          style: {
            width: 220,
            padding: 12,
            borderRadius: 18,
            border: "1px solid rgba(88, 166, 166, 0.45)",
            background: node.riskScore >= 90 ? "#381318" : "#101b2b",
            color: "#ecf2ff",
            whiteSpace: "pre-wrap",
          },
        })),
    [graph.nodes, showSuspiciousOnly],
  );

  const edges = useMemo<Edge[]>(
    () =>
      graph.edges
        .filter((edge) => !showSuspiciousOnly || (edge.amount ?? 0) > 4_000_000 || edge.relation === "co_reported")
        .map((edge) => ({
          id: edge.id,
          source: edge.source,
          target: edge.target,
          label: edge.label,
          style: { stroke: "#58a6a6", strokeWidth: 2 },
        })),
    [graph.edges, showSuspiciousOnly],
  );

  const activeNode = graph.nodes.find((node) => node.id === selectedNodeId) ?? graph.nodes[0];

  return (
    <div className="grid gap-4 xl:grid-cols-[1.25fr_0.55fr]">
      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle>Network graph</CardTitle>
          <NetworkControls />
        </CardHeader>
        <CardContent>
          <div className="h-[420px] overflow-hidden rounded-2xl border border-border/70">
            <ReactFlow
              nodes={nodes}
              edges={edges}
              fitView
              onNodeClick={(_, node) => setSelectedNodeId(node.id)}
            >
              <Background />
              <Controls />
              <MiniMap />
            </ReactFlow>
          </div>
        </CardContent>
      </Card>
      <NodeInspector node={activeNode} />
    </div>
  );
}
