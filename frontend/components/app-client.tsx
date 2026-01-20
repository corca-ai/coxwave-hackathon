"use client";

import Link from "next/link";
import dynamic from "next/dynamic";
import { useEffect, useMemo, useRef, useState } from "react";
import type { GraphNodeData } from "../lib/graph";
import { buildGraph } from "../lib/graph";
import { prettyJson } from "../lib/json";
import { getStep, parseRunBundle, sortSteps } from "../lib/run-bundle";
import { parseStreamEvents } from "../lib/stream";
import type { RunBundle, RunStep, StreamEvent } from "../lib/types";
import PayloadPanel from "./payload-panel";
import ReportPreview from "./report-preview";
import StreamPanel from "./stream-panel";
import TracePanel from "./trace-panel";

const GraphPanel = dynamic(() => import("./graph-panel"), {
  ssr: false,
  loading: () => (
    <div className="graph-shell">
      <div className="panel-subtitle">Loading graph engine...</div>
    </div>
  )
});

const DEFAULT_MAX_EVENTS = Number.parseInt(
  process.env.NEXT_PUBLIC_STREAM_MAX_EVENTS ?? "200",
  10
);
const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000";

export default function AppClient() {
  const [runBundle, setRunBundle] = useState<RunBundle | null>(null);
  const [streamEvents, setStreamEvents] = useState<StreamEvent[]>([]);
  const [selectedStep, setSelectedStep] = useState<RunStep | null>(null);
  const [selectedNode, setSelectedNode] = useState<GraphNodeData | null>(null);
  const [selectedEvent, setSelectedEvent] = useState<StreamEvent | null>(null);
  const [streamCursor, setStreamCursor] = useState(0);
  const [isPlaying, setIsPlaying] = useState(false);
  const [speed, setSpeed] = useState(1);
  const [maxEvents, setMaxEvents] = useState(DEFAULT_MAX_EVENTS);
  const [error, setError] = useState<string | null>(null);
  const [serverQuery, setServerQuery] = useState("Graph RAG for scientific papers");
  const [serverStatus, setServerStatus] = useState<string | null>(null);
  const [isStreaming, setIsStreaming] = useState(false);
  const streamAbortRef = useRef<AbortController | null>(null);

  const orderedSteps = useMemo(
    () => (runBundle ? sortSteps(runBundle.steps) : []),
    [runBundle]
  );

  const graphData = useMemo(() => buildGraph(runBundle), [runBundle]);
  const reportOutput = getStep(runBundle, "write")?.output ?? null;
  const visualOutput = getStep(runBundle, "visualize")?.output ?? null;

  const maxVisibleEvents = useMemo(() => {
    return Math.min(maxEvents, streamEvents.length);
  }, [maxEvents, streamEvents.length]);

  const visibleEvents = useMemo(() => {
    const end = Math.min(streamCursor, maxVisibleEvents);
    return streamEvents.slice(0, end);
  }, [streamCursor, streamEvents, maxVisibleEvents]);

  useEffect(() => {
    setStreamCursor((current) => Math.min(current, maxVisibleEvents));
  }, [maxVisibleEvents]);

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const override = params.get("maxEvents");
    if (override) {
      const parsed = Number.parseInt(override, 10);
      if (!Number.isNaN(parsed)) {
        setMaxEvents(parsed);
      }
    }
  }, []);

  useEffect(() => {
    const storedBundle = window.localStorage.getItem("rn_last_run_bundle");
    const storedEvents = window.localStorage.getItem("rn_last_stream_events");
    if (storedBundle && storedEvents) {
      try {
        const parsedBundle = parseRunBundle(JSON.parse(storedBundle));
        const parsedEvents = parseStreamEvents(storedEvents);
        setRunBundle(parsedBundle);
        setSelectedStep(parsedBundle.steps[0] ?? null);
        setStreamEvents(parsedEvents);
        setStreamCursor(Math.min(parsedEvents.length, maxEvents));
        setSelectedEvent(parsedEvents[0] ?? null);
        return;
      } catch (err) {
        console.warn("Failed to load stored run bundle:", err);
      }
    }
    void loadSample();
  }, []);

  useEffect(() => {
    if (!isPlaying) {
      return;
    }

    if (streamCursor >= maxVisibleEvents) {
      setIsPlaying(false);
      return;
    }

    const interval = window.setInterval(() => {
      setStreamCursor((current) => Math.min(current + 1, maxVisibleEvents));
    }, Math.max(120, 520 / speed));

    return () => window.clearInterval(interval);
  }, [isPlaying, speed, streamCursor, maxVisibleEvents]);

  const runMeta = runBundle
    ? `${runBundle.run_id} | ${new Date(runBundle.created_at).toLocaleString()}`
    : "No run loaded";

  async function loadSample() {
    try {
      setError(null);
      const [bundleResponse, streamResponse] = await Promise.all([
        fetch("/demo/run-bundle.json"),
        fetch("/demo/stream-events.ndjson")
      ]);
      const bundleJson = await bundleResponse.json();
      const streamText = await streamResponse.text();

      const parsedRun = parseRunBundle(bundleJson);
      const parsedEvents = parseStreamEvents(streamText);

      setRunBundle(parsedRun);
      setSelectedStep(parsedRun.steps[0] ?? null);
      setStreamEvents(parsedEvents);
      setStreamCursor(0);
      setSelectedEvent(parsedEvents[0] ?? null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load demo data");
    }
  }

  async function handleRunBundleUpload(file: File) {
    try {
      setError(null);
      const text = await file.text();
      const parsed = parseRunBundle(JSON.parse(text));
      setRunBundle(parsed);
      setSelectedStep(parsed.steps[0] ?? null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to parse run bundle");
    }
  }

  async function handleStreamUpload(file: File) {
    try {
      setError(null);
      const text = await file.text();
      const parsed = parseStreamEvents(text);
      setStreamEvents(parsed);
      setStreamCursor(0);
      setSelectedEvent(parsed[0] ?? null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to parse stream events");
    }
  }

  async function checkServerHealth() {
    try {
      setServerStatus("checking...");
      const response = await fetch(`${API_BASE}/health`);
      if (!response.ok) {
        const text = await response.text();
        throw new Error(text || `Health check failed: ${response.status}`);
      }
      const payload = await response.json();
      const status = payload?.status === "ok" ? "ok" : "unknown";
      setServerStatus(`${status} (${payload?.agents_loaded ? "agents loaded" : "no agents"})`);
    } catch (err) {
      setServerStatus(err instanceof Error ? `error: ${err.message}` : "error");
    }
  }

  async function runServerStream() {
    if (!serverQuery.trim()) {
      setError("Query is required to run the server pipeline.");
      return;
    }

    if (streamAbortRef.current) {
      streamAbortRef.current.abort();
    }

    const controller = new AbortController();
    streamAbortRef.current = controller;
    setIsStreaming(true);
    setError(null);
    setServerStatus("streaming...");
    setIsPlaying(false);
    setStreamEvents([]);
    setStreamCursor(0);
    setSelectedEvent(null);
    setRunBundle(null);

    type StepState = { input?: unknown; output?: unknown; status?: RunStep["status"] };
    const stepState: Partial<Record<RunStep["name"], StepState>> = {};
    const stepOrder: RunStep["name"][] = [
      "clarify",
      "plan",
      "search",
      "extract",
      "verify",
      "write",
      "visualize"
    ];
    const agentToStep: Record<string, RunStep["name"]> = {
      clarifier: "clarify",
      searcher: "search",
      extractor: "extract",
      verifier: "verify",
      visualizer: "visualize"
    };

    const ensureStep = (name: RunStep["name"]): StepState => {
      if (!stepState[name]) {
        stepState[name] = {};
      }
      return stepState[name] as StepState;
    };

    const setStepInput = (name: RunStep["name"], input: unknown) => {
      const step = ensureStep(name);
      if (step.input === undefined) {
        step.input = input ?? null;
      }
    };

    const setStepOutput = (name: RunStep["name"], output: unknown) => {
      const step = ensureStep(name);
      step.output = output ?? null;
      if (!step.status) {
        step.status = "ok";
      }
    };

    const setStepError = (name: RunStep["name"]) => {
      const step = ensureStep(name);
      step.status = "error";
    };

    const streamEventsBuffer: StreamEvent[] = [];
    let firstTimestamp: string | null = null;
    let clarifierOutput: unknown = null;
    let planOutput: unknown = null;

    try {
      const response = await fetch(`${API_BASE}/api/run/stream`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          query: serverQuery.trim(),
          max_clarify_rounds: 2,
          max_orchestrator_loops: 3,
          skip_clarify: false
        }),
        signal: controller.signal
      });

      if (!response.ok) {
        const text = await response.text();
        throw new Error(text || `Server error: ${response.status}`);
      }

      if (!response.body) {
        throw new Error("Streaming response body is empty.");
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";
      let done = false;

      while (!done) {
        const { value, done: streamDone } = await reader.read();
        if (streamDone) {
          break;
        }
        buffer += decoder.decode(value, { stream: true });

        const parts = buffer.split("\n\n");
        buffer = parts.pop() ?? "";

        for (const part of parts) {
          const lines = part.split("\n").map((line) => line.trim());
          for (const line of lines) {
            if (!line.startsWith("data:")) {
              continue;
            }
            const payloadText = line.replace(/^data:\s*/, "");
            if (!payloadText) {
              continue;
            }
            if (payloadText === "[DONE]") {
              done = true;
              break;
            }

            const [normalized] = parseStreamEvents(payloadText);
            if (!normalized) {
              continue;
            }

            if (!firstTimestamp) {
              firstTimestamp = normalized.timestamp;
            }

            streamEventsBuffer.push(normalized);
            setStreamEvents((prev) => [...prev, normalized]);
            setStreamCursor(Math.min(streamEventsBuffer.length, maxEvents));
            setSelectedEvent((current) => current ?? normalized);

            const agent = normalized.agent ?? "";
            const stepName = agentToStep[agent];

            if (normalized.type === "agent_start" && stepName) {
              const payload = normalized.payload as { input?: unknown } | null;
              setStepInput(stepName, payload?.input ?? null);
            }

            if (normalized.type === "agent_complete" && stepName) {
              const payload = normalized.payload as { output?: unknown } | null;
              setStepOutput(stepName, payload?.output ?? null);
              if (stepName === "clarify") {
                clarifierOutput = payload?.output ?? null;
                if (clarifierOutput) {
                  setStepInput("plan", { clarifier: clarifierOutput });
                }
              }
              if (stepName === "visualize") {
                setStepInput("visualize", { report: stepState.write?.output ?? null });
              }
            }

            if (normalized.type === "plan_complete") {
              const payload = normalized.payload as { plan?: unknown } | null;
              planOutput = payload?.plan ?? null;
              setStepOutput("plan", planOutput);
              if (!stepState.plan?.input) {
                setStepInput("plan", { clarifier: clarifierOutput ?? null });
              }
            }

            if (normalized.type === "write_complete") {
              const payload = normalized.payload as { report?: unknown } | null;
              setStepOutput("write", payload?.report ?? null);
              if (planOutput || clarifierOutput) {
                setStepInput("write", { clarifier: clarifierOutput, plan: planOutput });
              }
            }

            if (normalized.type === "agent_complete" && agent === "orchestrator") {
              const payload = normalized.payload as { output?: { report?: unknown } } | null;
              if (payload?.output?.report && !stepState.write?.output) {
                setStepOutput("write", payload.output.report);
              }
            }

            if (normalized.type === "error" && stepName) {
              setStepError(stepName);
            }
          }
        }
      }

      const steps: RunStep[] = [];
      for (const name of stepOrder) {
        const step = stepState[name];
        if (!step) {
          continue;
        }
        if (step.input === undefined && step.output === undefined) {
          continue;
        }
        steps.push({
          name,
          input: step.input ?? null,
          output: step.output ?? null,
          status: step.status
        });
      }

      const runCandidate = {
        run_id: `run_server_${Date.now()}`,
        created_at: firstTimestamp ?? new Date().toISOString(),
        query: serverQuery.trim(),
        meta: { mode: "server", api_base: API_BASE },
        steps
      };

      const parsed = parseRunBundle(runCandidate);
      setRunBundle(parsed);
      setSelectedStep(parsed.steps[0] ?? null);
      setServerStatus("done");
    } catch (err) {
      if ((err as Error).name !== "AbortError") {
        setError(err instanceof Error ? err.message : "Server stream failed");
        setServerStatus("error");
      }
    } finally {
      setIsStreaming(false);
    }
  }

  return (
    <main>
      <header className="header">
        <div className="header-top">
          <div className="title-block">
            <h1 className="title">Research Navigator UI</h1>
            <p className="subtitle">
              Graph + trace + streaming observability for multi-agent runs.
            </p>
          </div>
          <span className="badge">App Router / Local-first</span>
        </div>
        <div className="controls">
          <div className="control-group">
            <button className="button primary" type="button" onClick={loadSample}>
              Load demo bundle
            </button>
            <Link className="button" href="/">
              Home
            </Link>
            <label className="button input-file" aria-label="Load run bundle">
              Load run bundle
              <input
                type="file"
                accept="application/json"
                onChange={(event) => {
                  const file = event.target.files?.[0];
                  if (file) {
                    void handleRunBundleUpload(file);
                  }
                }}
              />
            </label>
            <label className="button input-file" aria-label="Load stream events">
              Load stream NDJSON
              <input
                type="file"
                accept="application/x-ndjson,.ndjson,application/json"
                onChange={(event) => {
                  const file = event.target.files?.[0];
                  if (file) {
                    void handleStreamUpload(file);
                  }
                }}
              />
            </label>
          </div>
          <div className="control-group">
            <span className="pill">Server</span>
            <span className="pill">{API_BASE}</span>
            <input
              className="text-input"
              type="text"
              value={serverQuery}
              onChange={(event) => setServerQuery(event.target.value)}
              placeholder="Enter a research query"
            />
            <button
              className="button primary"
              type="button"
              onClick={runServerStream}
              disabled={isStreaming}
            >
              {isStreaming ? "Streaming..." : "Run server stream"}
            </button>
            <button className="button" type="button" onClick={checkServerHealth}>
              Check health
            </button>
            {serverStatus ? <span className="pill">{serverStatus}</span> : null}
          </div>
          <div className="control-group">
            <span className="pill">Max events</span>
            <input
              type="number"
              min={1}
              max={9999}
              value={maxEvents}
              onChange={(event) => setMaxEvents(Number(event.target.value))}
            />
            <span className="pill">Speed x{speed.toFixed(1)}</span>
            <input
              type="range"
              min={0.5}
              max={3}
              step={0.1}
              value={speed}
              onChange={(event) => setSpeed(Number(event.target.value))}
            />
          </div>
        </div>
        <div className="panel-subtitle">{runMeta}</div>
        {error ? <div className="panel-subtitle">Error: {error}</div> : null}
      </header>

      <section className="grid-top">
        <div className="panel">
          <div className="panel-header">
            <div>
              <div className="panel-title">Agent Trace</div>
              <div className="panel-subtitle">Input -> output payloads (always visible)</div>
            </div>
            <span className="pill">Steps {orderedSteps.length}</span>
          </div>
          <TracePanel
            steps={orderedSteps}
            selectedStep={selectedStep}
            onSelectStep={(step) => setSelectedStep(step)}
          />
        </div>

        <div className="panel">
          <div className="panel-header">
            <div>
              <div className="panel-title">Evidence Graph</div>
              <div className="panel-subtitle">Sources -> claims -> verifications -> report</div>
            </div>
            <span className="pill">Nodes {graphData.nodes.length}</span>
          </div>
          <div className="graph-shell">
            <GraphPanel
              nodes={graphData.nodes}
              edges={graphData.edges}
              onSelectNode={setSelectedNode}
            />
          </div>
        </div>

        <div className="panel">
          <div className="panel-header">
            <div>
              <div className="panel-title">Payload Inspector</div>
              <div className="panel-subtitle">Connection verification via raw JSON</div>
            </div>
          </div>
          <PayloadPanel
            selectedStep={selectedStep}
            selectedNode={selectedNode}
            selectedEvent={selectedEvent}
            prettyJson={prettyJson}
          />
        </div>
      </section>

      <section className="grid-bottom">
        <div className="panel">
          <div className="panel-header">
            <div>
              <div className="panel-title">Streaming Timeline</div>
              <div className="panel-subtitle">Real-time or replay mode</div>
            </div>
            <div className="control-group">
              <button
                className="button"
                type="button"
                onClick={() => setIsPlaying((prev) => !prev)}
              >
                {isPlaying ? "Pause" : "Play"}
              </button>
              <button
                className="button"
                type="button"
                onClick={() => {
                  setStreamCursor(0);
                  setIsPlaying(false);
                }}
              >
                Reset
              </button>
            </div>
          </div>
          <StreamPanel
            events={visibleEvents}
            selectedEvent={selectedEvent}
            onSelectEvent={setSelectedEvent}
            maxEvents={maxVisibleEvents}
            cursor={streamCursor}
          />
        </div>

        <div className="panel">
          <div className="panel-header">
            <div>
              <div className="panel-title">Visualizer Preview</div>
              <div className="panel-subtitle">Rendered from VisualOutput components</div>
            </div>
            <span className="pill">Live</span>
          </div>
          <ReportPreview reportOutput={reportOutput} visualOutput={visualOutput} />
        </div>
      </section>
    </main>
  );
}
