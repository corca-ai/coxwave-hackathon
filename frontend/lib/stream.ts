import type { StreamEvent } from "./types";

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function normalizeStreamEvent(raw: unknown, index: number): StreamEvent {
  if (!isRecord(raw)) {
    throw new Error(`Stream event at index ${index} must be an object`);
  }

  const id = raw.id;
  const timestamp = raw.timestamp;
  const type = raw.type;

  if (typeof id !== "string" || typeof timestamp !== "string" || typeof type !== "string") {
    throw new Error(`Stream event at index ${index} missing required fields`);
  }

  return {
    id,
    timestamp,
    type,
    agent: typeof raw.agent === "string" ? raw.agent : undefined,
    stage: typeof raw.stage === "string" ? raw.stage : undefined,
    sequence: typeof raw.sequence === "number" ? raw.sequence : index,
    payload: raw.payload ?? null
  };
}

export function parseStreamEvents(text: string): StreamEvent[] {
  const trimmed = text.trim();
  if (!trimmed) {
    return [];
  }

  if (trimmed.startsWith("[")) {
    const parsed = JSON.parse(trimmed) as unknown;
    if (!Array.isArray(parsed)) {
      throw new Error("Stream event JSON array expected");
    }
    return parsed.map((item, index) => normalizeStreamEvent(item, index));
  }

  const lines = trimmed.split(/\r?\n/).filter((line) => line.trim().length > 0);
  return lines.map((line, index) => normalizeStreamEvent(JSON.parse(line), index));
}
