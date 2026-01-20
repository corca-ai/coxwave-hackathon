import type { StreamEvent } from "../lib/types";

interface StreamPanelProps {
  events: StreamEvent[];
  selectedEvent: StreamEvent | null;
  onSelectEvent: (event: StreamEvent) => void;
  maxEvents: number;
  cursor: number;
}

function formatTime(timestamp: string): string {
  const date = new Date(timestamp);
  if (Number.isNaN(date.getTime())) {
    return timestamp;
  }
  return date.toLocaleTimeString();
}

function payloadPreview(payload: unknown): string {
  if (payload === null || payload === undefined) {
    return "empty";
  }
  if (typeof payload === "string") {
    return payload.slice(0, 80);
  }
  try {
    const json = JSON.stringify(payload);
    return json.length > 80 ? `${json.slice(0, 80)}...` : json;
  } catch (error) {
    return "unserializable";
  }
}

export default function StreamPanel({
  events,
  selectedEvent,
  onSelectEvent,
  maxEvents,
  cursor
}: StreamPanelProps) {
  if (maxEvents === 0) {
    return <div className="panel-subtitle">No stream events loaded.</div>;
  }

  return (
    <div>
      <div className="panel-subtitle">
        Showing {cursor}/{maxEvents} events
      </div>
      <div className="stream-list">
        {events.map((event) => {
          const isActive = selectedEvent?.id === event.id;
          return (
            <button
              key={event.id}
              type="button"
              className={`stream-item ${isActive ? "active" : ""}`}
              onClick={() => onSelectEvent(event)}
            >
              <div className="stream-meta">
                <span className="stream-type">{event.type}</span>
                <span>{formatTime(event.timestamp)}</span>
              </div>
              <div className="panel-subtitle">
                {event.agent ? `agent: ${event.agent}` : "agent: n/a"}
              </div>
              <div className="panel-subtitle">{payloadPreview(event.payload)}</div>
            </button>
          );
        })}
      </div>
    </div>
  );
}
