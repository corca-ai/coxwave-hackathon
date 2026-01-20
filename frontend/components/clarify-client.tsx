"use client";

import Link from "next/link";
import { useMemo, useRef, useState } from "react";
import { prettyJson } from "../lib/json";
import { parseRunBundle } from "../lib/run-bundle";
import { parseStreamEvents } from "../lib/stream";
import type { RunStep, StreamEvent } from "../lib/types";
import StreamPanel from "./stream-panel";

interface ClarifyOutput {
  is_clear_enough: boolean;
  clarifying_questions: string[];
  interpreted_query: string;
  assumptions: string[];
}

interface ClarifyAnswer {
  question: string;
  answer: string;
}

interface ClarifyRound {
  input: string;
  output: ClarifyOutput;
  answers: ClarifyAnswer[];
  skipped: boolean;
}

type ChatMessage = {
  role: "user" | "assistant";
  text: string;
};

const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000";

function buildFollowupQuery(originalQuery: string, answers: ClarifyAnswer[]): string {
  const lines = [`Original query: ${originalQuery}`, "Clarifications:"];
  for (const answer of answers) {
    lines.push(`Q: ${answer.question}`);
    lines.push(`A: ${answer.answer}`);
  }
  return lines.join("\n");
}

export default function ClarifyClient() {
  const [queryInput, setQueryInput] = useState("");
  const [originalQuery, setOriginalQuery] = useState("");
  const [currentQuery, setCurrentQuery] = useState("");
  const [clarifyOutput, setClarifyOutput] = useState<ClarifyOutput | null>(null);
  const [pendingOutput, setPendingOutput] = useState<ClarifyOutput | null>(null);
  const [pendingInput, setPendingInput] = useState("");
  const [pendingQuestions, setPendingQuestions] = useState<string[]>([]);
  const [answerDrafts, setAnswerDrafts] = useState<string[]>([]);
  const [rounds, setRounds] = useState<ClarifyRound[]>([]);
  const [allAnswers, setAllAnswers] = useState<ClarifyAnswer[]>([]);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [status, setStatus] = useState<"idle" | "asking" | "awaiting" | "clear" | "error">(
    "idle"
  );
  const [pipelineStatus, setPipelineStatus] = useState<
    "idle" | "running" | "done" | "error"
  >("idle");
  const [error, setError] = useState<string | null>(null);
  const [streamEvents, setStreamEvents] = useState<StreamEvent[]>([]);
  const [selectedEvent, setSelectedEvent] = useState<StreamEvent | null>(null);
  const [currentAgent, setCurrentAgent] = useState<string | null>(null);
  const streamAbortRef = useRef<AbortController | null>(null);

  const clarifierContext = useMemo(() => {
    if (!originalQuery || !clarifyOutput) {
      return null;
    }
    return {
      original_query: originalQuery,
      rounds,
      final: clarifyOutput
    };
  }, [originalQuery, clarifyOutput, rounds]);

  async function runClarifier(query: string) {
    setStatus("asking");
    setError(null);
    setCurrentQuery(query);
    try {
      const response = await fetch(`${API_BASE}/api/clarify`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query })
      });
      if (!response.ok) {
        const text = await response.text();
        throw new Error(text || `Clarifier failed: ${response.status}`);
      }

      const payload = (await response.json()) as ClarifyOutput;
      setClarifyOutput(payload);

      if (payload.clarifying_questions.length > 0 && !payload.is_clear_enough) {
        setPendingInput(query);
        setPendingOutput(payload);
        setPendingQuestions(payload.clarifying_questions);
        setAnswerDrafts(payload.clarifying_questions.map(() => ""));
        setStatus("awaiting");
        setMessages((prev) => [
          ...prev,
          {
            role: "assistant",
            text: `I need a bit more detail:\n${payload.clarifying_questions
              .map((question, index) => `${index + 1}. ${question}`)
              .join("\n")}`
          }
        ]);
      } else {
        const round: ClarifyRound = {
          input: query,
          output: payload,
          answers: [],
          skipped: false
        };
        const nextRounds = [...rounds, round];
        setRounds(nextRounds);
        setStatus("clear");
        setMessages((prev) => [
          ...prev,
          {
            role: "assistant",
            text: `Thanks. I have enough context.\nInterpreted query: ${payload.interpreted_query}\nRunning the research workflow now...`
          }
        ]);
        const nextContext = {
          original_query: originalQuery,
          rounds: nextRounds,
          final: payload
        };
        void runPipelineStream(nextContext);
      }
    } catch (err) {
      setStatus("error");
      setError(err instanceof Error ? err.message : "Clarifier request failed.");
    }
  }

  function startClarify() {
    const trimmed = queryInput.trim();
    if (!trimmed) {
      setError("Please enter a research query.");
      return;
    }
    setOriginalQuery(trimmed);
    setQueryInput("");
    setRounds([]);
    setAllAnswers([]);
    setMessages([{ role: "user", text: trimmed }]);
    setClarifyOutput(null);
    setPendingOutput(null);
    setPendingQuestions([]);
    setAnswerDrafts([]);
    setPipelineStatus("idle");
    runClarifier(trimmed);
  }

  function updateAnswer(index: number, value: string) {
    setAnswerDrafts((prev) => {
      const next = [...prev];
      next[index] = value;
      return next;
    });
  }

  function submitAnswers() {
    if (!pendingOutput) {
      return;
    }
    const answers: ClarifyAnswer[] = pendingQuestions.map((question, index) => ({
      question,
      answer: answerDrafts[index]?.trim() ?? ""
    }));

    const mergedAnswers = [...allAnswers, ...answers];
    setAllAnswers(mergedAnswers);
    const round: ClarifyRound = {
      input: pendingInput,
      output: pendingOutput,
      answers,
      skipped: false
    };
    const nextRounds = [...rounds, round];
    setRounds(nextRounds);
    setPendingOutput(null);
    setPendingQuestions([]);
    setAnswerDrafts([]);
    setMessages((prev) => [
      ...prev,
      {
        role: "user",
        text: answers.map((answer) => `${answer.question}\n${answer.answer}`).join("\n\n")
      }
    ]);

    const followup = buildFollowupQuery(originalQuery, mergedAnswers);
    runClarifier(followup);
  }

  function skipClarify() {
    if (!pendingOutput) {
      return;
    }
    const round: ClarifyRound = {
      input: pendingInput,
      output: pendingOutput,
      answers: [],
      skipped: true
    };
    const nextRounds = [...rounds, round];
    setRounds(nextRounds);
    setPendingOutput(null);
    setPendingQuestions([]);
    setAnswerDrafts([]);
    setStatus("clear");
    setMessages((prev) => [
      ...prev,
      { role: "assistant", text: "Proceeding with current context. Running the workflow now..." }
    ]);
    const nextContext = {
      original_query: originalQuery,
      rounds: nextRounds,
      final: pendingOutput
    };
    void runPipelineStream(nextContext);
  }

  function reset() {
    if (streamAbortRef.current) {
      streamAbortRef.current.abort();
    }
    setQueryInput("");
    setOriginalQuery("");
    setCurrentQuery("");
    setClarifyOutput(null);
    setPendingOutput(null);
    setPendingQuestions([]);
    setAnswerDrafts([]);
    setRounds([]);
    setAllAnswers([]);
    setMessages([]);
    setStatus("idle");
    setPipelineStatus("idle");
    setError(null);
    setStreamEvents([]);
    setSelectedEvent(null);
    setCurrentAgent(null);
  }

  async function runPipelineStream(context: unknown) {
    if (streamAbortRef.current) {
      streamAbortRef.current.abort();
    }

    const controller = new AbortController();
    streamAbortRef.current = controller;

    setPipelineStatus("running");
    setError(null);
    setStreamEvents([]);
    setSelectedEvent(null);
    setCurrentAgent(null);

    const streamEventsBuffer: StreamEvent[] = [];
    let firstTimestamp: string | null = null;
    let planOutput: unknown = null;
    let clarifierOutput: unknown = null;

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

    try {
      const response = await fetch(`${API_BASE}/api/run/stream`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          query: originalQuery,
          skip_clarify: true,
          clarified_context: JSON.stringify(context)
        }),
        signal: controller.signal
      });

      if (!response.ok) {
        const text = await response.text();
        throw new Error(text || `Pipeline error: ${response.status}`);
      }

      if (!response.body) {
        throw new Error("Pipeline stream response body is empty.");
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { value, done } = await reader.read();
        if (done) {
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
            if (!payloadText || payloadText === "[DONE]") {
              continue;
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
            setSelectedEvent((current) => current ?? normalized);

            const agent = normalized.agent ?? "";
            const stepName = agentToStep[agent];

            // Update current agent display
            if (normalized.type === "agent_start" && agent) {
              setCurrentAgent(agent);
            }
            if (normalized.type === "agent_complete" && agent) {
              setCurrentAgent(null);
            }

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
            }

            if (normalized.type === "plan_complete") {
              const payload = normalized.payload as { plan?: unknown } | null;
              planOutput = payload?.plan ?? null;
              setStepOutput("plan", planOutput);
              if (clarifierOutput) {
                setStepInput("plan", { clarifier: clarifierOutput });
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
        run_id: `run_pipeline_${Date.now()}`,
        created_at: firstTimestamp ?? new Date().toISOString(),
        query: originalQuery,
        meta: { mode: "server", api_base: API_BASE },
        steps
      };

      const parsed = parseRunBundle(runCandidate);
      localStorage.setItem("rn_last_run_bundle", JSON.stringify(parsed));
      localStorage.setItem("rn_last_stream_events", JSON.stringify(streamEventsBuffer));

      setPipelineStatus("done");
      setCurrentAgent(null);
    } catch (err) {
      if ((err as Error).name !== "AbortError") {
        setPipelineStatus("error");
        setError(err instanceof Error ? err.message : "Pipeline run failed.");
      }
    } finally {
      setCurrentAgent(null);
    }
  }

  return (
    <main className="clarify-shell">
      <header className="header">
        <div className="header-top">
          <div className="title-block">
            <h1 className="title">Research Navigator</h1>
            <p className="subtitle">Start with a clear research question.</p>
          </div>
          <span className="badge">Research Intake</span>
        </div>
        <div className="controls">
          <div className="control-group">
            <input
              className="text-input"
              type="text"
              placeholder="Enter a research query"
              value={queryInput}
              onChange={(event) => setQueryInput(event.target.value)}
            />
            <button className="button primary" type="button" onClick={startClarify}>
              Start research
            </button>
            <button className="button" type="button" onClick={reset}>
              Reset
            </button>
            <Link className="button" href="/demo">
              Demo UI
            </Link>
          </div>
          <div className="control-group">
            <span className="pill">API</span>
            <span className="pill">{API_BASE}</span>
            <span className="pill">status: {status}</span>
            <span className="pill">pipeline: {pipelineStatus}</span>
            {currentAgent ? <span className="pill">agent: {currentAgent}</span> : null}
            {streamEvents.length > 0 ? (
              <span className="pill">events: {streamEvents.length}</span>
            ) : null}
          </div>
        </div>
        {error ? <div className="panel-subtitle">Error: {error}</div> : null}
      </header>

      <section className="clarify-grid">
        <div className="panel">
          <div className="panel-header">
            <div>
              <div className="panel-title">Conversation</div>
              <div className="panel-subtitle">Answer a few questions to refine the scope.</div>
            </div>
          </div>
          <div className="chat-list">
            {messages.length === 0 ? (
              <div className="panel-subtitle">No conversation yet.</div>
            ) : (
              messages.map((message, index) => (
                <div key={`${message.role}-${index}`} className={`chat-bubble ${message.role}`}>
                  <div className="chat-role">{message.role}</div>
                  <pre className="chat-text">{message.text}</pre>
                </div>
              ))
            )}
          </div>
          {status === "awaiting" ? (
            <div className="clarify-answers">
              {pendingQuestions.map((question, index) => (
                <label key={question} className="answer-row">
                  <span>{question}</span>
                  <input
                    className="text-input"
                    type="text"
                    value={answerDrafts[index] ?? ""}
                    onChange={(event) => updateAnswer(index, event.target.value)}
                  />
                </label>
              ))}
              <div className="control-group">
                <button className="button primary" type="button" onClick={submitAnswers}>
                  Submit answers
                </button>
                <button className="button" type="button" onClick={skipClarify}>
                  Skip
                </button>
              </div>
            </div>
          ) : null}
          {pipelineStatus === "done" ? (
            <div className="control-group">
              <span className="panel-subtitle">Pipeline complete. View the full run:</span>
              <Link className="button" href="/demo">
                Open demo view
              </Link>
            </div>
          ) : null}
        </div>

        <div className="panel">
          <div className="panel-header">
            <div>
              <div className="panel-title">Conversation Payloads</div>
              <div className="panel-subtitle">Inputs / outputs (observability)</div>
            </div>
          </div>
          <div className="payload-stack">
            <section className="payload-section">
              <div className="payload-title">Current input</div>
              <div className="payload-sub">query</div>
              <pre className="json-block">{prettyJson(currentQuery || null)}</pre>
            </section>
            <section className="payload-section">
              <div className="payload-title">Latest response</div>
              <div className="payload-sub">assistant</div>
              <pre className="json-block">{prettyJson(clarifyOutput ?? null)}</pre>
            </section>
            <section className="payload-section">
              <div className="payload-title">Conversation context</div>
              <div className="payload-sub">rounds</div>
              <pre className="json-block">{prettyJson(clarifierContext ?? null)}</pre>
            </section>
          </div>
        </div>
      </section>

      {pipelineStatus !== "idle" && (
        <section className="clarify-grid" style={{ marginTop: "1rem" }}>
          <div className="panel">
            <div className="panel-header">
              <div>
                <div className="panel-title">Streaming Timeline</div>
                <div className="panel-subtitle">Real-time agent events</div>
              </div>
              {currentAgent ? (
                <span className="pill" style={{ backgroundColor: "#22c55e", color: "white" }}>
                  Running: {currentAgent}
                </span>
              ) : null}
            </div>
            <StreamPanel
              events={streamEvents}
              selectedEvent={selectedEvent}
              onSelectEvent={setSelectedEvent}
              maxEvents={streamEvents.length}
              cursor={streamEvents.length}
            />
          </div>

          <div className="panel">
            <div className="panel-header">
              <div>
                <div className="panel-title">Selected Event</div>
                <div className="panel-subtitle">Event payload details</div>
              </div>
            </div>
            <div className="payload-stack">
              {selectedEvent ? (
                <section className="payload-section">
                  <div className="payload-title">{selectedEvent.type}</div>
                  <div className="payload-sub">
                    agent: {selectedEvent.agent ?? "n/a"} | stage: {selectedEvent.stage ?? "n/a"}
                  </div>
                  <pre className="json-block">{prettyJson(selectedEvent.payload)}</pre>
                </section>
              ) : (
                <div className="panel-subtitle">Select an event to view details.</div>
              )}
            </div>
          </div>
        </section>
      )}
    </main>
  );
}
