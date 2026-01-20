# Search Agent Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** arXiv 논문 검색 + 로컬 JSON 누적 저장하는 단일 에이전트 구현

**Architecture:** openai-agents-python 기반 단일 Agent, 3개 function_tool (search_sources, rag_ingest_candidates, rag_preview), 로컬 JSON 저장소

**Tech Stack:** Python 3.11+, openai-agents, arxiv, pydantic, click, httpx

**Design Doc:** `docs/plans/2026-01-20-search-agent-design.md`

---

## Task 1: 프로젝트 구조 생성

**Files:**
- Create: `src/__init__.py`
- Create: `src/agents/__init__.py`
- Create: `src/agents/search/__init__.py`
- Create: `src/agents/search/tools/__init__.py`
- Create: `src/agents/search/clients/__init__.py`
- Create: `src/shared/__init__.py`
- Create: `pyproject.toml`
- Create: `.env.example`

**Step 1: 디렉토리 구조 생성**

```bash
mkdir -p src/agents/search/tools src/agents/search/clients src/shared
touch src/__init__.py
touch src/agents/__init__.py
touch src/agents/search/__init__.py
touch src/agents/search/tools/__init__.py
touch src/agents/search/clients/__init__.py
touch src/shared/__init__.py
```

**Step 2: pyproject.toml 작성**

```toml
[project]
name = "researcher"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
    "openai-agents>=0.0.3",
    "arxiv>=2.1.0",
    "httpx>=0.27.0",
    "pydantic>=2.0.0",
    "pydantic-settings>=2.0.0",
    "click>=8.1.0",
    "python-dotenv>=1.0.0",
]

[project.optional-dependencies]
dev = ["pytest>=8.0.0", "ruff>=0.4.0"]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.ruff]
line-length = 100
target-version = "py311"

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["src"]
```

**Step 3: .env.example 작성**

```bash
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-5-mini
ARTIFACTS_DIR=artifacts
```

**Step 4: 커밋**

```bash
git add src/ pyproject.toml .env.example
git commit -m "chore: initialize search-agent project structure"
```

---

## Task 2: Pydantic 스키마 정의

**Files:**
- Create: `src/agents/search/schemas.py`
- Create: `tests/test_schemas.py`

**Step 1: 테스트 먼저 작성**

```python
# tests/test_schemas.py
import pytest
from agents.search.schemas import (
    SearchRequest,
    SearchResult,
    Candidate,
    Constraints,
    IngestPolicy,
    QueryPlan,
    IngestSummary,
    LoopDecision,
)


def test_search_request_defaults():
    req = SearchRequest(goal="test goal")
    assert req.goal == "test goal"
    assert req.namespace == "default"
    assert req.constraints.target_new_docs == 12


def test_candidate_required_fields():
    c = Candidate(
        arxiv_id="2401.00001",
        title="Test Paper",
        year=2024,
        authors=["Author A"],
        abstract="Abstract text",
        url="https://arxiv.org/abs/2401.00001",
    )
    assert c.arxiv_id == "2401.00001"
    assert c.score == 0.0  # default
    assert c.why_selected == ""  # default


def test_search_result_structure():
    result = SearchResult(
        query_plan=QueryPlan(queries=["test"], time_range="2017-2024", categories=[]),
        selected_papers=[],
        ingest_summary=IngestSummary(new_docs_added=0, duplicates_skipped=0),
    )
    assert result.errors == []
    assert result.preview_snippets == []
```

**Step 2: 테스트 실행 (실패 확인)**

```bash
pytest tests/test_schemas.py -v
```

Expected: FAIL - `ModuleNotFoundError: No module named 'agents'`

**Step 3: 스키마 구현**

```python
# src/agents/search/schemas.py
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
    chunks_added: int = 0
    index_size: int = 0


class PreviewSnippet(BaseModel):
    arxiv_id: str
    chunk_id: str
    score: float
    snippet: str


class SearchError(BaseModel):
    code: str
    message: str
    retryable: bool = False


class SearchResult(BaseModel):
    query_plan: QueryPlan
    selected_papers: list[Candidate]
    ingest_summary: IngestSummary
    preview_snippets: list[PreviewSnippet] = []
    errors: list[SearchError] = []
```

**Step 4: 테스트 실행 (통과 확인)**

```bash
pytest tests/test_schemas.py -v
```

Expected: PASS

**Step 5: 커밋**

```bash
git add src/agents/search/schemas.py tests/test_schemas.py
git commit -m "feat: add pydantic schemas for SearchRequest/SearchResult"
```

---

## Task 3: Config 모듈 구현

**Files:**
- Create: `src/shared/config.py`
- Create: `tests/test_config.py`

**Step 1: 테스트 작성**

```python
# tests/test_config.py
import os
import pytest


def test_settings_defaults(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    # Re-import to pick up env var
    from shared.config import Settings
    settings = Settings()

    assert settings.openai_api_key == "test-key"
    assert settings.openai_model == "gpt-5-mini"
    assert settings.artifacts_dir == "artifacts"
```

**Step 2: 테스트 실행 (실패 확인)**

```bash
pytest tests/test_config.py -v
```

Expected: FAIL

**Step 3: Config 구현**

```python
# src/shared/config.py
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    openai_api_key: str
    openai_model: str = "gpt-5-mini"
    artifacts_dir: str = "artifacts"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


def get_settings() -> Settings:
    return Settings()
```

**Step 4: 테스트 실행 (통과 확인)**

```bash
pytest tests/test_config.py -v
```

Expected: PASS

**Step 5: 커밋**

```bash
git add src/shared/config.py tests/test_config.py
git commit -m "feat: add shared config module with pydantic-settings"
```

---

## Task 4: arXiv 클라이언트 구현

**Files:**
- Create: `src/agents/search/clients/arxiv_client.py`
- Create: `tests/test_arxiv_client.py`

**Step 1: 테스트 작성 (모킹 사용)**

```python
# tests/test_arxiv_client.py
import pytest
from unittest.mock import Mock, patch
from datetime import datetime
from agents.search.clients.arxiv_client import ArxivClient, ArxivSearchParams


def test_build_query_simple():
    client = ArxivClient()
    params = ArxivSearchParams(queries=["graph neural network"])
    query = client._build_query(params)
    assert "graph neural network" in query


def test_build_query_with_categories():
    client = ArxivClient()
    params = ArxivSearchParams(
        queries=["transformer"],
        categories=["cs.AI", "cs.CL"],
    )
    query = client._build_query(params)
    assert "cat:cs.AI" in query or "cat:cs.CL" in query


def test_parse_result():
    client = ArxivClient()

    mock_result = Mock()
    mock_result.entry_id = "http://arxiv.org/abs/2401.00001v1"
    mock_result.title = "Test Paper Title"
    mock_result.summary = "This is the abstract."
    mock_result.authors = [Mock(name="Author A"), Mock(name="Author B")]
    mock_result.published = datetime(2024, 1, 15)
    mock_result.categories = ["cs.AI", "cs.LG"]
    mock_result.pdf_url = "http://arxiv.org/pdf/2401.00001v1"

    candidate = client._parse_result(mock_result)

    assert candidate.arxiv_id == "2401.00001"
    assert candidate.title == "Test Paper Title"
    assert candidate.year == 2024
    assert "Author A" in candidate.authors
```

**Step 2: 테스트 실행 (실패 확인)**

```bash
pytest tests/test_arxiv_client.py -v
```

Expected: FAIL

**Step 3: arXiv 클라이언트 구현**

```python
# src/agents/search/clients/arxiv_client.py
import arxiv
import re
from datetime import datetime, timedelta
from dataclasses import dataclass
from agents.search.schemas import Candidate


@dataclass
class ArxivSearchParams:
    queries: list[str]
    max_results: int = 80
    time_range_years: int = 7
    categories: list[str] | None = None


class ArxivClient:
    def __init__(self):
        self.client = arxiv.Client()

    def search(self, params: ArxivSearchParams) -> list[Candidate]:
        """arXiv에서 논문 검색"""
        query = self._build_query(params)

        search = arxiv.Search(
            query=query,
            max_results=params.max_results,
            sort_by=arxiv.SortCriterion.SubmittedDate,
            sort_order=arxiv.SortOrder.Descending,
        )

        candidates = []
        for result in self.client.results(search):
            candidate = self._parse_result(result)
            if candidate:
                candidates.append(candidate)

        return candidates

    def _build_query(self, params: ArxivSearchParams) -> str:
        """검색 쿼리 문자열 생성"""
        # 쿼리 결합 (OR)
        query_parts = [f'all:"{q}"' for q in params.queries]
        query = " OR ".join(query_parts)

        # 카테고리 필터
        if params.categories:
            cat_parts = [f"cat:{cat}" for cat in params.categories]
            cat_query = " OR ".join(cat_parts)
            query = f"({query}) AND ({cat_query})"

        return query

    def _parse_result(self, result: arxiv.Result) -> Candidate | None:
        """arxiv.Result를 Candidate로 변환"""
        try:
            # arxiv_id 추출 (예: 2401.00001)
            arxiv_id = self._extract_arxiv_id(result.entry_id)

            return Candidate(
                arxiv_id=arxiv_id,
                title=result.title.replace("\n", " ").strip(),
                year=result.published.year,
                authors=[str(a) for a in result.authors],
                abstract=result.summary.replace("\n", " ").strip(),
                url=result.entry_id,
                pdf_url=result.pdf_url,
                categories=list(result.categories),
            )
        except Exception:
            return None

    def _extract_arxiv_id(self, entry_id: str) -> str:
        """entry_id에서 arxiv_id 추출"""
        # http://arxiv.org/abs/2401.00001v1 -> 2401.00001
        match = re.search(r"(\d{4}\.\d{4,5})", entry_id)
        if match:
            return match.group(1)
        # 구형 ID 형식 처리 (예: hep-th/9901001)
        match = re.search(r"([a-z-]+/\d+)", entry_id)
        if match:
            return match.group(1)
        raise ValueError(f"Cannot extract arxiv_id from {entry_id}")
```

**Step 4: 테스트 실행 (통과 확인)**

```bash
pytest tests/test_arxiv_client.py -v
```

Expected: PASS

**Step 5: 커밋**

```bash
git add src/agents/search/clients/arxiv_client.py tests/test_arxiv_client.py
git commit -m "feat: add arXiv client for paper search"
```

---

## Task 5: 로컬 저장소 구현

**Files:**
- Create: `src/agents/search/clients/local_store.py`
- Create: `tests/test_local_store.py`

**Step 1: 테스트 작성**

```python
# tests/test_local_store.py
import pytest
import json
from pathlib import Path
from agents.search.clients.local_store import LocalStore
from agents.search.schemas import Candidate, SearchResult, QueryPlan, IngestSummary


@pytest.fixture
def tmp_store(tmp_path):
    return LocalStore(artifacts_dir=tmp_path)


@pytest.fixture
def sample_candidate():
    return Candidate(
        arxiv_id="2401.00001",
        title="Test Paper",
        year=2024,
        authors=["Author A"],
        abstract="Abstract text",
        url="https://arxiv.org/abs/2401.00001",
    )


def test_load_existing_ids_empty(tmp_store):
    ids = tmp_store.load_existing_ids("test")
    assert ids == set()


def test_append_papers_new(tmp_store, sample_candidate):
    added = tmp_store.append_papers("test", [sample_candidate])
    assert added == 1

    ids = tmp_store.load_existing_ids("test")
    assert "2401.00001" in ids


def test_append_papers_duplicate(tmp_store, sample_candidate):
    tmp_store.append_papers("test", [sample_candidate])
    added = tmp_store.append_papers("test", [sample_candidate])
    assert added == 0  # 중복이라 추가 안됨


def test_save_result(tmp_store, sample_candidate):
    result = SearchResult(
        query_plan=QueryPlan(queries=["test"], time_range="2017-2024", categories=[]),
        selected_papers=[sample_candidate],
        ingest_summary=IngestSummary(new_docs_added=1, duplicates_skipped=0),
    )

    path = tmp_store.save_result("test", result)
    assert path.exists()

    with open(path) as f:
        data = json.load(f)
    assert data["selected_papers"][0]["arxiv_id"] == "2401.00001"
```

**Step 2: 테스트 실행 (실패 확인)**

```bash
pytest tests/test_local_store.py -v
```

Expected: FAIL

**Step 3: 로컬 저장소 구현**

```python
# src/agents/search/clients/local_store.py
import json
from pathlib import Path
from agents.search.schemas import Candidate, SearchResult


class LocalStore:
    """Search Agent용 로컬 JSON 저장소"""

    def __init__(self, artifacts_dir: Path | str = Path("artifacts")):
        self.artifacts_dir = Path(artifacts_dir)
        self.artifacts_dir.mkdir(parents=True, exist_ok=True)

    def save_result(self, namespace: str, result: SearchResult) -> Path:
        """검색 결과를 JSON으로 저장"""
        path = self.artifacts_dir / f"{namespace}_search_result.json"
        with open(path, "w", encoding="utf-8") as f:
            json.dump(result.model_dump(), f, ensure_ascii=False, indent=2)
        return path

    def load_existing_ids(self, namespace: str) -> set[str]:
        """기존 저장된 arxiv_id 목록 로드 (중복 체크용)"""
        path = self.artifacts_dir / f"{namespace}_papers.json"
        if not path.exists():
            return set()
        with open(path, encoding="utf-8") as f:
            papers = json.load(f)
        return {p["arxiv_id"] for p in papers}

    def append_papers(self, namespace: str, candidates: list[Candidate]) -> int:
        """신규 논문을 로컬 JSON에 누적, 추가된 수 반환"""
        path = self.artifacts_dir / f"{namespace}_papers.json"

        existing: list[dict] = []
        if path.exists():
            with open(path, encoding="utf-8") as f:
                existing = json.load(f)

        existing_ids = {p["arxiv_id"] for p in existing}
        new_papers = [
            c.model_dump() for c in candidates if c.arxiv_id not in existing_ids
        ]

        if new_papers:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(existing + new_papers, f, ensure_ascii=False, indent=2)

        return len(new_papers)

    def count_papers(self, namespace: str) -> int:
        """저장된 논문 수 반환"""
        path = self.artifacts_dir / f"{namespace}_papers.json"
        if not path.exists():
            return 0
        with open(path, encoding="utf-8") as f:
            papers = json.load(f)
        return len(papers)
```

**Step 4: 테스트 실행 (통과 확인)**

```bash
pytest tests/test_local_store.py -v
```

Expected: PASS

**Step 5: 커밋**

```bash
git add src/agents/search/clients/local_store.py tests/test_local_store.py
git commit -m "feat: add local JSON store for paper persistence"
```

---

## Task 6: Ranking & Dedup 로직 구현

**Files:**
- Create: `src/agents/search/ranking.py`
- Create: `src/agents/search/dedup.py`
- Create: `tests/test_ranking.py`
- Create: `tests/test_dedup.py`

**Step 1: Dedup 테스트 작성**

```python
# tests/test_dedup.py
import pytest
from agents.search.dedup import dedupe_candidates
from agents.search.schemas import Candidate


def make_candidate(arxiv_id: str, title: str = "Title") -> Candidate:
    return Candidate(
        arxiv_id=arxiv_id,
        title=title,
        year=2024,
        authors=["A"],
        abstract="Abstract",
        url=f"https://arxiv.org/abs/{arxiv_id}",
    )


def test_dedupe_by_arxiv_id():
    candidates = [
        make_candidate("2401.00001"),
        make_candidate("2401.00001"),  # duplicate
        make_candidate("2401.00002"),
    ]
    result = dedupe_candidates(candidates)
    assert len(result) == 2


def test_dedupe_preserves_order():
    candidates = [
        make_candidate("2401.00003"),
        make_candidate("2401.00001"),
        make_candidate("2401.00002"),
    ]
    result = dedupe_candidates(candidates)
    assert result[0].arxiv_id == "2401.00003"
```

**Step 2: Ranking 테스트 작성**

```python
# tests/test_ranking.py
import pytest
from agents.search.ranking import rank_candidates, calculate_score
from agents.search.schemas import Candidate


def make_candidate(arxiv_id: str, year: int, title: str = "Title") -> Candidate:
    return Candidate(
        arxiv_id=arxiv_id,
        title=title,
        year=year,
        authors=["A"],
        abstract="Abstract about machine learning",
        url=f"https://arxiv.org/abs/{arxiv_id}",
    )


def test_calculate_score_keyword_match():
    candidate = make_candidate("2401.00001", 2024, "Machine Learning Paper")
    score = calculate_score(candidate, ["machine", "learning"])
    assert score > 0


def test_rank_candidates_by_recency():
    candidates = [
        make_candidate("2401.00001", 2020),
        make_candidate("2401.00002", 2024),
        make_candidate("2401.00003", 2022),
    ]
    ranked = rank_candidates(candidates, ["test"])
    # 최신이 더 높은 점수
    years = [c.year for c in ranked]
    assert years[0] >= years[-1]  # 내림차순 경향
```

**Step 3: 테스트 실행 (실패 확인)**

```bash
pytest tests/test_dedup.py tests/test_ranking.py -v
```

Expected: FAIL

**Step 4: Dedup 구현**

```python
# src/agents/search/dedup.py
from agents.search.schemas import Candidate


def dedupe_candidates(
    candidates: list[Candidate],
    existing_ids: set[str] | None = None,
) -> list[Candidate]:
    """중복 제거 (arxiv_id 기준), 순서 유지"""
    seen: set[str] = existing_ids.copy() if existing_ids else set()
    result: list[Candidate] = []

    for c in candidates:
        if c.arxiv_id not in seen:
            seen.add(c.arxiv_id)
            result.append(c)

    return result
```

**Step 5: Ranking 구현**

```python
# src/agents/search/ranking.py
import re
from datetime import datetime
from agents.search.schemas import Candidate


def calculate_score(candidate: Candidate, keywords: list[str]) -> float:
    """
    랭킹 점수 계산: keyword_match(0.6) + recency(0.4)
    """
    # Keyword match score (0-1)
    text = f"{candidate.title} {candidate.abstract}".lower()
    keyword_hits = sum(1 for kw in keywords if kw.lower() in text)
    keyword_score = min(keyword_hits / max(len(keywords), 1), 1.0)

    # Recency score (0-1)
    current_year = datetime.now().year
    years_old = current_year - candidate.year
    recency_score = max(0, 1 - (years_old / 10))  # 10년 이상이면 0

    # Weighted sum
    score = (keyword_score * 0.6) + (recency_score * 0.4)
    return round(score, 4)


def rank_candidates(
    candidates: list[Candidate],
    keywords: list[str],
    max_results: int | None = None,
) -> list[Candidate]:
    """후보 논문 랭킹 및 정렬"""
    for c in candidates:
        c.score = calculate_score(c, keywords)

    sorted_candidates = sorted(candidates, key=lambda c: c.score, reverse=True)

    if max_results:
        return sorted_candidates[:max_results]
    return sorted_candidates
```

**Step 6: 테스트 실행 (통과 확인)**

```bash
pytest tests/test_dedup.py tests/test_ranking.py -v
```

Expected: PASS

**Step 7: 커밋**

```bash
git add src/agents/search/ranking.py src/agents/search/dedup.py tests/test_ranking.py tests/test_dedup.py
git commit -m "feat: add ranking and dedup logic for candidates"
```

---

## Task 7: Tools 구현 (search_sources)

**Files:**
- Create: `src/agents/search/tools/search.py`
- Create: `tests/test_tools_search.py`

**Step 1: 테스트 작성**

```python
# tests/test_tools_search.py
import pytest
from unittest.mock import Mock, patch
from agents.search.tools.search import search_sources
from agents.search.schemas import Candidate


@pytest.fixture
def mock_arxiv_client():
    with patch("agents.search.tools.search.ArxivClient") as mock:
        client_instance = Mock()
        client_instance.search.return_value = [
            Candidate(
                arxiv_id="2401.00001",
                title="Test Paper",
                year=2024,
                authors=["Author A"],
                abstract="About machine learning",
                url="https://arxiv.org/abs/2401.00001",
            )
        ]
        mock.return_value = client_instance
        yield client_instance


def test_search_sources_arxiv(mock_arxiv_client):
    result = search_sources(
        queries=["machine learning"],
        sources=["arxiv"],
        max_results=10,
    )
    assert len(result) == 1
    assert result[0].arxiv_id == "2401.00001"
    mock_arxiv_client.search.assert_called_once()


def test_search_sources_unknown_source():
    result = search_sources(
        queries=["test"],
        sources=["unknown_source"],
        max_results=10,
    )
    assert result == []  # 알 수 없는 소스는 빈 결과
```

**Step 2: 테스트 실행 (실패 확인)**

```bash
pytest tests/test_tools_search.py -v
```

Expected: FAIL

**Step 3: search_sources 구현**

```python
# src/agents/search/tools/search.py
from agents import function_tool
from agents.search.schemas import Candidate
from agents.search.clients.arxiv_client import ArxivClient, ArxivSearchParams
from agents.search.ranking import rank_candidates
from agents.search.dedup import dedupe_candidates


@function_tool
def search_sources(
    queries: list[str],
    sources: list[str] = ["arxiv"],
    max_results: int = 80,
    time_range_years: int = 7,
    categories: list[str] | None = None,
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
        검색된 문서 후보 리스트 (랭킹 및 중복 제거 완료)
    """
    all_candidates: list[Candidate] = []

    for source in sources:
        if source == "arxiv":
            client = ArxivClient()
            params = ArxivSearchParams(
                queries=queries,
                max_results=max_results,
                time_range_years=time_range_years,
                categories=categories,
            )
            candidates = client.search(params)
            all_candidates.extend(candidates)
        elif source == "internal":
            # TODO: internal 소스 구현 (v1.1)
            pass
        # 알 수 없는 소스는 무시

    # 중복 제거
    deduped = dedupe_candidates(all_candidates)

    # 랭킹
    keywords = []
    for q in queries:
        keywords.extend(q.lower().split())
    ranked = rank_candidates(deduped, keywords, max_results=max_results)

    return ranked
```

**Step 4: 테스트 실행 (통과 확인)**

```bash
pytest tests/test_tools_search.py -v
```

Expected: PASS

**Step 5: 커밋**

```bash
git add src/agents/search/tools/search.py tests/test_tools_search.py
git commit -m "feat: add search_sources tool with arxiv integration"
```

---

## Task 8: Tools 구현 (RAG - 모킹)

**Files:**
- Create: `src/agents/search/tools/rag.py`
- Create: `tests/test_tools_rag.py`

**Step 1: 테스트 작성**

```python
# tests/test_tools_rag.py
import pytest
from pathlib import Path
from agents.search.tools.rag import rag_ingest_candidates, rag_preview, set_artifacts_dir
from agents.search.schemas import Candidate, IngestPolicy


@pytest.fixture
def sample_candidates():
    return [
        Candidate(
            arxiv_id="2401.00001",
            title="Paper 1",
            year=2024,
            authors=["A"],
            abstract="Abstract 1",
            url="https://arxiv.org/abs/2401.00001",
        ),
        Candidate(
            arxiv_id="2401.00002",
            title="Paper 2",
            year=2024,
            authors=["B"],
            abstract="Abstract 2",
            url="https://arxiv.org/abs/2401.00002",
        ),
    ]


def test_rag_ingest_candidates(tmp_path, sample_candidates):
    set_artifacts_dir(tmp_path)

    result = rag_ingest_candidates(
        namespace="test",
        candidates=sample_candidates,
        ingest_policy=IngestPolicy(),
    )

    assert result.new_docs_added == 2
    assert result.duplicates_skipped == 0


def test_rag_ingest_duplicates(tmp_path, sample_candidates):
    set_artifacts_dir(tmp_path)

    # 첫 번째 인제스트
    rag_ingest_candidates("test", sample_candidates, IngestPolicy())

    # 두 번째 인제스트 (중복)
    result = rag_ingest_candidates("test", sample_candidates, IngestPolicy())

    assert result.new_docs_added == 0
    assert result.duplicates_skipped == 2


def test_rag_preview_returns_empty():
    result = rag_preview(namespace="test", query="test query", top_k=5)
    assert result == []  # 모킹
```

**Step 2: 테스트 실행 (실패 확인)**

```bash
pytest tests/test_tools_rag.py -v
```

Expected: FAIL

**Step 3: RAG tools 구현**

```python
# src/agents/search/tools/rag.py
from pathlib import Path
from agents import function_tool
from agents.search.schemas import Candidate, IngestPolicy, IngestSummary, PreviewSnippet
from agents.search.clients.local_store import LocalStore

# 모듈 레벨 저장소 (테스트에서 교체 가능)
_store: LocalStore | None = None


def get_store() -> LocalStore:
    global _store
    if _store is None:
        _store = LocalStore()
    return _store


def set_artifacts_dir(path: Path) -> None:
    """테스트용: artifacts 디렉토리 설정"""
    global _store
    _store = LocalStore(artifacts_dir=path)


@function_tool
def rag_ingest_candidates(
    namespace: str,
    candidates: list[Candidate],
    ingest_policy: IngestPolicy,
) -> IngestSummary:
    """
    선택된 문서를 knowledge base에 저장합니다.
    v1.0: 로컬 JSON에 저장. 벡터 인덱싱은 모킹.

    Args:
        namespace: 저장소 네임스페이스
        candidates: 저장할 문서 후보 리스트
        ingest_policy: 인제스트 정책 (현재 abstract_only만 지원)

    Returns:
        인제스트 결과 요약
    """
    store = get_store()

    existing_ids = store.load_existing_ids(namespace)

    new_candidates = [c for c in candidates if c.arxiv_id not in existing_ids]
    duplicates = len(candidates) - len(new_candidates)

    new_docs_added = store.append_papers(namespace, new_candidates)

    return IngestSummary(
        new_docs_added=new_docs_added,
        duplicates_skipped=duplicates,
        chunks_added=0,  # 모킹
        index_size=store.count_papers(namespace),
    )


@function_tool
def rag_preview(
    namespace: str,
    query: str,
    top_k: int = 5,
) -> list[PreviewSnippet]:
    """
    저장된 문서에서 관련 스니펫을 검색합니다.
    v1.0: 모킹 - 빈 리스트 반환.

    Args:
        namespace: 저장소 네임스페이스
        query: 검색 쿼리
        top_k: 반환할 최대 스니펫 수

    Returns:
        관련 스니펫 리스트 (v1.0에서는 빈 리스트)
    """
    # TODO: 벡터 검색 구현 시 활성화
    return []
```

**Step 4: 테스트 실행 (통과 확인)**

```bash
pytest tests/test_tools_rag.py -v
```

Expected: PASS

**Step 5: tools/__init__.py 업데이트**

```python
# src/agents/search/tools/__init__.py
from agents.search.tools.search import search_sources
from agents.search.tools.rag import rag_ingest_candidates, rag_preview

__all__ = ["search_sources", "rag_ingest_candidates", "rag_preview"]
```

**Step 6: 커밋**

```bash
git add src/agents/search/tools/rag.py src/agents/search/tools/__init__.py tests/test_tools_rag.py
git commit -m "feat: add rag_ingest_candidates and rag_preview tools (mocked)"
```

---

## Task 9: Agent 정의

**Files:**
- Create: `src/agents/search/agent.py`
- Create: `tests/test_agent.py`

**Step 1: 테스트 작성**

```python
# tests/test_agent.py
import pytest
from agents.search.agent import search_agent, SEARCH_AGENT_INSTRUCTIONS


def test_agent_has_correct_name():
    assert agents.search.name == "SearchAgent"


def test_agent_has_tools():
    tool_names = [t.name for t in agents.search.tools]
    assert "search_sources" in tool_names
    assert "rag_ingest_candidates" in tool_names
    assert "rag_preview" in tool_names


def test_agent_instructions_contain_key_steps():
    assert "쿼리 생성" in SEARCH_AGENT_INSTRUCTIONS
    assert "검색 실행" in SEARCH_AGENT_INSTRUCTIONS
    assert "문서 선정" in SEARCH_AGENT_INSTRUCTIONS
    assert "저장" in SEARCH_AGENT_INSTRUCTIONS
    assert "루프 판단" in SEARCH_AGENT_INSTRUCTIONS
```

**Step 2: 테스트 실행 (실패 확인)**

```bash
pytest tests/test_agent.py -v
```

Expected: FAIL

**Step 3: Agent 구현**

```python
# src/agents/search/agent.py
from agents import Agent
from agents.search.tools import search_sources, rag_ingest_candidates, rag_preview
from agents.search.schemas import SearchResult

SEARCH_AGENT_INSTRUCTIONS = """
당신은 연구 논문 검색 에이전트입니다. 사용자의 연구 목표(goal)를 기반으로 학술 자료를 검색하고, knowledge base에 저장합니다.

## 작업 순서

1. **쿼리 생성**: goal에서 핵심 키워드 3-5개를 추출하여 검색 쿼리를 만듭니다.

2. **검색 실행**: search_sources를 호출하여 후보 문서를 가져옵니다.
   - 사용 가능한 소스: arxiv (기본), internal (향후 확장)
   - 소스별 특성에 맞게 쿼리를 조정할 수 있습니다.

3. **문서 선정**: 후보 중 goal과 가장 관련 있는 문서를 선정합니다.
   - max_selected 이하로 선정합니다.
   - 각 문서에 why_selected를 반드시 작성합니다.

4. **저장**: rag_ingest_candidates로 선정된 문서를 저장합니다.

5. **루프 판단**: 신규 저장 수가 target_new_docs 미만이면:
   - 1차: 키워드 확장 (동의어, 상위 개념 추가)
   - 2차: 기간/범위 확장 (time_range_years 증가)
   - loop_budget 소진 또는 2회 연속 신규 0이면 종료

6. **결과 반환**: SearchResult 형식의 JSON으로 반환합니다.

## 중요 규칙

- 항상 loop_decisions에 각 단계의 판단 이유를 기록합니다.
- 검색 결과가 0이어도 중단하지 말고, 쿼리를 조정하여 재시도합니다.
- 최종 출력은 반드시 SearchResult JSON 형식이어야 합니다.
- why_selected는 해당 논문이 goal과 어떻게 관련되는지 구체적으로 설명합니다.
"""

search_agent = Agent(
    name="SearchAgent",
    instructions=SEARCH_AGENT_INSTRUCTIONS,
    tools=[search_sources, rag_ingest_candidates, rag_preview],
    model="gpt-5-mini",
    output_type=SearchResult,
)
```

**Step 4: 테스트 실행 (통과 확인)**

```bash
pytest tests/test_agent.py -v
```

Expected: PASS

**Step 5: 커밋**

```bash
git add src/agents/search/agent.py tests/test_agent.py
git commit -m "feat: define SearchAgent with instructions and tools"
```

---

## Task 10: CLI Runner 구현

**Files:**
- Create: `src/agents/search/runner.py`
- Create: `src/agents/search/__main__.py`

**Step 1: Runner 구현**

```python
# src/agents/search/runner.py
import json
import click
from pathlib import Path
from agents import Runner
from agents.search.agent import search_agent
from agents.search.schemas import SearchRequest, Constraints
from agents.search.tools.rag import set_artifacts_dir
from agents.search.clients.local_store import LocalStore


@click.command()
@click.option("--goal", required=True, help="연구 목표")
@click.option("--namespace", default="default", help="저장소 네임스페이스")
@click.option("--target-docs", default=12, help="목표 신규 문서 수")
@click.option("--max-candidates", default=80, help="최대 후보 수")
@click.option("--max-selected", default=20, help="최대 선정 수")
@click.option("--output", default=None, help="결과 저장 경로 (JSON)")
@click.option("--artifacts-dir", default="artifacts", help="아티팩트 저장 디렉토리")
def search(
    goal: str,
    namespace: str,
    target_docs: int,
    max_candidates: int,
    max_selected: int,
    output: str | None,
    artifacts_dir: str,
):
    """Search Agent 실행: 연구 목표에 맞는 논문 검색 및 저장"""

    # 아티팩트 디렉토리 설정
    artifacts_path = Path(artifacts_dir)
    set_artifacts_dir(artifacts_path)

    # 요청 생성
    request = SearchRequest(
        goal=goal,
        namespace=namespace,
        constraints=Constraints(
            target_new_docs=target_docs,
            max_candidates=max_candidates,
            max_selected=max_selected,
        ),
    )

    click.echo(f"Starting search for: {goal}")
    click.echo(f"Namespace: {namespace}, Target: {target_docs} docs")

    # Agent 실행
    result = Runner.run_sync(search_agent, request.model_dump_json())

    # 결과 출력
    output_data = result.final_output.model_dump()
    click.echo("\n=== Search Result ===")
    click.echo(f"Papers found: {len(output_data['selected_papers'])}")
    click.echo(f"New docs added: {output_data['ingest_summary']['new_docs_added']}")
    click.echo(f"Duplicates skipped: {output_data['ingest_summary']['duplicates_skipped']}")

    if output_data.get('errors'):
        click.echo(f"Errors: {len(output_data['errors'])}")

    # 결과 저장
    store = LocalStore(artifacts_dir=artifacts_path)
    result_path = store.save_result(namespace, result.final_output)
    click.echo(f"\nResult saved to: {result_path}")

    # 추가 출력 파일 (옵션)
    if output:
        output_path = Path(output)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(output_data, f, ensure_ascii=False, indent=2)
        click.echo(f"Also saved to: {output_path}")


def main():
    search()


if __name__ == "__main__":
    main()
```

**Step 2: __main__.py 작성**

```python
# src/agents/search/__main__.py
from agents.search.runner import main

if __name__ == "__main__":
    main()
```

**Step 3: __init__.py 업데이트**

```python
# src/agents/search/__init__.py
from agents.search.agent import search_agent
from agents.search.schemas import SearchRequest, SearchResult

__all__ = ["search_agent", "SearchRequest", "SearchResult"]
```

**Step 4: 커밋**

```bash
git add src/agents/search/runner.py src/agents/search/__main__.py src/agents/search/__init__.py
git commit -m "feat: add CLI runner for SearchAgent"
```

---

## Task 11: 통합 테스트

**Files:**
- Create: `tests/test_integration.py`

**Step 1: 통합 테스트 작성**

```python
# tests/test_integration.py
"""
통합 테스트: 실제 API 호출 포함 (CI에서는 skip)
로컬에서 OPENAI_API_KEY 설정 후 실행:
  pytest tests/test_integration.py -v --run-integration
"""
import pytest
import os
from pathlib import Path


# 통합 테스트 마커
def pytest_configure(config):
    config.addinivalue_line("markers", "integration: mark test as integration test")


@pytest.fixture
def has_api_key():
    return bool(os.getenv("OPENAI_API_KEY"))


@pytest.mark.integration
def test_full_search_flow(tmp_path, has_api_key):
    if not has_api_key:
        pytest.skip("OPENAI_API_KEY not set")

    from agents.search.tools.rag import set_artifacts_dir
    from agents.search.tools.search import search_sources
    from agents.search.tools.rag import rag_ingest_candidates
    from agents.search.schemas import IngestPolicy

    set_artifacts_dir(tmp_path)

    # 1. 검색
    candidates = search_sources(
        queries=["graph neural network"],
        sources=["arxiv"],
        max_results=5,
    )

    assert len(candidates) > 0
    assert candidates[0].arxiv_id

    # 2. 인제스트
    result = rag_ingest_candidates(
        namespace="integration_test",
        candidates=candidates,
        ingest_policy=IngestPolicy(),
    )

    assert result.new_docs_added == len(candidates)

    # 3. 파일 확인
    papers_file = tmp_path / "integration_test_papers.json"
    assert papers_file.exists()
```

**Step 2: pytest.ini 설정**

```ini
# pytest.ini (이미 pyproject.toml에 있으면 생략)
[pytest]
markers =
    integration: mark test as integration test (requires API keys)
```

**Step 3: 커밋**

```bash
git add tests/test_integration.py
git commit -m "test: add integration test for full search flow"
```

---

## Task 12: 문서 및 최종 정리

**Files:**
- Update: `README.md`
- Update: `.gitignore`

**Step 1: README 업데이트**

```markdown
# Research Navigator - Search Agent

> 연구자를 위한 자율형 리서치 에이전트

## Quick Start

```bash
# 환경 설정
cp .env.example .env
# OPENAI_API_KEY 입력

# 의존성 설치
pip install -e ".[dev]"

# 실행
python -m search_agent --goal "Graph RAG for scientific papers"
```

## CLI 옵션

```bash
python -m search_agent \
  --goal "LLM agents for code generation" \
  --namespace demo \
  --target-docs 20 \
  --output artifacts/result.json
```

## 테스트

```bash
# 단위 테스트
pytest tests/ -v

# 통합 테스트 (API 키 필요)
pytest tests/test_integration.py -v
```

## 문서

- [설계 문서](docs/plans/2026-01-20-search-agent-design.md)
- [구현 계획](docs/plans/2026-01-20-search-agent-impl.md)
```

**Step 2: .gitignore에 artifacts 추가**

```bash
echo "artifacts/" >> .gitignore
echo "*.pyc" >> .gitignore
echo ".env" >> .gitignore
```

**Step 3: 최종 커밋**

```bash
git add README.md .gitignore
git commit -m "docs: update README and gitignore for search-agent"
```

---

## 구현 완료 체크리스트

- [ ] Task 1: 프로젝트 구조 생성
- [ ] Task 2: Pydantic 스키마 정의
- [ ] Task 3: Config 모듈 구현
- [ ] Task 4: arXiv 클라이언트 구현
- [ ] Task 5: 로컬 저장소 구현
- [ ] Task 6: Ranking & Dedup 로직 구현
- [ ] Task 7: Tools 구현 (search_sources)
- [ ] Task 8: Tools 구현 (RAG - 모킹)
- [ ] Task 9: Agent 정의
- [ ] Task 10: CLI Runner 구현
- [ ] Task 11: 통합 테스트
- [ ] Task 12: 문서 및 최종 정리
