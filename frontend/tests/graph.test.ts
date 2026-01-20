import fs from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";
import { buildGraph } from "../lib/graph";
import { parseRunBundle } from "../lib/run-bundle";
import { writeJsonArtifact } from "./observability";

const demoPath = path.resolve(process.cwd(), "public/demo/run-bundle.json");

describe("graph builder", () => {
  it("builds graph nodes and edges from demo bundle", () => {
    const rawText = fs.readFileSync(demoPath, "utf-8");
    const bundle = parseRunBundle(JSON.parse(rawText));
    const graph = buildGraph(bundle);

    console.log("Graph output:");
    console.log(JSON.stringify(graph, null, 2));

    writeJsonArtifact("graph.output.json", graph);

    expect(graph.nodes.length).toBeGreaterThan(0);
    expect(graph.edges.length).toBeGreaterThan(0);
    expect(graph.nodes.some((node) => node.data?.kind === "query")).toBe(true);
  });
});
