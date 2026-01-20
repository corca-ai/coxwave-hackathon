import fs from "node:fs";
import path from "node:path";
import dotenv from "dotenv";

const rootEnv = path.resolve(process.cwd(), "..", ".env");
dotenv.config({ path: rootEnv });

const artifactDir = path.resolve(process.cwd(), "tests/_artifacts");
fs.mkdirSync(artifactDir, { recursive: true });

const runBundlePath = path.resolve(process.cwd(), "public/demo/run-bundle.json");
const streamPath = path.resolve(process.cwd(), "public/demo/stream-events.ndjson");

const runBundleRaw = fs.readFileSync(runBundlePath, "utf-8");
const streamRaw = fs.readFileSync(streamPath, "utf-8");

console.log("E2E demo input: run bundle");
console.log(runBundleRaw);
console.log("E2E demo input: stream events");
console.log(streamRaw);

const runBundle = JSON.parse(runBundleRaw);
const streamEvents = streamRaw
  .trim()
  .split(/\r?\n/)
  .filter((line) => line.trim().length > 0)
  .map((line) => JSON.parse(line));

if (!runBundle.run_id || !runBundle.created_at || !runBundle.query) {
  throw new Error("Run bundle missing required fields");
}

if (!Array.isArray(runBundle.steps) || runBundle.steps.length === 0) {
  throw new Error("Run bundle steps missing");
}

if (streamEvents.length === 0) {
  throw new Error("Stream events missing");
}

const output = {
  run_id: runBundle.run_id,
  step_count: runBundle.steps.length,
  event_count: streamEvents.length
};

console.log("E2E demo output:");
console.log(JSON.stringify(output, null, 2));

fs.writeFileSync(path.join(artifactDir, "frontend-e2e.input.run-bundle.json"), runBundleRaw);
fs.writeFileSync(path.join(artifactDir, "frontend-e2e.input.stream.ndjson"), streamRaw);
fs.writeFileSync(
  path.join(artifactDir, "frontend-e2e.output.summary.json"),
  JSON.stringify(output, null, 2)
);
