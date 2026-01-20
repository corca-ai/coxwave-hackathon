"use client";

import dynamic from "next/dynamic";
import { useEffect, useMemo, useState } from "react";
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
