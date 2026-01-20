"use client";

import {
  Background,
  Controls,
  MiniMap,
  ReactFlow,
  type Edge,
  type Node,
  type NodeMouseHandler
} from "@xyflow/react";
import { useMemo, useState } from "react";
import type { GraphNodeData } from "../lib/graph";
import GraphNodeCard from "./graph-node-card";

interface GraphPanelProps {
  nodes: Node<GraphNodeData>[];
  edges: Edge[];
  onSelectNode: (node: GraphNodeData | null) => void;
}

export default function GraphPanel({ nodes, edges, onSelectNode }: GraphPanelProps) {
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);

  const nodeTypes = useMemo(() => ({ card: GraphNodeCard }), []);

  const decoratedNodes = useMemo(() => {
    return nodes.map((node) => ({
      ...node,
      selected: node.id === selectedNodeId
    }));
  }, [nodes, selectedNodeId]);

  const handleNodeClick: NodeMouseHandler = (_event, node) => {
    setSelectedNodeId(node.id);
    onSelectNode(node.data ?? null);
  };

  return (
    <ReactFlow
      nodes={decoratedNodes}
      edges={edges}
      nodeTypes={nodeTypes}
      fitView
      onNodeClick={handleNodeClick}
      onPaneClick={() => {
        setSelectedNodeId(null);
        onSelectNode(null);
      }}
    >
      <MiniMap
        pannable
        zoomable
        nodeColor={(node) => {
          switch (node.data?.kind) {
            case "source":
              return "#5ce1c6";
            case "claim":
              return "#f6b26b";
            case "verification":
              return "#9ac3ff";
            case "report":
              return "#ffcfe1";
            case "visual":
              return "#f5f7fb";
            case "citation":
              return "#b8ffed";
            default:
              return "#8aa4b8";
          }
        }}
      />
      <Controls showInteractive={false} />
      <Background color="#1b2733" gap={20} size={1} />
    </ReactFlow>
  );
}
