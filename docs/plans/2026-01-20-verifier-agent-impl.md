# Verifier Agent Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Extractor 결과를 검증하고 Self-Healing 처방을 내리는 Quality Gate Agent 구현

**Architecture:** openai-agents-python 기반 Agent가 직접 tool 호출하여 evidence 검증

**Tech Stack:** Python 3.11+, openai-agents, pydantic

**Design Doc:** `docs/plans/2026-01-20-verifier-agent-design.md`

---

## Task 1: 프로젝트 구조 생성

**Files:**
- Create: `src/agents/verifier/__init__.py`
- Create: `src/agents/verifier/tools/__init__.py`

**Step 1: 디렉토리 구조 생성**

```bash
mkdir -p src/agents/verifier/tools
touch src/agents/verifier/__init__.py
touch src/agents/verifier/tools/__init__.py
```

**Step 2: 커밋**

```bash
git add src/agents/verifier/
git commit -m "chore: initialize verifier-agent directory structure"
```

---

## Task 2: Pydantic 스키마 정의

**Files:**
- Create: `src/agents/verifier/schemas.py`
- Create: `tests/verifier/test_schemas.py`

**Step 1: 테스트 먼저 작성**

```python
# tests/verifier/test_schemas.py
import pytest
from agents.verifier.schemas import (
    VerifierRequest,
    VerifierResult,
    VerifierConstraints,
    QualityGate,
    QualityMetrics,
    ClaimJudgement,
    NextAction,
    ExtractorResult,
    Claim,
    Evidence,
)


def test_verifier_constraints_defaults():
    constraints = VerifierConstraints()
    assert constraints.evidence_min == 10
    assert constraints.unsupported_ratio_max == 0.25
    assert constraints.min_concept_coverage == 0.7
    assert constraints.max_loops == 3


def test_claim_judgement_status():
    judgement = ClaimJudgement(
        claim_id="claim_1",
        status="supported",
        evidence_valid=True,
        reason="Quote found in chunk"
    )
    assert judgement.status == "supported"


def test_next_action_types():
    action = NextAction(
        type="search_expand",
        priority=1,
        why="concept_coverage < 0.7",
        suggested_queries=["graph rag evaluation"],
        target_concepts=["Evaluation"]
    )
    assert action.type == "search_expand"
    assert len(action.suggested_queries) == 1


def test_quality_gate_pass():
    gate = QualityGate(passed=True, reasons=[])
    assert gate.passed is True


def test_verifier_result_structure():
    result = VerifierResult(
        quality_gate=QualityGate(passed=True, reasons=[]),
        metrics=QualityMetrics(),
        claim_judgements=[],
        next_actions=[]
    )
    assert result.quality_gate.passed is True
```

**Step 2: 스키마 구현**

```python
# src/agents/verifier/schemas.py
from pydantic import BaseModel, Field
from typing import Literal
from datetime import datetime


# --- Input Schemas ---

class Evidence(BaseModel):
    chunk_id: str
    quote: str
    page: int | None = None


class Claim(BaseModel):
    claim_id: str
    doc_id: str  # arxiv_id
    text: str
    evidence: Evidence | None = None
    concept_tags: list[str] = []
    confidence: float = 0.0


class Concept(BaseModel):
    concept_id: str
    name: str
    description: str = ""


class PaperCard(BaseModel):
    arxiv_id: str
    title: str
    year: int
    authors: list[str]
    abstract: str


class GraphNode(BaseModel):
    id: str
    type: Literal["paper", "claim", "concept", "author"]
    label: str


class GraphEdge(BaseModel):
    source: str
    target: str
    relation: str


class GraphData(BaseModel):
    nodes: list[GraphNode] = []
    edges: list[GraphEdge] = []


class ExtractorResult(BaseModel):
    paper_cards: list[PaperCard] = []
    claims: list[Claim] = []
    concepts: list[Concept] = []
    graph: GraphData | None = None


class VerifierConstraints(BaseModel):
    evidence_min: int = 10
    unsupported_ratio_max: float = 0.25
    min_concept_coverage: float = 0.7
    max_loops: int = 3
    loops_done: int = 0
    evidence_check_limit: int = 20


class VerifierRequest(BaseModel):
    goal: str
    namespace: str = "default"
    extractor_result: ExtractorResult
    constraints: VerifierConstraints = Field(default_factory=VerifierConstraints)


# --- Output Schemas ---

class QualityGate(BaseModel):
    passed: bool
    reasons: list[str] = []


class QualityMetrics(BaseModel):
    evidence_coverage: float = 0.0
    unsupported_ratio: float = 0.0
    concept_coverage: float = 0.0
    conflicts_count: int = 0
    isolated_nodes_ratio: float = 0.0
    total_claims: int = 0
    verified_claims: int = 0
    weak_claims: int = 0
    unsupported_claims: int = 0


class ClaimJudgement(BaseModel):
    claim_id: str
    status: Literal["supported", "weak", "unsupported", "conflicting"]
    evidence_valid: bool | None = None
    reason: str


class NextAction(BaseModel):
    type: Literal[
        "search_expand",
        "search_more_papers",
        "reextract",
        "human_review",
        "stop"
    ]
    priority: int = 1
    why: str
    suggested_queries: list[str] = []
    target_concepts: list[str] = []


class ToolCallLog(BaseModel):
    tool: str
    latency_ms: int = 0
    success: bool = True
    error: str | None = None


class ObservabilitySummary(BaseModel):
    run_id: str = ""
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())
    decision_trace: list[str] = []
    tool_calls: list[ToolCallLog] = []
    duration_ms: int = 0


class VerifierResult(BaseModel):
    quality_gate: QualityGate
    metrics: QualityMetrics
    claim_judgements: list[ClaimJudgement] = []
    next_actions: list[NextAction] = []
    observability_summary: ObservabilitySummary = Field(
        default_factory=ObservabilitySummary
    )
```

**Step 3: 커밋**

```bash
git add src/agents/verifier/schemas.py tests/verifier/test_schemas.py
git commit -m "feat: add pydantic schemas for VerifierRequest/VerifierResult"
```

---

## Task 3: rag_get_chunk Tool 구현

**Files:**
- Create: `src/agents/verifier/tools/rag.py`
- Create: `tests/verifier/test_tools_rag.py`

**Step 1: 테스트 작성**

```python
# tests/verifier/test_tools_rag.py
import pytest
import json
from pathlib import Path
from agents.verifier.tools.rag import rag_get_chunk, set_artifacts_dir


@pytest.fixture
def setup_papers(tmp_path):
    papers = [
        {
            "arxiv_id": "2401.00001",
            "abstract": "This is the abstract text with important findings.",
            "title": "Test Paper"
        }
    ]
    papers_file = tmp_path / "test_papers.json"
    with open(papers_file, "w") as f:
        json.dump(papers, f)

    set_artifacts_dir(tmp_path)
    return tmp_path


def test_get_chunk_abstract(setup_papers):
    # rag_get_chunk는 function_tool이므로 .func로 직접 호출
    result = rag_get_chunk.func("test", "2401.00001", "abstract")
    assert result is not None
    assert "important findings" in result


def test_get_chunk_not_found(setup_papers):
    result = rag_get_chunk.func("test", "9999.99999", "abstract")
    assert result is None
```

**Step 2: 구현**

```python
# src/agents/verifier/tools/rag.py
import json
from pathlib import Path
from agents import function_tool

_artifacts_dir: Path = Path("artifacts")


def set_artifacts_dir(path: Path) -> None:
    """테스트용: artifacts 디렉토리 설정"""
    global _artifacts_dir
    _artifacts_dir = path


def get_artifacts_dir() -> Path:
    return _artifacts_dir


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
        arxiv_id: 논문 ID (예: "2401.00001")
        chunk_id: 청크 ID ("abstract" 또는 "chunk_N")

    Returns:
        청크 텍스트. 찾을 수 없으면 None.
    """
    papers_file = get_artifacts_dir() / f"{namespace}_papers.json"

    if not papers_file.exists():
        return None

    try:
        with open(papers_file, encoding="utf-8") as f:
            papers = json.load(f)
    except Exception:
        return None

    paper = next((p for p in papers if p.get("arxiv_id") == arxiv_id), None)
    if paper is None:
        return None

    # v1.0: abstract만 지원
    if chunk_id == "abstract":
        return paper.get("abstract")

    return paper.get("abstract")  # fallback
```

**Step 3: 커밋**

```bash
git add src/agents/verifier/tools/rag.py tests/verifier/test_tools_rag.py
git commit -m "feat: add rag_get_chunk tool for evidence verification"
```

---

## Task 4: kg_query Tool 구현 (mocked)

**Files:**
- Create: `src/agents/verifier/tools/kg.py`
- Create: `tests/verifier/test_tools_kg.py`

**Step 1: 테스트 작성**

```python
# tests/verifier/test_tools_kg.py
import pytest
from agents.verifier.tools.kg import kg_query


def test_kg_query_returns_empty():
    result = kg_query.func("SELECT ?s WHERE { ?s ?p ?o }")
    assert result == []
```

**Step 2: 구현**

```python
# src/agents/verifier/tools/kg.py
from agents import function_tool


@function_tool
def kg_query(sparql: str) -> list[dict]:
    """
    GraphDB에 SPARQL 쿼리를 실행합니다.
    v1.0: 모킹 - 빈 리스트 반환.

    Args:
        sparql: SPARQL 쿼리 문자열

    Returns:
        쿼리 결과 rows (v1.0에서는 빈 리스트)
    """
    # TODO: GraphDB 연동 시 활성화
    return []
```

**Step 3: tools/__init__.py 작성**

```python
# src/agents/verifier/tools/__init__.py
from agents.verifier.tools.rag import rag_get_chunk, set_artifacts_dir
from agents.verifier.tools.kg import kg_query

__all__ = ["rag_get_chunk", "kg_query", "set_artifacts_dir"]
```

**Step 4: 커밋**

```bash
git add src/agents/verifier/tools/ tests/verifier/test_tools_kg.py
git commit -m "feat: add kg_query tool (mocked for v1)"
```

---

## Task 5: Verifier Agent 정의 (핵심)

**Files:**
- Create: `src/agents/verifier/agent.py`
- Create: `tests/verifier/test_agent.py`

**Step 1: 테스트 작성**

```python
# tests/verifier/test_agent.py
import pytest
from agents.verifier.agent import verifier_agent, VERIFIER_AGENT_INSTRUCTIONS


def test_agent_has_correct_name():
    assert verifier_agent.name == "VerifierAgent"


def test_agent_has_tools():
    tool_names = [t.name for t in verifier_agent.tools]
    assert "rag_get_chunk" in tool_names
    assert "kg_query" in tool_names


def test_agent_has_output_type():
    from agents.verifier.schemas import VerifierResult
    assert verifier_agent.output_type == VerifierResult


def test_instructions_contain_key_concepts():
    assert "rag_get_chunk" in VERIFIER_AGENT_INSTRUCTIONS
    assert "quality_gate" in VERIFIER_AGENT_INSTRUCTIONS.lower()
    assert "next_actions" in VERIFIER_AGENT_INSTRUCTIONS
```

**Step 2: Agent 구현**

```python
# src/agents/verifier/agent.py
from agents import Agent
from agents.verifier.tools import rag_get_chunk, kg_query
from agents.verifier.schemas import VerifierResult

VERIFIER_AGENT_INSTRUCTIONS = """
당신은 연구 결과 검증 에이전트입니다. Extractor가 생성한 Claim과 Evidence를 검증하고, Quality Gate 통과 여부를 결정합니다.

## 역할

1. **Evidence 검증**: 각 claim의 evidence가 실제로 존재하는지 rag_get_chunk tool로 확인
2. **품질 평가**: 검증 결과를 바탕으로 metrics 계산
3. **Gate 판정**: 기준 충족 여부 결정
4. **처방 제안**: 실패 시 Self-Healing 액션 제안

## 입력 형식

JSON 형식의 VerifierRequest:
- goal: 연구 목표
- namespace: RAG 저장소 네임스페이스
- extractor_result: {paper_cards, claims, concepts, graph}
- constraints: {evidence_min, unsupported_ratio_max, min_concept_coverage, ...}

## 검증 절차

### 1단계: 스키마 검증
각 claim을 검사:
- claim_id, doc_id 필수
- evidence가 있으면 chunk_id, quote 필수
- 누락된 필드가 있으면 해당 claim은 "unsupported"

### 2단계: Evidence 검증 (Tool 호출 필수!)
상위 N개 claim에 대해 (N = constraints.evidence_check_limit):

```
rag_get_chunk(namespace, claim.doc_id, claim.evidence.chunk_id)
```

- 반환된 텍스트에 evidence.quote가 포함되면 → evidence_valid = true
- 포함되지 않으면 → evidence_valid = false (환각 의심)
- tool 호출 실패하면 → evidence_valid = null

### 3단계: Claim 상태 판정
- evidence_valid=true + 구체적 내용 → "supported"
- evidence_valid=true + 일반적 표현("We propose...", "This paper...") → "weak"
- evidence_valid=false → "unsupported"
- evidence_valid=null → "weak"

### 4단계: Conflict 감지
같은 concept_tags를 가진 claim 쌍에서 대립 키워드 탐지:
- can vs cannot
- effective vs ineffective
- outperforms vs underperforms
- succeeds vs fails

### 5단계: Metrics 계산
- evidence_coverage = verified_claims / total_claims
- unsupported_ratio = unsupported_claims / total_claims
- concept_coverage = (goal에서 추출한 concept 중 claims가 커버하는 비율)
- conflicts_count = 감지된 conflict 쌍 수

### 6단계: Quality Gate 판정
다음 조건 모두 충족 시 passed=true:
- evidence_coverage >= 0.6 (abstract-only 기준)
- unsupported_ratio <= 0.25
- concept_coverage >= 0.7
- conflicts_count <= 3

### 7단계: next_actions 생성 (실패 시)
- concept_coverage 부족 → type="search_expand", target_concepts=[부족한 concepts]
- unsupported_ratio 높음 → type="search_more_papers"
- conflicts 많음 → type="human_review"
- loops_done >= max_loops → type="stop"

## 출력 형식 (VerifierResult)

반드시 다음 JSON 구조로 출력:

```json
{
  "quality_gate": {
    "passed": true/false,
    "reasons": ["..."]
  },
  "metrics": {
    "evidence_coverage": 0.8,
    "unsupported_ratio": 0.1,
    "concept_coverage": 0.9,
    "conflicts_count": 0,
    "total_claims": 10,
    "verified_claims": 8,
    "weak_claims": 1,
    "unsupported_claims": 1
  },
  "claim_judgements": [
    {
      "claim_id": "c1",
      "status": "supported",
      "evidence_valid": true,
      "reason": "quote가 chunk에서 확인됨"
    }
  ],
  "next_actions": [
    {
      "type": "search_expand",
      "priority": 1,
      "why": "concept_coverage 0.5 < 0.7",
      "suggested_queries": ["..."],
      "target_concepts": ["Evaluation"]
    }
  ],
  "observability_summary": {
    "decision_trace": ["schema_validated", "evidence_checked_8/10", "gate_pass"],
    "tool_calls": [{"tool": "rag_get_chunk", "success": true}]
  }
}
```

## 중요 규칙

1. **반드시 rag_get_chunk를 호출하여 evidence 검증** - 추측하지 말 것
2. **Tool 호출 실패해도 중단하지 말 것** - evidence_valid=null로 처리
3. **빈 claims도 정상 처리** - metrics는 모두 0, passed=true
4. **observability_summary에 decision_trace 기록** - 디버깅용
"""

verifier_agent = Agent(
    name="VerifierAgent",
    instructions=VERIFIER_AGENT_INSTRUCTIONS,
    tools=[rag_get_chunk, kg_query],
    model="gpt-5-mini",
    output_type=VerifierResult,
)
```

**Step 3: 커밋**

```bash
git add src/agents/verifier/agent.py tests/verifier/test_agent.py
git commit -m "feat: define VerifierAgent with comprehensive instructions"
```

---

## Task 6: CLI Runner 구현

**Files:**
- Create: `src/agents/verifier/runner.py`
- Update: `src/agents/verifier/__init__.py`

**Step 1: Runner 구현**

```python
# src/agents/verifier/runner.py
import json
import click
from pathlib import Path
from agents import Runner
from agents.verifier.agent import verifier_agent
from agents.verifier.schemas import VerifierRequest, ExtractorResult
from agents.verifier.tools.rag import set_artifacts_dir


@click.command()
@click.option("--extractor-result", required=True, help="Extractor 결과 JSON 파일 경로")
@click.option("--goal", required=True, help="연구 목표")
@click.option("--namespace", default="default", help="RAG 네임스페이스")
@click.option("--output", default=None, help="결과 저장 경로")
@click.option("--artifacts-dir", default="artifacts", help="아티팩트 디렉토리")
def verify(
    extractor_result: str,
    goal: str,
    namespace: str,
    output: str | None,
    artifacts_dir: str
):
    """Verifier Agent 실행: Extractor 결과 검증"""

    # 아티팩트 디렉토리 설정
    artifacts_path = Path(artifacts_dir)
    set_artifacts_dir(artifacts_path)

    # Extractor 결과 로드
    with open(extractor_result, encoding="utf-8") as f:
        extractor_data = json.load(f)

    request = VerifierRequest(
        goal=goal,
        namespace=namespace,
        extractor_result=ExtractorResult(**extractor_data)
    )

    click.echo(f"Verifying: {goal}")
    click.echo(f"Claims: {len(request.extractor_result.claims)}")

    # Agent 실행 - JSON을 user message로 전달
    result = Runner.run_sync(verifier_agent, request.model_dump_json())

    # 결과 출력
    output_data = result.final_output.model_dump()
    click.echo("\n=== Verification Result ===")
    click.echo(f"Quality Gate: {'PASS' if output_data['quality_gate']['passed'] else 'FAIL'}")
    click.echo(f"Evidence Coverage: {output_data['metrics']['evidence_coverage']:.2%}")
    click.echo(f"Unsupported Ratio: {output_data['metrics']['unsupported_ratio']:.2%}")
    click.echo(f"Concept Coverage: {output_data['metrics']['concept_coverage']:.2%}")
    click.echo(f"Conflicts: {output_data['metrics']['conflicts_count']}")

    if not output_data['quality_gate']['passed']:
        click.echo(f"\nReasons: {output_data['quality_gate']['reasons']}")
        click.echo(f"Next Actions: {[a['type'] for a in output_data['next_actions']]}")

    # 결과 저장
    output_path = Path(output) if output else artifacts_path / f"{namespace}_verify_result.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)
    click.echo(f"\nResult saved to: {output_path}")


def main():
    verify()


if __name__ == "__main__":
    main()
```

**Step 2: __init__.py 업데이트**

```python
# src/agents/verifier/__init__.py
from agents.verifier.agent import verifier_agent
from agents.verifier.schemas import VerifierRequest, VerifierResult

__all__ = [
    "verifier_agent",
    "VerifierRequest",
    "VerifierResult",
]
```

**Step 3: 커밋**

```bash
git add src/agents/verifier/runner.py src/agents/verifier/__init__.py
git commit -m "feat: add CLI runner for VerifierAgent"
```

---

## Task 7: 통합 테스트

**Files:**
- Create: `tests/verifier/test_integration.py`

**Step 1: 통합 테스트 작성**

```python
# tests/verifier/test_integration.py
"""
통합 테스트: 실제 API 호출 포함 (CI에서는 skip)
로컬에서 OPENAI_API_KEY 설정 후 실행:
  pytest tests/verifier/test_integration.py -v -m integration
"""
import pytest
import json
import os
from pathlib import Path


@pytest.fixture
def has_api_key():
    return bool(os.getenv("OPENAI_API_KEY"))


@pytest.fixture
def sample_extractor_result(tmp_path):
    """테스트용 Extractor 결과 생성"""
    papers = [
        {
            "arxiv_id": "2401.00001",
            "title": "Graph RAG for Scientific Papers",
            "year": 2024,
            "authors": ["Author A"],
            "abstract": "We propose a novel method for graph-based retrieval augmented generation. Our approach achieves 95% accuracy on benchmark datasets."
        }
    ]
    papers_file = tmp_path / "test_papers.json"
    with open(papers_file, "w") as f:
        json.dump(papers, f)

    extractor_result = {
        "paper_cards": papers,
        "claims": [
            {
                "claim_id": "c1",
                "doc_id": "2401.00001",
                "text": "Graph RAG achieves 95% accuracy",
                "evidence": {
                    "chunk_id": "abstract",
                    "quote": "achieves 95% accuracy on benchmark datasets"
                },
                "concept_tags": ["Performance", "Graph RAG"]
            }
        ],
        "concepts": [
            {"concept_id": "concept_1", "name": "Graph RAG", "description": ""}
        ],
        "graph": None
    }

    result_file = tmp_path / "extractor_result.json"
    with open(result_file, "w") as f:
        json.dump(extractor_result, f)

    return tmp_path, result_file


@pytest.mark.integration
def test_verifier_agent_full_flow(has_api_key, sample_extractor_result):
    if not has_api_key:
        pytest.skip("OPENAI_API_KEY not set")

    from agents import Runner
    from agents.verifier.agent import verifier_agent
    from agents.verifier.schemas import VerifierRequest, ExtractorResult
    from agents.verifier.tools.rag import set_artifacts_dir

    tmp_path, result_file = sample_extractor_result
    set_artifacts_dir(tmp_path)

    with open(result_file) as f:
        extractor_data = json.load(f)

    request = VerifierRequest(
        goal="Graph RAG performance evaluation",
        namespace="test",
        extractor_result=ExtractorResult(**extractor_data)
    )

    # Agent 실행
    result = Runner.run_sync(verifier_agent, request.model_dump_json())

    # 검증
    assert result.final_output is not None
    assert hasattr(result.final_output, 'quality_gate')
    assert hasattr(result.final_output, 'metrics')
    assert hasattr(result.final_output, 'claim_judgements')

    # claim이 1개이고 evidence가 유효하면 supported여야 함
    if result.final_output.claim_judgements:
        judgement = result.final_output.claim_judgements[0]
        assert judgement.claim_id == "c1"
        # evidence_valid가 True면 supported 또는 weak
        if judgement.evidence_valid:
            assert judgement.status in ["supported", "weak"]
```

**Step 2: pytest 마커 설정**

```python
# conftest.py (또는 pyproject.toml에 추가)
def pytest_configure(config):
    config.addinivalue_line("markers", "integration: mark test as integration test")
```

**Step 3: 커밋**

```bash
git add tests/verifier/test_integration.py
git commit -m "test: add integration test for VerifierAgent"
```

---

## Task 8: 문서 및 최종 정리

**Files:**
- Update: `.gitignore`

**Step 1: .gitignore 업데이트**

```bash
echo "artifacts/" >> .gitignore
```

**Step 2: 최종 커밋**

```bash
git add .gitignore
git commit -m "docs: update gitignore for verifier-agent"
```

---

## 구현 완료 체크리스트

- [ ] Task 1: 프로젝트 구조 생성
- [ ] Task 2: Pydantic 스키마 정의
- [ ] Task 3: rag_get_chunk Tool 구현
- [ ] Task 4: kg_query Tool 구현 (mocked)
- [ ] Task 5: Verifier Agent 정의 (핵심)
- [ ] Task 6: CLI Runner 구현
- [ ] Task 7: 통합 테스트
- [ ] Task 8: 문서 및 최종 정리

---

## 주요 변경 사항 (vs 이전 설계)

| 이전 | 변경 후 |
|------|---------|
| `pipeline.py`에서 Python 로직 실행 | Agent가 직접 tool 호출하며 검증 |
| validators/ 디렉토리 | 제거 (Agent instructions로 대체) |
| 12개 Task | 8개 Task로 간소화 |
| gpt-4o-mini | gpt-5-mini |

## Agent 실행 흐름

```
1. Runner.run_sync(verifier_agent, request_json)
2. Agent가 claims 분석 (reasoning)
3. Agent가 rag_get_chunk 호출 (tool call)
4. Agent가 결과로 claim 판정 (reasoning)
5. Agent가 metrics 계산 + quality_gate 판정 (reasoning)
6. Agent가 VerifierResult JSON 출력 (structured output)
```
