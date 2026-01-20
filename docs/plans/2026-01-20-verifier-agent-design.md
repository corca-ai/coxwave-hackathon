# Verifier Agent v1.0 설계 문서

> 작성일: 2026-01-20

## 1. 개요

### 한 줄 정의
Extractor가 생성한 Claim/Evidence/Graph 결과를 **검증 가능한 품질 지표**로 평가하고, 통과/실패를 결정하며, 실패 시 Orchestrator가 실행할 **Self-Healing 액션**을 구조화해서 리턴한다.

### 핵심 역할
- **판정**: Quality Gate 통과 여부 결정
- **처방**: 실패 시 다음 액션 제안 (재검색/재추출/중단/승인)

### 핵심 결정 사항

| 항목 | 결정 |
|------|------|
| 역할 | Quality Gate + Self-Healing 처방 (실행은 Orchestrator) |
| 검증 방식 | Agent가 `rag_get_chunk` tool 호출로 evidence 검증 |
| GraphDB 의존 | v1: graph JSON만 사용 / v2: kg_query 추가 |
| Tools 수 | 최소화 (2개: rag_get_chunk, kg_query) |
| 프레임워크 | openai-agents-python (Agent가 직접 tool 호출) |
| 모델 | gpt-5-mini |

---

## 2. 성공 기준

### Primary KPI
- **Quality Gate 정확도**: 실제 품질 문제를 놓치지 않음 (false positive 최소화)
- **Self-Healing 처방 실행 가능성**: Orchestrator가 바로 실행 가능한 액션 제공

### Reliability KPI
- Tool 호출 실패해도 run이 중단되지 않고 partial result 반환
- 빈 배열/None 입력에도 정상 처리

### Performance KPI
- Extractor 결과 → Verifier 결과: 합리적 시간 내 완료

---

## 3. Scope

### In-scope (v1.0)
- Evidence substring 검증 (rag_get_chunk)
- Quality Gate 4가지 지표 평가
- Claim 상태 판정 (supported/weak/unsupported/conflicting)
- next_actions 생성 (Self-Healing 처방)
- Observability summary 출력

### Out-of-scope (v1.0)
- GraphDB 직접 쿼리 (Extractor가 준 graph JSON 사용)
- 복잡한 semantic conflict 감지 (규칙 기반만)
- 자동 수정/재실행 (Orchestrator가 담당)

---

## 4. 디렉토리 구조

```
src/
├── agents/
│   ├── __init__.py
│   └── verifier/
│       ├── __init__.py
│       ├── agent.py          # VerifierAgent 정의 (핵심)
│       ├── schemas.py        # Pydantic 모델
│       ├── tools/
│       │   ├── __init__.py
│       │   ├── rag.py        # rag_get_chunk (Agent가 호출)
│       │   └── kg.py         # kg_query (v1: mocked)
│       └── runner.py         # CLI 진입점
├── shared/
│   └── config.py
└── runner.py
```

> **설계 원칙**: Agent가 직접 tool을 호출하여 검증. Python 함수로 로직을 분리하지 않고, Agent의 instructions에 검증 절차 포함.

---

## 5. 입출력 계약

### Input (VerifierRequest)

```python
class VerifierRequest(BaseModel):
    goal: str                           # 유저 연구 목표
    namespace: str                      # RAG DB 네임스페이스
    extractor_result: ExtractorResult   # Extractor 출력
    constraints: VerifierConstraints    # 검증 기준

class ExtractorResult(BaseModel):
    paper_cards: list[PaperCard]
    claims: list[Claim]
    concepts: list[Concept]
    graph: GraphData | None = None
    kg_upsert_summary: dict | None = None

class VerifierConstraints(BaseModel):
    evidence_min: int = 10
    unsupported_ratio_max: float = 0.25
    min_concept_coverage: float = 0.7
    max_loops: int = 3
    loops_done: int = 0
```

### Output (VerifierResult)

```python
class VerifierResult(BaseModel):
    quality_gate: QualityGate
    metrics: QualityMetrics
    claim_judgements: list[ClaimJudgement]
    next_actions: list[NextAction]
    observability_summary: ObservabilitySummary
```

---

## 6. 스키마 정의

### Quality Gate

```python
class QualityGate(BaseModel):
    passed: bool
    reasons: list[str]

class QualityMetrics(BaseModel):
    evidence_coverage: float          # (verified claims) / (total claims)
    unsupported_ratio: float          # (unsupported claims) / (total claims)
    concept_coverage: float           # (covered concepts) / (required concepts)
    conflicts_count: int
    isolated_nodes_ratio: float       # graph 고립 노드 비율
    total_claims: int
    verified_claims: int
    weak_claims: int
    unsupported_claims: int
```

### Claim Judgement

```python
class ClaimJudgement(BaseModel):
    claim_id: str
    status: Literal["supported", "weak", "unsupported", "conflicting"]
    evidence_valid: bool | None       # None = 검증 안 함
    reason: str
```

### Next Actions (Self-Healing 처방)

```python
class NextAction(BaseModel):
    type: Literal[
        "search_expand",       # concept coverage 부족
        "search_more_papers",  # evidence 부족
        "reextract",           # 스키마/파싱 실패
        "human_review",        # conflict 많음
        "stop"                 # 루프 종료
    ]
    priority: int              # 1 = 최우선
    why: str
    suggested_queries: list[str] = []
    target_concepts: list[str] = []
```

### Observability

```python
class ObservabilitySummary(BaseModel):
    run_id: str
    timestamp: str
    decision_trace: list[str]         # ["schema_ok", "evidence_check_3/5", ...]
    tool_calls: list[ToolCallLog]
    duration_ms: int

class ToolCallLog(BaseModel):
    tool: str
    latency_ms: int
    success: bool
    error: str | None = None
```

---

## 7. Tools 정의 (LLM-facing)

### Tool 1: rag_get_chunk

```python
@function_tool
def rag_get_chunk(
    namespace: str,
    arxiv_id: str,
    chunk_id: str
) -> str | None:
    """
    특정 chunk의 원본 텍스트를 가져옵니다.
    Evidence quote가 실제로 존재하는지 검증하는 데 사용합니다.

    Args:
        namespace: RAG 저장소 네임스페이스
        arxiv_id: 논문 ID
        chunk_id: 청크 ID

    Returns:
        청크 텍스트 (없으면 None)
    """
```

### Tool 2: kg_query (v1: mocked)

```python
@function_tool
def kg_query(
    sparql: str
) -> list[dict]:
    """
    GraphDB에 SPARQL 쿼리를 실행합니다.
    v1.0: 모킹 - graph JSON에서 계산된 결과 반환.

    Args:
        sparql: SPARQL 쿼리 문자열

    Returns:
        쿼리 결과 rows
    """
    # v1.0: graph JSON fallback
    return []
```

---

## 8. Quality Gate 기준

### 1. Evidence Coverage
```
evidence_coverage = (# evidence가 검증된 claim) / (total_claims)
기준: >= 0.75 (abstract-only면 0.6으로 완화 가능)
```

### 2. Unsupported Ratio
```
unsupported_ratio = (# unsupported claims) / (total_claims)
기준: <= 0.25
```

### 3. Concept Coverage
```
concept_coverage = (# covered concepts) / (# required concepts from goal)
기준: >= 0.7
```

### 4. Conflict Handling
```
conflicts_count <= threshold (기본 3)
conflict 있으면 리포트에 "Conflicts/Open Questions" 섹션 포함
```

### Gate 통과 조건
```python
passed = (
    evidence_coverage >= 0.75 and
    unsupported_ratio <= 0.25 and
    concept_coverage >= 0.7 and
    conflicts_count <= 3
)
```

---

## 9. Agent 검증 워크플로우

> **핵심**: Agent가 직접 tool을 호출하며 검증 수행. Python 로직이 아닌 LLM의 reasoning으로 처리.

### Step A: 스키마 검증 (Agent reasoning)
- Agent가 입력된 claims를 분석
- `claim_id/doc_id/evidence(chunk_id, quote)` 누락 확인
- 누락된 claim은 `claim_judgements`에 `unsupported`로 기록

### Step B: Evidence 진위 검증 (Tool 호출)
- Agent가 각 claim에 대해 `rag_get_chunk(namespace, doc_id, chunk_id)` 호출
- 반환된 chunk_text에서 quote가 실제로 존재하는지 확인
- 비용 제한: 상위 N개 claim만 검증 (constraints.evidence_check_limit)

### Step C: Claim 상태 판정 (Agent reasoning)
- `evidence_valid=True` + 구체적 내용 → `supported`
- `evidence_valid=True` + 일반적 표현("We propose...") → `weak`
- `evidence_valid=False` → `unsupported` (환각 의심)
- tool 호출 실패 → `weak` (보수적 판정)

### Step D: Conflict 감지 (Agent reasoning)
- 같은 concept tag를 가진 claim 쌍 분석
- 대립 키워드 탐지 (can/cannot, effective/ineffective 등)
- 최대 10쌍 제한

### Step E: Metrics 계산 (Agent reasoning)
- `evidence_coverage`: supported / total
- `unsupported_ratio`: unsupported / total
- `concept_coverage`: goal의 concept 커버 비율
- `conflicts_count`: conflict 쌍 수
- graph JSON에서 `isolated_nodes_ratio` 계산

### Step F: Quality Gate 판정 + next_actions 생성
- Gate 기준 충족 여부 판단
- 실패 시 적절한 `next_actions` 생성
  - concept 부족 → `search_expand`
  - evidence 부족 → `search_more_papers`
  - conflict 많음 → `human_review`
  - loop 소진 → `stop`

---

## 10. Orchestrator 협업 구조

### next_actions 예시

```json
{
  "next_actions": [
    {
      "type": "search_expand",
      "priority": 1,
      "why": "concept_coverage 0.5 < 0.7, 'Evaluation', 'Long-context' 미커버",
      "suggested_queries": [
        "graph rag evaluation metrics",
        "retrieval augmented generation long context"
      ],
      "target_concepts": ["Evaluation", "Long-context"]
    },
    {
      "type": "human_review",
      "priority": 2,
      "why": "상충 claim 3개 존재, 관점 우선순위 승인 필요",
      "suggested_queries": [],
      "target_concepts": []
    }
  ]
}
```

### Orchestrator 루프

```
Verifier.pass == False
  → Orchestrator reads next_actions
  → if "search_expand": SearchAgent 재호출
  → if "reextract": Extractor 재호출
  → if "human_review": 사용자 승인 대기
  → Verifier 재호출
  → repeat until pass or max_loops
```

---

## 11. Tool 실패 대비

### rag_get_chunk 실패 시
```python
evidence_valid = None  # "unknown" (unsupported가 아님)
# weak으로 분류, 검증 불가 사유 기록
```

### kg_query 실패 시
```python
# graph JSON fallback 계산
# GraphDB 없이도 isolated_ratio 등 계산 가능
```

### 원칙
- 툴 실패해도 Verifier가 죽지 않음
- partial result라도 반환
- observability_summary에 실패 기록

---

## 12. MVP 운영 팁 (abstract-only)

### 품질 기준 완화
- evidence_coverage 기준: 0.75 → 0.6
- `weak` 상태 적극 사용

### 보고 방식
- "weak 포함 커버리지"와 "supported-only 커버리지" 둘 다 표시
- 중요한 건 "근거를 조작하지 않는다"는 신뢰성

### Loop 종료 조건
- loops_done >= max_loops → 강제 종료 (partial pass 허용)
- 2회 연속 metrics 개선 없음 → 조기 종료

---

## 13. 구현 우선순위

1. **스키마 체크 + metrics 계산** (필수)
2. **rag_get_chunk로 evidence substring 검증** (상위 claim만)
3. **quality_gate(pass/fail) + next_actions 생성** (필수)
4. (옵션) conflict 간단 감지
5. (옵션) kg_query로 graph 지표 교차검증

---

## 14. 해커톤 채점표 매핑

| 채점 항목 | Verifier 기여 |
|-----------|---------------|
| 기술 구현 (40%) | Self-Healing 처방, Tool 견고성, 에러 복구 |
| 완성도 (20%) | Edge case 대응 (빈 입력, tool 실패) |
| 가산점: Safety | 환각 evidence 감지 (rag_get_chunk 검증) |
| 가산점: Observability | decision_trace, tool_calls 로깅 |
| 가산점: Human-in-the-loop | human_review 액션으로 승인 플로우 |
