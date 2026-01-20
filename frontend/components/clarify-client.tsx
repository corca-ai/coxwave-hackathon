"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import { prettyJson } from "../lib/json";

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
  const [error, setError] = useState<string | null>(null);

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
        setRounds((prev) => [...prev, round]);
        setStatus("clear");
        setMessages((prev) => [
          ...prev,
          {
            role: "assistant",
            text: `Thanks. I have enough context.\nInterpreted query: ${payload.interpreted_query}`
          }
        ]);
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

    setAllAnswers((prev) => [...prev, ...answers]);
    setRounds((prev) => [
      ...prev,
      {
        input: pendingInput,
        output: pendingOutput,
        answers,
        skipped: false
      }
    ]);
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

    const followup = buildFollowupQuery(originalQuery, [...allAnswers, ...answers]);
    runClarifier(followup);
  }

  function skipClarify() {
    if (!pendingOutput) {
      return;
    }
    setRounds((prev) => [
      ...prev,
      {
        input: pendingInput,
        output: pendingOutput,
        answers: [],
        skipped: true
      }
    ]);
    setPendingOutput(null);
    setPendingQuestions([]);
    setAnswerDrafts([]);
    setStatus("clear");
    setMessages((prev) => [
      ...prev,
      { role: "assistant", text: "Clarification skipped. Proceeding with current context." }
    ]);
  }

  function reset() {
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
    setError(null);
  }

  return (
    <main className="clarify-shell">
      <header className="header">
        <div className="header-top">
          <div className="title-block">
            <h1 className="title">Research Navigator</h1>
            <p className="subtitle">Clarify the research question before running the pipeline.</p>
          </div>
          <span className="badge">Clarifier</span>
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
              Start clarifier
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
          </div>
        </div>
        {error ? <div className="panel-subtitle">Error: {error}</div> : null}
      </header>

      <section className="clarify-grid">
        <div className="panel">
          <div className="panel-header">
            <div>
              <div className="panel-title">Clarify Chat</div>
              <div className="panel-subtitle">Conversation flow (CLI-style)</div>
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
        </div>

        <div className="panel">
          <div className="panel-header">
            <div>
              <div className="panel-title">Clarifier Payloads</div>
              <div className="panel-subtitle">Input / output payloads (observability)</div>
            </div>
          </div>
          <div className="payload-stack">
            <section className="payload-section">
              <div className="payload-title">Current input</div>
              <div className="payload-sub">query</div>
              <pre className="json-block">{prettyJson(currentQuery || null)}</pre>
            </section>
            <section className="payload-section">
              <div className="payload-title">Latest output</div>
              <div className="payload-sub">clarify</div>
              <pre className="json-block">{prettyJson(clarifyOutput ?? null)}</pre>
            </section>
            <section className="payload-section">
              <div className="payload-title">Clarifier context</div>
              <div className="payload-sub">rounds</div>
              <pre className="json-block">{prettyJson(clarifierContext ?? null)}</pre>
            </section>
          </div>
        </div>
      </section>
    </main>
  );
}
