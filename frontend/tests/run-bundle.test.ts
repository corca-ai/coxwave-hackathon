import fs from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";
import { parseRunBundle } from "../lib/run-bundle";
import { writeArtifact, writeJsonArtifact } from "./observability";

const demoPath = path.resolve(process.cwd(), "public/demo/run-bundle.json");

describe("run bundle parser", () => {
  it("parses demo run bundle and logs payloads", () => {
    const rawText = fs.readFileSync(demoPath, "utf-8");
    console.log("Run bundle input:");
    console.log(rawText);

    const parsed = parseRunBundle(JSON.parse(rawText));
    console.log("Run bundle output:");
    console.log(JSON.stringify(parsed, null, 2));

    writeArtifact("run-bundle.input.json", rawText);
    writeJsonArtifact("run-bundle.output.json", parsed);

    expect(parsed.run_id.length).toBeGreaterThan(0);
    expect(parsed.steps.length).toBeGreaterThan(0);
  });
});
