"""Streaming event types for real-time progress updates."""

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any
import uuid


@dataclass
class StreamEvent:
    """A streaming event conforming to docs/schemas/stream-events.schema.json."""

    type: str
    payload: Any
    agent: str | None = None
    stage: str | None = None
    sequence: int = 0

    def to_dict(self) -> dict:
        """Convert to JSON-serializable dict matching the schema."""
        return {
            "id": str(uuid.uuid4()),
            "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "type": self.type,
            "agent": self.agent,
            "stage": self.stage,
            "sequence": self.sequence,
            "payload": self.payload,
        }


class StreamEventTypes:
    """Constants for event types."""

    AGENT_START = "agent_start"
    AGENT_COMPLETE = "agent_complete"
    TEXT_DELTA = "text_delta"
    TOOL_CALL = "tool_call"
    TOOL_OUTPUT = "tool_output"
    MESSAGE_COMPLETE = "message_complete"
    LOOP_START = "loop_start"
    LOOP_COMPLETE = "loop_complete"
    ERROR = "error"
