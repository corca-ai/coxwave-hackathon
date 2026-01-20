# Orchestrator Agent 설계

## 개요

Research Navigator의 핵심 연구 루프(Plan → Search → Extract → Verify → Write)를 관리하는 Orchestrator 에이전트 추가.

## 아키텍처

```
User Query
    ↓
┌───────────┐
│ Clarifier │  ← 사용자 상호작용 (별도, 기존 유지)
└─────┬─────┘
      ↓
┌─────────────────────────────────────┐
│          Orchestrator               │  ← 새로 추가
│  ┌────────────────────────────────┐ │
│  │ Plan → Search → Extract →      │ │
│  │         Verify → Write         │ │
│  │           ↑         │          │ │
│  │           └─ loop ──┘          │ │
│  └────────────────────────────────┘ │
└─────────────────┬───────────────────┘
                  ↓
           ┌────────────┐
           │ Visualizer │  ← 후처리 (별도, 기존 유지)
           └────────────┘
```

## Orchestrator 책임

1. **Plan 수립 및 승인 관리**
   - Planner 호출 → 사용자 승인 요청
   - 피드백 시 재계획

2. **Search ↔ Verify 루프**
   - Verify에서 `is_enough=False` 시 `next_search_queries`로 재검색
   - 품질 게이트 통과까지 반복

3. **반복 예산 관리**
   - `max_loops` 설정 (기본값: 3)
   - 예산 소진 시 현재 결과로 Write 진행

4. **최종 Write 호출**
   - 검증된 claims로 리포트 생성

## 데이터 흐름

```
ClarifyOutput
    ↓
Orchestrator.run(clarify_context)
    ├── Planner.run() → PlanOutput
    │       ↓ (승인)
    ├── loop (max_loops):
    │   ├── Searcher.run() → SearchOutput
    │   ├── Extractor.run() → ExtractOutput
    │   └── Verifier.run() → VerifyOutput
    │           ↓
    │       is_enough? ──No──→ next_search_queries → loop
    │           ↓ Yes
    └── Writer.run() → ReportOutput
```

## 인터페이스

```python
@dataclass
class OrchestratorConfig:
    max_loops: int = 3
    require_plan_approval: bool = True

class Orchestrator(Protocol):
    def run(self, clarify_context: str, config: OrchestratorConfig) -> ReportOutput:
        ...
```

## 구현 방식

OpenAI Agent SDK의 handoff 패턴 활용:
- Orchestrator를 메인 Agent로
- 각 단계별 에이전트를 tool 또는 handoff로 연결
- 루프 로직은 Orchestrator의 instructions에서 관리

## 변경 범위

| 파일 | 변경 |
|------|------|
| `main.py` | `run_demo()` 단순화, Orchestrator 호출로 대체 |
| `agents_impl.py` | `OpenAIOrchestrator` 클래스 추가 |
| `src/agent/orchestrator/` | 새 디렉토리 (선택) |

## 비목표 (Out of Scope)

- Clarifier 로직 변경
- Visualizer 로직 변경
- 새로운 에이전트 타입 추가
