import type { GraphNodeData } from "../lib/graph";
import type { RunStep, StreamEvent } from "../lib/types";

interface PayloadPanelProps {
  selectedStep: RunStep | null;
  selectedNode: GraphNodeData | null;
  selectedEvent: StreamEvent | null;
  prettyJson: (value: unknown) => string;
}

export default function PayloadPanel({
  selectedStep,
  selectedNode,
  selectedEvent,
  prettyJson
}: PayloadPanelProps) {
  return (
    <div className="payload-stack">
      <section className="payload-section">
        <div className="payload-title">Step Input</div>
        <div className="payload-sub">
          {selectedStep ? selectedStep.name.toUpperCase() : "No step selected"}
        </div>
        <pre className="json-block">{prettyJson(selectedStep?.input ?? null)}</pre>
      </section>

      <section className="payload-section">
        <div className="payload-title">Step Output</div>
        <div className="payload-sub">
          {selectedStep ? selectedStep.name.toUpperCase() : "No step selected"}
        </div>
        <pre className="json-block">{prettyJson(selectedStep?.output ?? null)}</pre>
      </section>

      <section className="payload-section">
        <div className="payload-title">Graph Node Payload</div>
        <div className="payload-sub">
          {selectedNode ? `${selectedNode.kind} / ${selectedNode.label}` : "No node selected"}
        </div>
        <pre className="json-block">{prettyJson(selectedNode?.payload ?? null)}</pre>
      </section>

      <section className="payload-section">
        <div className="payload-title">Stream Event Payload</div>
        <div className="payload-sub">
          {selectedEvent ? selectedEvent.type : "No event selected"}
        </div>
        <pre className="json-block">{prettyJson(selectedEvent?.payload ?? null)}</pre>
      </section>
    </div>
  );
}
