import type { RunBundle, RunStep, RunStepName } from "./types";

const STEP_ORDER: RunStepName[] = [
  "clarify",
  "plan",
  "search",
  "extract",
  "verify",
  "write",
  "visualize"
];

const STEP_SET = new Set(STEP_ORDER);

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function coerceStepName(value: unknown): RunStepName {
  if (typeof value !== "string") {
    throw new Error("Step name must be a string");
  }
  const lowered = value.toLowerCase();
  if (!STEP_SET.has(lowered as RunStepName)) {
    throw new Error(`Unsupported step name: ${value}`);
  }
  return lowered as RunStepName;
}

export function parseRunBundle(raw: unknown): RunBundle {
  if (!isRecord(raw)) {
    throw new Error("Run bundle must be an object");
  }

  const run_id = raw.run_id;
  const created_at = raw.created_at;
  const query = raw.query;
  const steps = raw.steps;

  if (typeof run_id !== "string" || typeof created_at !== "string" || typeof query !== "string") {
    throw new Error("Run bundle must include run_id, created_at, and query");
  }
  if (!Array.isArray(steps)) {
    throw new Error("Run bundle steps must be an array");
  }

  const normalizedSteps: RunStep[] = steps.map((step, index) => {
    if (!isRecord(step)) {
      throw new Error(`Step at index ${index} must be an object`);
    }
    return {
      name: coerceStepName(step.name),
      input: step.input ?? null,
      output: step.output ?? null,
      status: typeof step.status === "string" ? (step.status as RunStep["status"]) : undefined,
      started_at: typeof step.started_at === "string" ? step.started_at : undefined,
      ended_at: typeof step.ended_at === "string" ? step.ended_at : undefined,
      trace_id: typeof step.trace_id === "string" ? step.trace_id : undefined
    };
  });

  return {
    run_id,
    created_at,
    query,
    meta: isRecord(raw.meta) ? raw.meta : undefined,
    steps: normalizedSteps
  };
}

export function getStep(runBundle: RunBundle | null, name: RunStepName): RunStep | undefined {
  if (!runBundle) {
    return undefined;
  }
  return runBundle.steps.find((step) => step.name === name);
}

export function sortSteps(steps: RunStep[]): RunStep[] {
  return [...steps].sort((a, b) => STEP_ORDER.indexOf(a.name) - STEP_ORDER.indexOf(b.name));
}
