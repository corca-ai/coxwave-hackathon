# 구현 도구 및 기술 스택

이 문서는 연구자를 위한 자율형 리서치 시스템 구현에 활용할 수 있는 도구와 기술 스택을 정리한다.

## 목차

1. [LLM 파이프라인 최적화: DSPy](#llm-파이프라인-최적화-dspy)
2. [에이전트 프레임워크: OpenAI Agent SDK](#에이전트-프레임워크-openai-agent-sdk)
3. [지식 그래프 저장소](#지식-그래프-저장소)
4. [기술 스택 선택 근거](#기술-스택-선택-근거)

---

## LLM 파이프라인 최적화: DSPy

### 개요

[DSPy](https://dspy.ai/)는 "프롬프팅이 아닌 프로그래밍"을 지향하는 선언적 AI 프레임워크다. 프롬프트 문자열 대신 구조화된 코드로 LLM 동작을 정의하고, 평가 지표 기반으로 자동 최적화한다.

### 핵심 개념

#### Signature (시그니처)
입출력을 타입과 설명으로 선언:

```python
class ExtractClaim(dspy.Signature):
    """논문 텍스트에서 핵심 주장을 추출한다."""

    paper_text: str = dspy.InputField(desc="논문 본문 또는 초록")
    claims: list[str] = dspy.OutputField(desc="추출된 주장들의 리스트")
```

#### Module (모듈)
시그니처를 실행하는 단위:

```python
class ClaimExtractor(dspy.Module):
    def __init__(self):
        self.extract = dspy.ChainOfThought(ExtractClaim)

    def forward(self, paper_text):
        return self.extract(paper_text=paper_text)
```

#### Metric (평가 지표)
최적화의 기준이 되는 함수:

```python
def claim_quality_metric(example, prediction):
    """추출된 claim의 품질을 평가"""
    # 구체성, 검증가능성, 중복 여부 등 평가
    score = evaluate_specificity(prediction.claims)
    score += evaluate_verifiability(prediction.claims)
    return score / 2
```

#### Optimizer (최적화기)
metric을 최대화하도록 프롬프트/파이프라인 자동 조정:

```python
optimizer = dspy.MIPROv2(metric=claim_quality_metric)
optimized_extractor = optimizer.compile(
    ClaimExtractor(),
    trainset=examples,  # 수십~수백 개의 예시
)
```

### 이 프로젝트에서의 활용 (현재/예정)

현재 구현 상태 요약:
- DSPy는 **Clarifier/Visualizer** 최적화에만 사용 (옵션, `dspy_integration/`).
- Extract/Verify는 **Agent SDK + 스키마 출력** 기반이며 DSPy 모듈은 아직 적용하지 않음.
- Orchestrator는 **`main.py`의 상태 기반 루프(MockOrchestrator)** 로 동작 (Agent SDK handoff 미사용).
- GraphDB는 Docker 설정이 준비되어 있으며, `kg_query`는 v1에서 mock 처리.

아래 예시는 향후 확장/적용 가능한 패턴을 설명한다.

#### 1. 정보 추출 파이프라인

논문에서 구조화된 데이터를 추출하는 모듈들:

```python
class ExtractPaperMetadata(dspy.Signature):
    """논문에서 메타데이터를 추출한다."""
    paper_text: str = dspy.InputField()
    title: str = dspy.OutputField()
    authors: list[str] = dspy.OutputField()
    year: int = dspy.OutputField()
    concepts: list[str] = dspy.OutputField(desc="논문이 다루는 핵심 개념들")

class ExtractClaimRelations(dspy.Signature):
    """두 논문의 claim 간 관계를 판단한다."""
    claim_a: str = dspy.InputField()
    claim_b: str = dspy.InputField()
    relation: str = dspy.OutputField(desc="extends | supports | refutes | none")
    reasoning: str = dspy.OutputField(desc="판단 근거")
```

#### 2. 품질 평가 자동화

kg2 회고에서 강조된 "자동화된 평가 기준":

```python
def graph_enrichment_metric(example, prediction):
    """추출된 데이터가 그래프 연결성을 얼마나 개선하는지"""
    # 기존 concept과의 연결 수
    concept_links = count_existing_concept_matches(prediction.concepts)
    # 기존 claim과의 관계 수
    claim_links = count_claim_relations(prediction.claims)
    # 고립 노드 생성 페널티
    isolation_penalty = count_isolated_entities(prediction)

    return (concept_links + claim_links - isolation_penalty) / 3
```

#### 3. Self-Healing 파이프라인

Enrichment와 Merging 자동화:

```python
class EnrichmentAgent(dspy.Module):
    def __init__(self):
        self.find_gaps = dspy.ChainOfThought(FindEnrichmentOpportunity)
        self.search = dspy.ChainOfThought(SearchForData)
        self.extract = dspy.ChainOfThought(ExtractAndValidate)

    def forward(self, graph_state):
        gaps = self.find_gaps(graph_state=graph_state)
        for gap in gaps.opportunities:
            data = self.search(gap=gap)
            enrichment = self.extract(data=data)
            if enrichment.is_valid:
                yield enrichment

class MergeCandidate(dspy.Signature):
    """두 엔티티가 동일한지 판단한다."""
    entity_a: dict = dspy.InputField()
    entity_b: dict = dspy.InputField()
    is_same: bool = dspy.OutputField()
    confidence: float = dspy.OutputField(desc="0.0~1.0")
    evidence: str = dspy.OutputField(desc="판단 근거")
```

#### 4. 데모 시나리오 에이전트 (예시)

멀티 에이전트 워크플로우를 DSPy 모듈로 구성:

```python
# Clarifier Agent
class ClarifyQuery(dspy.Signature):
    user_query: str = dspy.InputField()
    clarifying_questions: list[str] = dspy.OutputField()
    is_clear_enough: bool = dspy.OutputField()

# Verifier Agent
class VerifyClaim(dspy.Signature):
    claim: str = dspy.InputField()
    evidence: list[str] = dspy.InputField()
    is_supported: bool = dspy.OutputField()
    confidence: float = dspy.OutputField()
    gaps: list[str] = dspy.OutputField(desc="추가로 필요한 증거")

# Writer Agent
class SynthesizeReport(dspy.Signature):
    query: str = dspy.InputField()
    verified_claims: list[dict] = dspy.InputField()
    report: str = dspy.OutputField()
    citations: list[str] = dspy.OutputField()
```

### DSPy vs 프롬프트 엔지니어링

| 관점 | 프롬프트 엔지니어링 | DSPy |
|-----|-------------------|------|
| 반복 개선 | 수동으로 프롬프트 수정 | metric 기반 자동 최적화 |
| 품질 보장 | 휴리스틱, 수동 검토 | 정량적 평가 함수 |
| 구조화 출력 | JSON 파싱 + 예외처리 | Typed Signature로 강제 |
| 재현성 | 프롬프트 버전 관리 | 코드로 버전 관리 |
| 디버깅 | 어려움 | 모듈 단위 테스트 가능 |

### 주의사항

- **학습 곡선**: 새로운 추상화 레이어 학습 필요
- **예시 데이터 필요**: 최적화를 위해 수십~수백 개의 labeled 예시 필요
- **OpenAI Agent SDK와 통합**: 별도 연동 작업 필요 (DSPy는 LLM 호출 래퍼, Agent SDK는 워크플로우 관리)

---

## 에이전트 프레임워크: OpenAI Agent SDK

### 개요

[OpenAI Agent SDK (Python)](https://github.com/openai/openai-agents-python/)는 멀티 에이전트 워크플로우를 구축하기 위한 공식 SDK다.

### 데모 시나리오와의 매핑

```
데모 시나리오 에이전트    →    구현 (현재 코드 기준)
─────────────────────────────────────
Clarifier Agent         →    Agent with clarification tools
Orchestrator            →    `main.py` state-based loop (MockOrchestrator)
├─ Planner Agent        →    Agent with planning signature
Search/Select Agent     →    Agent with search tools + RAG ingest
Extractor Agent         →    Agent with schema-driven extraction
Verifier Agent          →    Agent with rag_get_chunk + kg_query (v1 mock)
Writer Agent            →    Agent with synthesis signature
Visualizer Agent        →    Agent with UI component spec output
```

### DSPy와의 통합 패턴 (선택적)

```python
from agents import Agent, Tool
import dspy

# DSPy 모듈을 Tool로 래핑
class DSPyTool(Tool):
    def __init__(self, dspy_module, name, description):
        self.module = dspy_module
        super().__init__(name=name, description=description)

    def run(self, **kwargs):
        return self.module(**kwargs)

# 에이전트에 DSPy 도구 추가
extractor_agent = Agent(
    name="Extractor",
    tools=[
        DSPyTool(optimized_claim_extractor, "extract_claims", "논문에서 claim 추출"),
        DSPyTool(optimized_concept_extractor, "extract_concepts", "논문에서 concept 추출"),
    ]
)
```

---

## 지식 그래프 저장소

### GraphDB (kg2에서 사용)

- **장점**: OWL 추론 지원, SHACL 검증, 안정적
- **단점**: 서버 위치에 따른 latency (회고에서 언급)

### 대안: Neo4j

> "owl 같은 무거운거 말고 그냥 neo4j 로 간단하게 만들어도 좋을 것 같고요" - 피드백

- **장점**: Cypher 쿼리 직관적, 성능 좋음, 클라우드 옵션 다양
- **단점**: OWL 추론 없음 (LLM으로 대체 가능)

### 선택 기준

| 요구사항 | GraphDB | Neo4j |
|---------|---------|-------|
| OWL 추론 필수 | O | X |
| SHACL 검증 | O | 별도 구현 |
| 빠른 프로토타이핑 | △ | O |
| Latency 민감 | 서버 위치 주의 | Aura 등 글로벌 |

---

## 기술 스택 선택 근거

### 해커톤 맥락

- **시간 제약**: 7시간
- **필수 조건**: OpenAI API/SDK 사용, 멀티에이전트 협업 구조
- **평가 기준**: 아이디어 30%, 기술 구현 40%, 완성도 20%, 문서화 10%

### 권장 스택

```
┌─────────────────────────────────────────────────┐
│                   Frontend                       │
│            (선택: Next.js / SvelteKit)           │
├─────────────────────────────────────────────────┤
│              OpenAI Agent SDK                    │
│     (Orchestrator, Handoffs, Tool calling)       │
├─────────────────────────────────────────────────┤
│                    DSPy                          │
│   (정보 추출, 품질 평가, 파이프라인 최적화)        │
├─────────────────────────────────────────────────┤
│              Knowledge Graph                     │
│        (GraphDB or Neo4j + SPARQL/Cypher)        │
└─────────────────────────────────────────────────┘
```

### 우선순위 (현재 기준)

1. **먼저**: 지식 그래프 스키마 확정 + GraphDB 실연동
2. **다음**: DSPy로 추출/검증 파이프라인 확장 + 평가 지표 고도화
3. **완료**: Agent SDK 워크플로우 통합 + UI

---

## 참고 자료

- [DSPy 공식 문서](https://dspy.ai/)
- [DSPy GitHub](https://github.com/stanfordnlp/dspy)
- [OpenAI Agent SDK](https://github.com/openai/openai-agents-python/)
- [concepts.md](./concepts.md) - 지식 그래프/온톨로지 개념
