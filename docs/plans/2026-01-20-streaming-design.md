# Streaming 구현 설계

## 개요

모든 에이전트에 streaming 기능을 추가하여 프론트엔드에서 실시간 진행 상황을 표시할 수 있도록 한다.

## 요구사항

- **수준**: 토큰 레벨 + 이벤트 레벨 둘 다
- **범위**: 모든 에이전트 (Clarifier, Searcher, Extractor, Verifier, Visualizer, Orchestrator)
- **스키마**: 기존 `docs/schemas/stream-events.schema.json` 사용

## StreamEvent 스키마

```json
{
  "id": "uuid",
  "timestamp": "ISO 8601",
  "type": "string",
  "agent": "string (optional)",
  "stage": "string (optional)",
  "sequence": "integer",
  "payload": "any"
}
```

## 이벤트 타입

| type | 설명 | payload |
|------|------|---------|
| `agent_start` | 에이전트 시작 | `{input: ...}` |
| `agent_complete` | 에이전트 완료 | `{output: ...}` |
| `text_delta` | 토큰 단위 텍스트 | `{delta: "..."}` |
| `tool_call` | 툴 호출 시작 | `{name: "...", args: ...}` |
| `tool_output` | 툴 결과 | `{name: "...", output: ...}` |
| `loop_start` | 오케스트레이터 루프 시작 | `{loop: 1}` |
| `loop_complete` | 오케스트레이터 루프 완료 | `{loop: 1}` |

## 구현 방식

### 1. stream_events.py (새 파일)

```python
from dataclasses import dataclass
from datetime import datetime
from typing import Any
import uuid

@dataclass
class StreamEvent:
    type: str
    payload: Any
    agent: str | None = None
    stage: str | None = None
    sequence: int = 0

    def to_dict(self) -> dict:
        return {
            "id": str(uuid.uuid4()),
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "type": self.type,
            "agent": self.agent,
            "stage": self.stage,
            "sequence": self.sequence,
            "payload": self.payload,
        }
```

### 2. 에이전트 변경

각 에이전트에 `run_stream()` async generator 메서드 추가:

```python
class OpenAIClarifier:
    def run(self, query: str) -> ClarifierOutput:
        # 기존 동기 방식 유지
        ...

    async def run_stream(self, query: str) -> AsyncGenerator[StreamEvent, None]:
        yield StreamEvent("agent_start", {"query": query}, agent="clarifier")

        result = Runner.run_streamed(self._agent, query)
        async for event in result.stream_events():
            if event.type == "raw_response_event":
                if isinstance(event.data, ResponseTextDeltaEvent):
                    yield StreamEvent("text_delta", {"delta": event.data.delta}, agent="clarifier")
            elif event.type == "run_item_stream_event":
                if event.item.type == "tool_call_item":
                    yield StreamEvent("tool_call", {...}, agent="clarifier")
                elif event.item.type == "message_output_item":
                    yield StreamEvent("message_complete", {...}, agent="clarifier")

        yield StreamEvent("agent_complete", {"output": result.final_output}, agent="clarifier")
```

### 3. Orchestrator 변경

하위 에이전트의 이벤트를 전파:

```python
async def run_stream(self, context: str, config: OrchestratorConfig):
    yield StreamEvent("agent_start", {"config": asdict(config)}, agent="orchestrator")

    for loop_idx in range(config.max_loops):
        yield StreamEvent("loop_start", {"loop": loop_idx + 1}, agent="orchestrator")

        # Search - 하위 이벤트 전파
        search_result = None
        async for event in self.searcher.run_stream(search_context):
            yield event
            if event.type == "agent_complete":
                search_result = event.payload["output"]

        # Extract, Verify 동일 패턴
        ...

        yield StreamEvent("loop_complete", {"loop": loop_idx + 1}, agent="orchestrator")

    yield StreamEvent("agent_complete", {"output": final_output}, agent="orchestrator")
```

## 파일 변경 목록

1. `stream_events.py` - 새 파일 (StreamEvent 클래스)
2. `agents_impl.py` - 각 에이전트에 `run_stream()` 추가
3. `main.py` - MockOrchestrator에 `run_stream()` 추가, Protocol 업데이트
