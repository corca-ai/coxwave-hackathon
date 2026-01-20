# Search Agent v1.0 설계 문서

> 작성일: 2026-01-20

## 1. 개요

### 한 줄 정의
사용자 goal을 기반으로 **학술 자료를 검색·선정**하고, 선택된 문서를 **로컬 JSON에 누적 저장**하여 이후 단계(Extractor/Verifier/Writer)가 재사용할 수 있는 검색 기반을 만든다.

### 핵심 결정 사항

| 항목 | 결정 |
|------|------|
| 기존 코드 관계 | 완전 별도 구현 (`src/search_agent/`), kg2는 참고만 |
| 저장소 | 로컬 JSON (GraphDB는 Extractor 단계에서 연동) |
| 벡터/RAG | 인터페이스 모킹, 향후 구현 |
| 검색 소스 | arXiv 공식 API (확장 가능한 구조) |
| 프레임워크 | openai-agents-python |

---

## 2. 성공 기준

### Primary KPI
- 한 실행에서 **신규 문서 N개 이상 누적** (`target_new_docs=12` 기본)

### Reliability KPI
- 검색 결과 0 / 중복 과다 등 엣지 케이스에서도 **run이 중단되지 않고 정상 종료 + 이유 반환**

---

## 3. Scope

### In-scope (v1.0)
- arXiv 검색 (메타+초록)
- 후보 랭킹 (keyword + recency) + 중복 제거
- 로컬 JSON 누적 저장
- Loop (최대 2회): 신규 문서 부족 시 쿼리 확장/기간 완화
- openai-agents-python Agent + function_tool

### Out-of-scope (v1.0)
- 벡터 검색 / Semantic ranking (모킹)
- GraphDB 연동 (Extractor에서 담당)
- Full-text PDF 파싱
- Internal 문서 검색 (인터페이스만)

---

## 4. 디렉토리 구조

```
src/search_agent/
├── __init__.py
├── agent.py              # SearchAgent 정의 (openai-agents-python)
├── runner.py             # CLI 진입점 + Runner.run_sync 호출
├── schemas.py            # Pydantic 모델
├── config.py             # 설정 (API endpoints, 기본값)
├── tools/
│   ├── __init__.py
│   ├── search.py         # search_sources 툴 (arXiv + 확장 포인트)
│   └── rag.py            # rag_ingest_candidates, rag_preview (모킹)
├── clients/
│   ├── __init__.py
│   ├── arxiv_client.py   # arXiv API 호출 로직
│   └── local_store.py    # 로컬 JSON 저장소
├── ranking.py            # 후보 랭킹 로직 (keyword + recency)
└── dedup.py              # 중복 제거 로직

pyproject.toml
.env.example
artifacts/                # 실행 결과 저장
```

---

## 5. 스키마 정의

```python
# schemas.py
from pydantic import BaseModel, Field
from typing import Literal

class IngestPolicy(BaseModel):
    mode: Literal["abstract_only"] = "abstract_only"
    chunk_size: int = 512
    chunk_overlap: int = 50

class Constraints(BaseModel):
    target_new_docs: int = 12
    max_candidates: int = 80
    max_selected: int = 20
    time_range_years: int = 7
    loop_budget: int = 2
    categories: list[str] | None = None
    ingest_policy: IngestPolicy = Field(default_factory=IngestPolicy)
    preview_top_k: int = 5

class SearchRequest(BaseModel):
    goal: str
    namespace: str = "default"
    constraints: Constraints = Field(default_factory=Constraints)

class Candidate(BaseModel):
    arxiv_id: str
    title: str
    year: int
    authors: list[str]
    abstract: str
    url: str
    pdf_url: str | None = None
    categories: list[str] = []
    score: float = 0.0
    why_selected: str = ""

class LoopDecision(BaseModel):
    iteration: int
    action: str  # "keyword_expand", "time_expand", "category_relax", "terminate"
    reason: str

class QueryPlan(BaseModel):
    queries: list[str]
    time_range: str
    categories: list[str]
    loop_decisions: list[LoopDecision] = []

class IngestSummary(BaseModel):
    new_docs_added: int
    duplicates_skipped: int
    chunks_added: int = 0      # 모킹
    index_size: int = 0        # 모킹

class SearchResult(BaseModel):
    query_plan: QueryPlan
    selected_papers: list[Candidate]
    ingest_summary: IngestSummary
    preview_snippets: list[dict] = []  # 모킹
    errors: list[dict] = []
```

---

## 6. Tools 정의

### LLM-facing Tools (3개)

```python
# tools/search.py
@function_tool
def search_sources(
    queries: list[str],
    sources: list[str] = ["arxiv"],  # 확장 포인트
    max_results: int = 80,
    time_range_years: int = 7,
    categories: list[str] | None = None
) -> list[Candidate]:
    """
    지정된 소스에서 문서를 검색합니다.

    Args:
        queries: 검색 쿼리 리스트 (OR 조합)
        sources: 검색할 소스 목록 ["arxiv", "internal"]
        max_results: 최대 후보 수
        time_range_years: 검색 기간 (최근 N년)
        categories: 카테고리 필터 (예: ["cs.AI", "cs.CL"])

    Returns:
        검색된 문서 후보 리스트
    """
```

```python
# tools/rag.py
@function_tool
def rag_ingest_candidates(
    namespace: str,
    candidates: list[Candidate],
    ingest_policy: IngestPolicy
) -> IngestSummary:
    """
    선택된 문서를 knowledge base에 저장합니다.
    v1.0: 로컬 JSON에 저장. 벡터 인덱싱은 모킹.
    """

@function_tool
def rag_preview(
    namespace: str,
    query: str,
    top_k: int = 5
) -> list[dict]:
    """
    저장된 문서에서 관련 스니펫을 검색합니다.
    v1.0: 모킹 - 빈 리스트 반환.
    """
    return []
```

---

## 7. Agent 정의

```python
# agent.py
from agents import Agent
from tools.search import search_sources
from tools.rag import rag_ingest_candidates, rag_preview
from schemas import SearchResult

SEARCH_AGENT_INSTRUCTIONS = """
당신은 연구 논문 검색 에이전트입니다. 사용자의 연구 목표(goal)를 기반으로 학술 자료를 검색하고, knowledge base에 저장합니다.

## 작업 순서

1. **쿼리 생성**: goal에서 핵심 키워드 3-5개를 추출하여 검색 쿼리를 만듭니다.

2. **검색 실행**: search_sources를 호출하여 후보 문서를 가져옵니다.
   - 사용 가능한 소스: arxiv (기본), internal (향후 확장)
   - 소스별 특성에 맞게 쿼리를 조정할 수 있습니다.

3. **문서 선정**: 후보 중 goal과 가장 관련 있는 문서를 선정합니다.
   - 각 문서에 why_selected를 반드시 작성합니다.

4. **저장**: rag_ingest_candidates로 선정된 문서를 저장합니다.

5. **루프 판단**: 신규 저장 수가 target_new_docs 미만이면:
   - 1차: 키워드 확장 (동의어, 상위 개념 추가)
   - 2차: 기간/범위 확장
   - loop_budget 소진 또는 2회 연속 신규 0이면 종료

6. **결과 반환**: SearchResult 형식의 JSON으로 반환합니다.

## 중요 규칙

- 항상 loop_decisions에 각 단계의 판단 이유를 기록합니다.
- 검색 결과가 0이어도 중단하지 말고, 쿼리를 조정하여 재시도합니다.
- 최종 출력은 반드시 SearchResult JSON 형식이어야 합니다.
"""

search_agent = Agent(
    name="SearchAgent",
    instructions=SEARCH_AGENT_INSTRUCTIONS,
    tools=[search_sources, rag_ingest_candidates, rag_preview],
    model="gpt-4o",
    output_type=SearchResult,
)
```

---

## 8. 저장소 전략

### 아키텍처
```
Search Agent → artifacts/{namespace}_papers.json (로컬)
     ↓
Extractor Agent → GraphDB (Paper/Claim/Concept)
     ↓              ↓ (fallback)
              artifacts/graph.json
```

### 로컬 저장소 구현

```python
# clients/local_store.py
class LocalStore:
    """Search Agent용 로컬 저장소"""

    def save_result(self, namespace: str, result: SearchResult) -> Path:
        """검색 결과를 JSON으로 저장"""

    def load_existing_ids(self, namespace: str) -> set[str]:
        """기존 저장된 arxiv_id 목록 로드 (중복 체크용)"""

    def append_papers(self, namespace: str, candidates: list[Candidate]) -> int:
        """신규 논문을 로컬 JSON에 누적, 추가된 수 반환"""
```

### 설계 의도
- Search Agent는 GraphDB를 건드리지 않음
- GraphDB 연동은 Extractor 단계에서 담당
- GraphDB 장애 시에도 Search Agent는 정상 동작

---

## 9. Search Loop 정책

### 종료 조건
- `new_docs_added >= target_new_docs`
- 또는 `loop_budget` 소진
- 또는 `no_new_docs`가 2회 연속

### 루프 액션 (순서 고정)
1. **키워드 확장**: 동의어/상위개념 2-3개 추가
2. **기간 확장**: 7년 → 10년
3. **카테고리 완화**: 제한 있었다면 제거

### 실패 복구
- 검색 결과 0: 쿼리 확장 → 그래도 0이면 이유 반환
- 중복만 나옴: 기간/키워드 확장 → 그래도 중복이면 "DB가 이미 커버" 메시지

---

## 10. Ranking & Dedupe

### Ranking (v1.0)
```
score = keyword_match(0.6) + recency(0.4)
```
- Semantic ranking은 v1.1에서 추가 예정

### Dedupe 키
1. `arxiv_id` 동일
2. DOI 동일 (있으면)
3. title 정규화 유사 (후순위)

---

## 11. 의존성 & 설정

### pyproject.toml
```toml
[project]
name = "search-agent"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
    "openai-agents>=0.0.3",
    "arxiv>=2.1.0",
    "httpx>=0.27.0",
    "pydantic>=2.0.0",
    "click>=8.1.0",
    "python-dotenv>=1.0.0",
]

[project.optional-dependencies]
dev = ["pytest>=8.0.0", "ruff>=0.4.0"]
```

### .env.example
```bash
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o
ARTIFACTS_DIR=artifacts
```

---

## 12. CLI 사용법

```bash
# 기본 실행
python -m search_agent.runner --goal "Graph RAG for scientific papers"

# 옵션 지정
python -m search_agent.runner \
  --goal "LLM agents for code generation" \
  --namespace demo \
  --target-docs 20 \
  --output artifacts/result.json
```

---

## 13. 구현 체크리스트

1. [ ] 프로젝트 구조 생성 (`src/search_agent/`)
2. [ ] Pydantic 스키마 정의 (`schemas.py`)
3. [ ] arXiv 클라이언트 구현 (`clients/arxiv_client.py`)
4. [ ] 로컬 저장소 구현 (`clients/local_store.py`)
5. [ ] Ranking/Dedupe 로직 (`ranking.py`, `dedup.py`)
6. [ ] Tools 구현 (`tools/search.py`, `tools/rag.py`)
7. [ ] Agent 정의 (`agent.py`)
8. [ ] CLI Runner (`runner.py`)
9. [ ] End-to-end 테스트
10. [ ] artifacts 저장 검증

---

## 14. 향후 확장 포인트

- **벡터 검색**: `rag_preview` 모킹 해제, FAISS/Chroma 연동
- **추가 소스**: `search_sources`의 `sources` 파라미터로 internal, S2 등 추가
- **GraphDB 연동**: Extractor Agent에서 담당
