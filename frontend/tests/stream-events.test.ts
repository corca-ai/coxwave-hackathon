import fs from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";
import { parseStreamEvents } from "../lib/stream";
import { writeArtifact, writeJsonArtifact } from "./observability";

const demoPath = path.resolve(process.cwd(), "public/demo/stream-events.ndjson");

describe("stream events parser", () => {
  it("parses demo stream events and logs payloads", () => {
    const rawText = fs.readFileSync(demoPath, "utf-8");
    console.log("Stream events input:");
    console.log(rawText);

    const parsed = parseStreamEvents(rawText);
    console.log("Stream events output:");
    console.log(JSON.stringify(parsed, null, 2));

    writeArtifact("stream-events.input.ndjson", rawText);
    writeJsonArtifact("stream-events.output.json", parsed);

    expect(parsed.length).toBeGreaterThan(0);
    expect(parsed[0].id.length).toBeGreaterThan(0);
  });
});
