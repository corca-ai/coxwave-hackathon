import type { NodeProps } from "@xyflow/react";
import type { GraphNodeData } from "../lib/graph";

export default function GraphNodeCard({ data, selected }: NodeProps<GraphNodeData>) {
  return (
    <div className={`graph-node ${selected ? "selected" : ""}`}>
      <div className="graph-node-kind">{data.kind}</div>
      <div className="graph-node-title">{data.label}</div>
      {data.subtitle ? <div className="graph-node-sub">{data.subtitle}</div> : null}
    </div>
  );
}
