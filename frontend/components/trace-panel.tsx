import type { RunStep } from "../lib/types";

interface TracePanelProps {
  steps: RunStep[];
  selectedStep: RunStep | null;
  onSelectStep: (step: RunStep) => void;
}

function payloadSummary(payload: unknown): string {
  if (payload === null || payload === undefined) {
    return "empty";
  }
  if (Array.isArray(payload)) {
    return `${payload.length} items`;
  }
  if (typeof payload === "object") {
    return `${Object.keys(payload as Record<string, unknown>).length} keys`;
  }
  return typeof payload;
}

export default function TracePanel({ steps, selectedStep, onSelectStep }: TracePanelProps) {
  if (steps.length === 0) {
    return <div className="panel-subtitle">No steps loaded.</div>;
  }

  return (
    <div className="trace-list">
      {steps.map((step) => {
        const isActive = selectedStep?.name === step.name;
        return (
          <button
            key={step.name}
            type="button"
            className={`trace-item ${isActive ? "active" : ""}`}
            onClick={() => onSelectStep(step)}
          >
            <div className="trace-item-title">{step.name}</div>
            <div className="trace-item-meta">
              input {payloadSummary(step.input)} | output {payloadSummary(step.output)}
            </div>
            {step.status ? (
              <div className="trace-item-meta">status: {step.status}</div>
            ) : null}
          </button>
        );
      })}
    </div>
  );
}
