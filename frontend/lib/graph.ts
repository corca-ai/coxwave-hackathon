import type { Edge, Node } from "@xyflow/react";
import type {
  Claim,
  ReportOutput,
  RunBundle,
  Source,
  Verification,
  VisualComponent,
  VisualOutput
} from "./types";
import { truncate } from "./json";
import { getStep } from "./run-bundle";

export type GraphKind =
  | "query"
  | "source"
  | "claim"
  | "verification"
  | "report"
  | "citation"
  | "visual";

export interface GraphNodeData {
  label: string;
  subtitle?: string;
  kind: GraphKind;
  payload: unknown;
}

export interface GraphData {
  nodes: Node<GraphNodeData>[];
  edges: Edge[];
}

const COLUMN_ORDER: GraphKind[] = [
  "query",
  "source",
  "claim",
  "verification",
  "report",
  "citation",
  "visual"
];

const COLUMN_MAP = new Map(COLUMN_ORDER.map((kind, index) => [kind, index]));

export function buildGraph(runBundle: RunBundle | null): GraphData {
  if (!runBundle) {
    return { nodes: [], edges: [] };
  }

  const nodes: Node<GraphNodeData>[] = [];
  const edges: Edge[] = [];
  const columnCounts = new Map<number, number>();

  const addNode = (kind: GraphKind, label: string, payload: unknown, subtitle?: string) => {
    const columnIndex = COLUMN_MAP.get(kind) ?? 0;
    const currentCount = columnCounts.get(columnIndex) ?? 0;
    const nodeId = `${kind}-${currentCount + 1}`;
    const x = columnIndex * 240;
    const y = currentCount * 140;

    columnCounts.set(columnIndex, currentCount + 1);

    nodes.push({
      id: nodeId,
      type: "card",
      position: { x, y },
      data: {
        label,
        subtitle,
        kind,
        payload
      }
    });

    return nodeId;
  };

  const queryNodeId = addNode(
    "query",
    "Query",
    { query: runBundle.query },
    truncate(runBundle.query, 64)
  );

  const searchOutput = getStep(runBundle, "search")?.output as {
    sources?: Source[];
  } | null;
  const extractOutput = getStep(runBundle, "extract")?.output as {
    claims?: Claim[];
  } | null;
  const verifyOutput = getStep(runBundle, "verify")?.output as {
    verdicts?: Verification[];
  } | null;
  const reportOutput = getStep(runBundle, "write")?.output as ReportOutput | null;
  const visualOutput = getStep(runBundle, "visualize")?.output as VisualOutput | null;

  const sources = Array.isArray(searchOutput?.sources) ? searchOutput.sources : [];
  const claims = Array.isArray(extractOutput?.claims) ? extractOutput.claims : [];
  const verdicts = Array.isArray(verifyOutput?.verdicts) ? verifyOutput.verdicts : [];

  const sourceNodeMap = new Map<string, string>();
  sources.forEach((source) => {
    const nodeId = addNode(
      "source",
      source.source_id,
      source,
      truncate(source.title, 48)
    );
    sourceNodeMap.set(source.source_id, nodeId);
    edges.push({
      id: `edge-${queryNodeId}-${nodeId}`,
      source: queryNodeId,
      target: nodeId,
      animated: true
    });
  });

  const claimNodeMap = new Map<string, string>();
  claims.forEach((claim) => {
    const confidence =
      typeof claim.confidence === "number" ? claim.confidence : Number.NaN;
    const nodeId = addNode(
      "claim",
      truncate(claim.claim, 52),
      claim,
      Number.isNaN(confidence) ? "conf n/a" : `conf ${confidence.toFixed(2)}`
    );
    claimNodeMap.set(claim.claim, nodeId);

    if (claim.source_id && sourceNodeMap.has(claim.source_id)) {
      const sourceNode = sourceNodeMap.get(claim.source_id) as string;
      edges.push({
        id: `edge-${sourceNode}-${nodeId}`,
        source: sourceNode,
        target: nodeId
      });
    }
  });

  verdicts.forEach((verdict, index) => {
    const nodeId = addNode(
      "verification",
      `${verdict.verdict}`,
      verdict,
      truncate(verdict.claim, 44)
    );
    const claimNode = claimNodeMap.get(verdict.claim);
    if (claimNode) {
      edges.push({
        id: `edge-${claimNode}-${nodeId}`,
        source: claimNode,
        target: nodeId
      });
    } else if (verdict.source_id && sourceNodeMap.has(verdict.source_id)) {
      const sourceNode = sourceNodeMap.get(verdict.source_id) as string;
      edges.push({
        id: `edge-${sourceNode}-${nodeId}-${index}`,
        source: sourceNode,
        target: nodeId
      });
    }
  });

  const reportNodes: Record<string, string> = {};
  if (reportOutput) {
    if (reportOutput.title) {
      reportNodes.title = addNode("report", "Report Title", reportOutput, reportOutput.title);
    }
    if (reportOutput.executive_summary) {
      reportNodes.executive_summary = addNode(
        "report",
        "Executive Summary",
        reportOutput,
        truncate(reportOutput.executive_summary, 52)
      );
    }
    if (Array.isArray(reportOutput.key_findings) && reportOutput.key_findings.length > 0) {
      reportNodes.key_findings = addNode(
        "report",
        "Key Findings",
        reportOutput,
        `${reportOutput.key_findings.length} items`
      );
    }
    if (Array.isArray(reportOutput.limitations) && reportOutput.limitations.length > 0) {
      reportNodes.limitations = addNode(
        "report",
        "Limitations",
        reportOutput,
        `${reportOutput.limitations.length} items`
      );
    }
    if (Array.isArray(reportOutput.citations) && reportOutput.citations.length > 0) {
      reportNodes.citations = addNode(
        "report",
        "Citations",
        reportOutput,
        `${reportOutput.citations.length} links`
      );
    }
  }

  const citationNodes: string[] = [];
  if (reportOutput?.citations) {
    reportOutput.citations.forEach((citation, index) => {
      const nodeId = addNode(
        "citation",
        `Citation ${index + 1}`,
        { citation },
        truncate(citation, 48)
      );
      citationNodes.push(nodeId);
    });
  }

  if (reportNodes.citations) {
    citationNodes.forEach((citationId, index) => {
      edges.push({
        id: `edge-${reportNodes.citations}-${citationId}-${index}`,
        source: reportNodes.citations,
        target: citationId
      });
    });
  }

  if (visualOutput?.components) {
    visualOutput.components.forEach((component, index) => {
      const nodeId = addNode(
        "visual",
        component.type,
        component,
        componentSubtitle(component)
      );
      const mappedSection = mapComponentSection(component);
      const reportNode = mappedSection ? reportNodes[mappedSection] : undefined;
      if (reportNode) {
        edges.push({
          id: `edge-${nodeId}-${reportNode}-${index}`,
          source: nodeId,
          target: reportNode
        });
      }
    });
  }

  return { nodes, edges };
}

function componentSubtitle(component: VisualComponent): string | undefined {
  const props = component.props ?? {};
  if (typeof props.text === "string") {
    return truncate(props.text, 44);
  }
  if (typeof props.title === "string") {
    return truncate(props.title, 44);
  }
  if (Array.isArray(props.items)) {
    return `${props.items.length} items`;
  }
  return undefined;
}

function mapComponentSection(component: VisualComponent): keyof ReportOutput | null {
  switch (component.type) {
    case "heading":
      return "title";
    case "paragraph":
      return "executive_summary";
    case "bullets":
      return "key_findings";
    case "callout":
      return "limitations";
    case "list":
      return "citations";
    default:
      return null;
  }
}
