# RAG Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Qdrant 기반 RAG 시스템을 Search/Verifier Agent에 통합하여 논문 검색 및 evidence 조회 기능 구현

**Architecture:** OpenAI text-embedding-3-small로 논문 abstract를 벡터화하고 Qdrant에 저장. Search Agent가 ingestion 시 벡터 저장, Verifier Agent가 claim 검증 시 source_id 조회 + semantic fallback으로 evidence 검색.

**Tech Stack:** qdrant-client, OpenAI Embeddings API, Pydantic

---

## Task 1: 의존성 추가

**Files:**
- Modify: `requirements.txt`

**Step 1: qdrant-client 추가**

```txt
openai-agents
arxiv
qdrant-client>=1.12.0
```

**Step 2: 설치 확인**

Run: `pip install -r requirements.txt`
Expected: Successfully installed qdrant-client

**Step 3: Commit**

```bash
git add requirements.txt
git commit -m "deps: add qdrant-client for RAG"
```

---

## Task 2: RAG 설정 추가

**Files:**
- Modify: `src/shared/config.py`

**Step 1: Settings 클래스 확장**

```python
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    openai_api_key: str
    openai_model: str = "gpt-5-mini"
    artifacts_dir: str = "artifacts"

    # RAG settings
    qdrant_url: str = "http://localhost:6333"
    qdrant_collection: str = "papers"
    embedding_model: str = "text-embedding-3-small"
    embedding_dim: int = 1536


def get_settings() -> Settings:
    return Settings()
```

**Step 2: Commit**

```bash
git add src/shared/config.py
git commit -m "feat: add RAG settings to config"
```

---

## Task 3: RAG 스키마 정의

**Files:**
- Create: `src/shared/rag/__init__.py`
- Create: `src/shared/rag/schemas.py`

**Step 1: 패키지 init 생성**

```python
"""RAG (Retrieval-Augmented Generation) infrastructure."""

from .schemas import VectorDocument, SearchResult

__all__ = ["VectorDocument", "SearchResult"]
```

**Step 2: 스키마 정의**

```python
"""RAG schemas for vector storage and retrieval."""

from pydantic import BaseModel


class VectorDocument(BaseModel):
    """Document stored in vector database."""

    arxiv_id: str
    title: str
    abstract: str
    url: str
    authors: list[str] = []
    year: int = 0


class SearchResult(BaseModel):
    """Result from vector similarity search."""

    arxiv_id: str
    title: str
    abstract: str
    url: str
    score: float
```

**Step 3: Commit**

```bash
git add src/shared/rag/
git commit -m "feat: add RAG schemas"
```

---

## Task 4: Embedding 모듈 구현

**Files:**
- Create: `src/shared/rag/embeddings.py`
- Create: `tests/shared/rag/test_embeddings.py`

**Step 1: 테스트 작성**

```python
"""Tests for embedding module."""

import pytest
from unittest.mock import patch, MagicMock

from shared.rag.embeddings import get_embedding, get_embeddings


class TestGetEmbedding:
    """Tests for get_embedding function."""

    @patch("shared.rag.embeddings.OpenAI")
    def test_returns_embedding_vector(self, mock_openai_class):
        """Should return embedding vector from OpenAI API."""
        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client
        mock_client.embeddings.create.return_value.data = [
            MagicMock(embedding=[0.1, 0.2, 0.3])
        ]

        result = get_embedding("test text")

        assert result == [0.1, 0.2, 0.3]
        mock_client.embeddings.create.assert_called_once()

    @patch("shared.rag.embeddings.OpenAI")
    def test_uses_configured_model(self, mock_openai_class):
        """Should use embedding model from settings."""
        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client
        mock_client.embeddings.create.return_value.data = [
            MagicMock(embedding=[0.1])
        ]

        get_embedding("test", model="text-embedding-3-small")

        call_args = mock_client.embeddings.create.call_args
        assert call_args.kwargs["model"] == "text-embedding-3-small"


class TestGetEmbeddings:
    """Tests for batch embedding function."""

    @patch("shared.rag.embeddings.OpenAI")
    def test_batch_returns_multiple_embeddings(self, mock_openai_class):
        """Should return embeddings for multiple texts."""
        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client
        mock_client.embeddings.create.return_value.data = [
            MagicMock(embedding=[0.1, 0.2]),
            MagicMock(embedding=[0.3, 0.4]),
        ]

        results = get_embeddings(["text1", "text2"])

        assert len(results) == 2
        assert results[0] == [0.1, 0.2]
        assert results[1] == [0.3, 0.4]
```

**Step 2: 테스트 실행 (실패 확인)**

Run: `PYTHONPATH=src pytest tests/shared/rag/test_embeddings.py -v`
Expected: FAIL (module not found)

**Step 3: 구현**

```python
"""OpenAI embedding utilities."""

from openai import OpenAI

from shared.config import get_settings

_client: OpenAI | None = None


def _get_client() -> OpenAI:
    """Get or create OpenAI client."""
    global _client
    if _client is None:
        settings = get_settings()
        _client = OpenAI(api_key=settings.openai_api_key)
    return _client


def get_embedding(
    text: str,
    model: str | None = None,
) -> list[float]:
    """Get embedding vector for text.

    Args:
        text: Text to embed
        model: Embedding model (default: from settings)

    Returns:
        Embedding vector
    """
    settings = get_settings()
    client = _get_client()
    response = client.embeddings.create(
        input=text,
        model=model or settings.embedding_model,
    )
    return response.data[0].embedding


def get_embeddings(
    texts: list[str],
    model: str | None = None,
) -> list[list[float]]:
    """Get embeddings for multiple texts (batch).

    Args:
        texts: Texts to embed
        model: Embedding model (default: from settings)

    Returns:
        List of embedding vectors
    """
    settings = get_settings()
    client = _get_client()
    response = client.embeddings.create(
        input=texts,
        model=model or settings.embedding_model,
    )
    return [d.embedding for d in response.data]
```

**Step 4: 테스트 디렉토리 생성 및 init 파일**

```bash
mkdir -p tests/shared/rag
touch tests/shared/__init__.py
touch tests/shared/rag/__init__.py
```

**Step 5: 테스트 실행 (통과 확인)**

Run: `PYTHONPATH=src pytest tests/shared/rag/test_embeddings.py -v`
Expected: PASS

**Step 6: Commit**

```bash
git add src/shared/rag/embeddings.py tests/shared/
git commit -m "feat: add OpenAI embedding module with tests"
```

---

## Task 5: Qdrant 클라이언트 구현

**Files:**
- Create: `src/shared/rag/client.py`
- Create: `tests/shared/rag/test_client.py`

**Step 1: 테스트 작성**

```python
"""Tests for Qdrant RAG client."""

import pytest
from unittest.mock import patch, MagicMock

from shared.rag.client import QdrantRAG
from shared.rag.schemas import VectorDocument, SearchResult


class TestQdrantRAG:
    """Tests for QdrantRAG class."""

    @patch("shared.rag.client.QdrantClient")
    def test_upsert_stores_document(self, mock_qdrant_class):
        """Should store document with embedding in Qdrant."""
        mock_client = MagicMock()
        mock_qdrant_class.return_value = mock_client

        rag = QdrantRAG(url="http://localhost:6333", collection="test")
        doc = VectorDocument(
            arxiv_id="2401.00001",
            title="Test Paper",
            abstract="This is a test abstract.",
            url="https://arxiv.org/abs/2401.00001",
        )
        embedding = [0.1] * 1536

        rag.upsert(doc, embedding)

        mock_client.upsert.assert_called_once()
        call_args = mock_client.upsert.call_args
        assert call_args.kwargs["collection_name"] == "test"

    @patch("shared.rag.client.QdrantClient")
    def test_get_by_id_returns_document(self, mock_qdrant_class):
        """Should retrieve document by arxiv_id."""
        mock_client = MagicMock()
        mock_qdrant_class.return_value = mock_client
        mock_client.retrieve.return_value = [
            MagicMock(payload={
                "arxiv_id": "2401.00001",
                "title": "Test Paper",
                "abstract": "Abstract text",
                "url": "https://arxiv.org/abs/2401.00001",
                "authors": [],
                "year": 2024,
            })
        ]

        rag = QdrantRAG(url="http://localhost:6333", collection="test")
        result = rag.get_by_id("2401.00001")

        assert result is not None
        assert result.arxiv_id == "2401.00001"

    @patch("shared.rag.client.QdrantClient")
    def test_get_by_id_returns_none_if_not_found(self, mock_qdrant_class):
        """Should return None if document not found."""
        mock_client = MagicMock()
        mock_qdrant_class.return_value = mock_client
        mock_client.retrieve.return_value = []

        rag = QdrantRAG(url="http://localhost:6333", collection="test")
        result = rag.get_by_id("nonexistent")

        assert result is None

    @patch("shared.rag.client.QdrantClient")
    def test_search_returns_similar_documents(self, mock_qdrant_class):
        """Should return similar documents by embedding."""
        mock_client = MagicMock()
        mock_qdrant_class.return_value = mock_client
        mock_client.search.return_value = [
            MagicMock(
                score=0.95,
                payload={
                    "arxiv_id": "2401.00001",
                    "title": "Similar Paper",
                    "abstract": "Similar abstract",
                    "url": "https://arxiv.org/abs/2401.00001",
                }
            )
        ]

        rag = QdrantRAG(url="http://localhost:6333", collection="test")
        results = rag.search([0.1] * 1536, top_k=5)

        assert len(results) == 1
        assert results[0].arxiv_id == "2401.00001"
        assert results[0].score == 0.95

    @patch("shared.rag.client.QdrantClient")
    def test_exists_returns_true_if_found(self, mock_qdrant_class):
        """Should return True if document exists."""
        mock_client = MagicMock()
        mock_qdrant_class.return_value = mock_client
        mock_client.retrieve.return_value = [MagicMock()]

        rag = QdrantRAG(url="http://localhost:6333", collection="test")
        assert rag.exists("2401.00001") is True

    @patch("shared.rag.client.QdrantClient")
    def test_exists_returns_false_if_not_found(self, mock_qdrant_class):
        """Should return False if document doesn't exist."""
        mock_client = MagicMock()
        mock_qdrant_class.return_value = mock_client
        mock_client.retrieve.return_value = []

        rag = QdrantRAG(url="http://localhost:6333", collection="test")
        assert rag.exists("nonexistent") is False
```

**Step 2: 테스트 실행 (실패 확인)**

Run: `PYTHONPATH=src pytest tests/shared/rag/test_client.py -v`
Expected: FAIL (module not found)

**Step 3: 구현**

```python
"""Qdrant vector database client for RAG."""

import hashlib

from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct

from shared.rag.schemas import VectorDocument, SearchResult


def _arxiv_id_to_point_id(arxiv_id: str) -> int:
    """Convert arxiv_id to numeric point ID for Qdrant."""
    hash_bytes = hashlib.md5(arxiv_id.encode()).digest()
    return int.from_bytes(hash_bytes[:8], byteorder="big") & 0x7FFFFFFFFFFFFFFF


class QdrantRAG:
    """Qdrant client for RAG operations."""

    def __init__(self, url: str, collection: str):
        """Initialize Qdrant client.

        Args:
            url: Qdrant server URL
            collection: Collection name
        """
        self.client = QdrantClient(url=url)
        self.collection = collection

    def upsert(self, doc: VectorDocument, embedding: list[float]) -> None:
        """Store document with embedding.

        Args:
            doc: Document to store
            embedding: Document embedding vector
        """
        point_id = _arxiv_id_to_point_id(doc.arxiv_id)
        point = PointStruct(
            id=point_id,
            vector=embedding,
            payload=doc.model_dump(),
        )
        self.client.upsert(
            collection_name=self.collection,
            points=[point],
        )

    def get_by_id(self, arxiv_id: str) -> VectorDocument | None:
        """Get document by arxiv_id.

        Args:
            arxiv_id: ArXiv paper ID

        Returns:
            Document if found, None otherwise
        """
        point_id = _arxiv_id_to_point_id(arxiv_id)
        results = self.client.retrieve(
            collection_name=self.collection,
            ids=[point_id],
            with_payload=True,
        )
        if not results:
            return None
        payload = results[0].payload
        return VectorDocument(**payload)

    def get_by_ids(self, arxiv_ids: list[str]) -> list[VectorDocument]:
        """Get multiple documents by arxiv_ids.

        Args:
            arxiv_ids: List of ArXiv paper IDs

        Returns:
            List of found documents
        """
        if not arxiv_ids:
            return []
        point_ids = [_arxiv_id_to_point_id(aid) for aid in arxiv_ids]
        results = self.client.retrieve(
            collection_name=self.collection,
            ids=point_ids,
            with_payload=True,
        )
        return [VectorDocument(**r.payload) for r in results if r.payload]

    def search(
        self,
        query_embedding: list[float],
        top_k: int = 5,
        score_threshold: float = 0.5,
    ) -> list[SearchResult]:
        """Search for similar documents.

        Args:
            query_embedding: Query vector
            top_k: Maximum results
            score_threshold: Minimum similarity score

        Returns:
            List of similar documents with scores
        """
        results = self.client.search(
            collection_name=self.collection,
            query_vector=query_embedding,
            limit=top_k,
            score_threshold=score_threshold,
        )
        return [
            SearchResult(
                arxiv_id=r.payload["arxiv_id"],
                title=r.payload["title"],
                abstract=r.payload["abstract"],
                url=r.payload["url"],
                score=r.score,
            )
            for r in results
            if r.payload
        ]

    def exists(self, arxiv_id: str) -> bool:
        """Check if document exists.

        Args:
            arxiv_id: ArXiv paper ID

        Returns:
            True if exists
        """
        point_id = _arxiv_id_to_point_id(arxiv_id)
        results = self.client.retrieve(
            collection_name=self.collection,
            ids=[point_id],
        )
        return len(results) > 0
```

**Step 4: __init__.py 업데이트**

```python
"""RAG (Retrieval-Augmented Generation) infrastructure."""

from .schemas import VectorDocument, SearchResult
from .client import QdrantRAG
from .embeddings import get_embedding, get_embeddings

__all__ = [
    "VectorDocument",
    "SearchResult",
    "QdrantRAG",
    "get_embedding",
    "get_embeddings",
]
```

**Step 5: 테스트 실행 (통과 확인)**

Run: `PYTHONPATH=src pytest tests/shared/rag/test_client.py -v`
Expected: PASS

**Step 6: Commit**

```bash
git add src/shared/rag/ tests/shared/rag/
git commit -m "feat: add Qdrant RAG client with tests"
```

---

## Task 6: Search Agent RAG 도구 수정

**Files:**
- Modify: `src/agent/search/tools/rag.py`
- Modify: `tests/test_rag_tools.py` (if exists, or create)

**Step 1: 테스트 수정/추가**

```python
"""Tests for RAG tools with Qdrant integration."""

import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path

from agent.search.schemas import Candidate, IngestPolicy
from agent.search.tools.rag import (
    _rag_ingest_candidates_impl,
    _rag_preview_impl,
    set_artifacts_dir,
)


class TestRagIngestWithQdrant:
    """Tests for rag_ingest_candidates with Qdrant."""

    @patch("agent.search.tools.rag.get_qdrant_client")
    @patch("agent.search.tools.rag.get_embedding")
    def test_stores_in_qdrant(self, mock_embedding, mock_qdrant, tmp_path):
        """Should store papers in Qdrant with embeddings."""
        set_artifacts_dir(tmp_path)

        mock_embedding.return_value = [0.1] * 1536
        mock_rag = MagicMock()
        mock_qdrant.return_value = mock_rag
        mock_rag.exists.return_value = False

        candidates = [
            Candidate(
                arxiv_id="2401.00001",
                title="Test Paper",
                year=2024,
                authors=["Author"],
                abstract="Test abstract",
                url="https://arxiv.org/abs/2401.00001",
            )
        ]

        result = _rag_ingest_candidates_impl(
            namespace="test",
            candidates=candidates,
            ingest_policy=IngestPolicy(),
        )

        assert result.new_docs_added == 1
        mock_rag.upsert.assert_called_once()


class TestRagPreviewWithQdrant:
    """Tests for rag_preview with Qdrant."""

    @patch("agent.search.tools.rag.get_qdrant_client")
    @patch("agent.search.tools.rag.get_embedding")
    def test_searches_qdrant(self, mock_embedding, mock_qdrant):
        """Should search Qdrant for similar papers."""
        mock_embedding.return_value = [0.1] * 1536
        mock_rag = MagicMock()
        mock_qdrant.return_value = mock_rag
        mock_rag.search.return_value = [
            MagicMock(
                arxiv_id="2401.00001",
                title="Found Paper",
                abstract="Found abstract",
                url="https://arxiv.org/abs/2401.00001",
                score=0.9,
            )
        ]

        result = _rag_preview_impl(
            namespace="test",
            query="test query",
            top_k=5,
        )

        assert len(result) == 1
        mock_embedding.assert_called_with("test query")
        mock_rag.search.assert_called_once()
```

**Step 2: rag.py 수정**

```python
"""RAG tools for ingesting and previewing documents in knowledge base."""

from pathlib import Path

from agents import function_tool

from agent.search.clients.local_store import LocalStore
from agent.search.schemas import Candidate, IngestPolicy, IngestSummary, PreviewSnippet
from shared.config import get_settings
from shared.rag import QdrantRAG, VectorDocument, get_embedding

_store: LocalStore | None = None
_qdrant: QdrantRAG | None = None


def get_store() -> LocalStore:
    """Get the global LocalStore instance, creating if needed."""
    global _store
    if _store is None:
        _store = LocalStore()
    return _store


def get_qdrant_client() -> QdrantRAG:
    """Get the global Qdrant client, creating if needed."""
    global _qdrant
    if _qdrant is None:
        settings = get_settings()
        _qdrant = QdrantRAG(
            url=settings.qdrant_url,
            collection=settings.qdrant_collection,
        )
    return _qdrant


def set_artifacts_dir(path: Path) -> None:
    """Set artifacts directory for testing purposes."""
    global _store
    _store = LocalStore(artifacts_dir=path)


def _rag_ingest_candidates_impl(
    namespace: str,
    candidates: list[Candidate],
    ingest_policy: IngestPolicy,
) -> IngestSummary:
    """
    Store selected documents in the knowledge base.

    Stores to both local JSON and Qdrant vector database.

    Args:
        namespace: The namespace to store documents under.
        candidates: List of candidate papers to ingest.
        ingest_policy: Policy controlling how documents are ingested.
    """
    store = get_store()
    qdrant = get_qdrant_client()

    # Check existing in local store
    existing_ids = store.load_existing_ids(namespace)
    seen = set(existing_ids)

    new_candidates: list[Candidate] = []
    duplicates = 0

    for c in candidates:
        if c.arxiv_id in seen:
            duplicates += 1
            continue
        # Also check Qdrant
        if qdrant.exists(c.arxiv_id):
            duplicates += 1
            seen.add(c.arxiv_id)
            continue
        seen.add(c.arxiv_id)
        new_candidates.append(c)

    # Store in local JSON
    new_docs_added = store.append_papers(namespace, new_candidates)

    # Store in Qdrant with embeddings
    for c in new_candidates:
        text = f"{c.title}\n\n{c.abstract}"
        embedding = get_embedding(text)
        doc = VectorDocument(
            arxiv_id=c.arxiv_id,
            title=c.title,
            abstract=c.abstract,
            url=c.url,
            authors=c.authors,
            year=c.year,
        )
        qdrant.upsert(doc, embedding)

    return IngestSummary(
        new_docs_added=new_docs_added,
        duplicates_skipped=duplicates,
        chunks_added=0,
        index_size=store.count_papers(namespace),
    )


def _rag_preview_impl(
    namespace: str,
    query: str,
    top_k: int = 5,
) -> list[PreviewSnippet]:
    """
    Search for relevant snippets from stored documents.

    Uses Qdrant vector search.

    Args:
        namespace: The namespace to search in.
        query: The search query.
        top_k: Maximum number of snippets to return.
    """
    qdrant = get_qdrant_client()
    query_embedding = get_embedding(query)
    results = qdrant.search(query_embedding, top_k=top_k)

    return [
        PreviewSnippet(
            arxiv_id=r.arxiv_id,
            chunk_id=f"{r.arxiv_id}_abstract",
            score=r.score,
            snippet=r.abstract[:500],
        )
        for r in results
    ]


# Wrap the implementation functions as FunctionTools for use with Agent
rag_ingest_candidates = function_tool(_rag_ingest_candidates_impl)
rag_preview = function_tool(_rag_preview_impl)
```

**Step 3: 테스트 실행**

Run: `PYTHONPATH=src pytest tests/test_rag_tools.py -v`
Expected: PASS

**Step 4: Commit**

```bash
git add src/agent/search/tools/rag.py tests/test_rag_tools.py
git commit -m "feat: integrate Qdrant into Search Agent RAG tools"
```

---

## Task 7: Verifier RAG 도구 추가

**Files:**
- Create: `src/agent/verify/tools/rag.py`
- Create: `tests/verifier/test_rag_tools.py`

**Step 1: 테스트 작성**

```python
"""Tests for Verifier RAG tools."""

import pytest
from unittest.mock import patch, MagicMock

from agent.verify.tools.rag import _rag_get_evidence_impl


class TestRagGetEvidence:
    """Tests for rag_get_evidence tool."""

    @patch("agent.verify.tools.rag.get_qdrant_client")
    @patch("agent.verify.tools.rag.get_embedding")
    def test_returns_by_source_ids_first(self, mock_embedding, mock_qdrant):
        """Should return documents by source_ids first."""
        mock_rag = MagicMock()
        mock_qdrant.return_value = mock_rag
        mock_rag.get_by_ids.return_value = [
            MagicMock(
                arxiv_id="2401.00001",
                title="Paper 1",
                abstract="Abstract 1",
                url="url1",
            ),
            MagicMock(
                arxiv_id="2401.00002",
                title="Paper 2",
                abstract="Abstract 2",
                url="url2",
            ),
        ]

        result = _rag_get_evidence_impl(
            claim_text="test claim",
            source_ids=["2401.00001", "2401.00002"],
            top_k=3,
        )

        assert len(result) == 2
        mock_embedding.assert_not_called()  # No need for semantic search

    @patch("agent.verify.tools.rag.get_qdrant_client")
    @patch("agent.verify.tools.rag.get_embedding")
    def test_falls_back_to_semantic_search(self, mock_embedding, mock_qdrant):
        """Should fallback to semantic search if source_ids not enough."""
        mock_embedding.return_value = [0.1] * 1536
        mock_rag = MagicMock()
        mock_qdrant.return_value = mock_rag
        mock_rag.get_by_ids.return_value = [
            MagicMock(arxiv_id="2401.00001", title="P1", abstract="A1", url="u1"),
        ]
        mock_rag.search.return_value = [
            MagicMock(arxiv_id="2401.00099", title="P2", abstract="A2", url="u2", score=0.8),
        ]

        result = _rag_get_evidence_impl(
            claim_text="test claim",
            source_ids=["2401.00001"],
            top_k=3,
        )

        assert len(result) == 2
        mock_embedding.assert_called_with("test claim")
        mock_rag.search.assert_called_once()

    @patch("agent.verify.tools.rag.get_qdrant_client")
    @patch("agent.verify.tools.rag.get_embedding")
    def test_semantic_only_when_no_source_ids(self, mock_embedding, mock_qdrant):
        """Should use semantic search only when no source_ids."""
        mock_embedding.return_value = [0.1] * 1536
        mock_rag = MagicMock()
        mock_qdrant.return_value = mock_rag
        mock_rag.get_by_ids.return_value = []
        mock_rag.search.return_value = [
            MagicMock(arxiv_id="2401.00001", title="P1", abstract="A1", url="u1", score=0.9),
        ]

        result = _rag_get_evidence_impl(
            claim_text="test claim",
            source_ids=[],
            top_k=3,
        )

        assert len(result) == 1
        mock_embedding.assert_called_with("test claim")
```

**Step 2: 테스트 실행 (실패 확인)**

Run: `PYTHONPATH=src pytest tests/verifier/test_rag_tools.py -v`
Expected: FAIL

**Step 3: 구현**

```python
"""RAG tools for Verifier agent."""

from dataclasses import dataclass

from agents import function_tool

from shared.config import get_settings
from shared.rag import QdrantRAG, get_embedding

_qdrant: QdrantRAG | None = None


def get_qdrant_client() -> QdrantRAG:
    """Get the global Qdrant client."""
    global _qdrant
    if _qdrant is None:
        settings = get_settings()
        _qdrant = QdrantRAG(
            url=settings.qdrant_url,
            collection=settings.qdrant_collection,
        )
    return _qdrant


@dataclass
class EvidenceResult:
    """Evidence retrieved from RAG."""

    arxiv_id: str
    title: str
    abstract: str
    url: str
    score: float = 1.0


def _rag_get_evidence_impl(
    claim_text: str,
    source_ids: list[str],
    top_k: int = 3,
) -> list[EvidenceResult]:
    """
    Get evidence for a claim from the knowledge base.

    Strategy: First try source_ids, then semantic search fallback.

    Args:
        claim_text: The claim to find evidence for.
        source_ids: Known source IDs to look up first.
        top_k: Maximum results to return.
    """
    qdrant = get_qdrant_client()
    results: list[EvidenceResult] = []
    found_ids: set[str] = set()

    # Step 1: Get by source_ids
    if source_ids:
        docs = qdrant.get_by_ids(source_ids)
        for doc in docs:
            results.append(EvidenceResult(
                arxiv_id=doc.arxiv_id,
                title=doc.title,
                abstract=doc.abstract,
                url=doc.url,
                score=1.0,
            ))
            found_ids.add(doc.arxiv_id)

    # Step 2: Semantic search fallback if not enough
    if len(results) < top_k:
        remaining = top_k - len(results)
        query_embedding = get_embedding(claim_text)
        search_results = qdrant.search(query_embedding, top_k=remaining + len(found_ids))

        for sr in search_results:
            if sr.arxiv_id not in found_ids and len(results) < top_k:
                results.append(EvidenceResult(
                    arxiv_id=sr.arxiv_id,
                    title=sr.title,
                    abstract=sr.abstract,
                    url=sr.url,
                    score=sr.score,
                ))
                found_ids.add(sr.arxiv_id)

    return results


rag_get_evidence = function_tool(_rag_get_evidence_impl)
```

**Step 4: 테스트 실행 (통과 확인)**

Run: `PYTHONPATH=src pytest tests/verifier/test_rag_tools.py -v`
Expected: PASS

**Step 5: Verifier agent에 도구 등록 (확인 필요)**

Check `src/agent/verify/agent.py` for tool registration.

**Step 6: Commit**

```bash
git add src/agent/verify/tools/rag.py tests/verifier/test_rag_tools.py
git commit -m "feat: add rag_get_evidence tool for Verifier agent"
```

---

## Task 8: Orchestrator 수정 - Writer context에 sources 추가

**Files:**
- Modify: `main.py:491-498`

**Step 1: 현재 코드 확인**

Lines 491-498:
```python
writer_context = json.dumps({
    "clarifier": clarifier_data,
    "plan": asdict(plan_out),
    "supported_claims": [asdict(v) for v in supported],
    "weak_claims": [asdict(v) for v in weak],
    "total_sources": len(accumulated_sources),
    "loops_used": loops_used,
})
```

**Step 2: 수정**

```python
writer_context = json.dumps({
    "clarifier": clarifier_data,
    "plan": asdict(plan_out),
    "supported_claims": [asdict(v) for v in supported],
    "weak_claims": [asdict(v) for v in weak],
    "sources": [asdict(s) for s in accumulated_sources],
    "loops_used": loops_used,
})
```

**Step 3: 테스트 실행**

Run: `PYTHONPATH=src pytest tests/test_orchestrator.py -v`
Expected: PASS

**Step 4: Commit**

```bash
git add main.py
git commit -m "feat: pass full sources to Writer context"
```

---

## Task 9: Collection 초기화 스크립트

**Files:**
- Create: `scripts/init_qdrant.py`

**Step 1: 스크립트 작성**

```python
#!/usr/bin/env python3
"""Initialize Qdrant collection for RAG."""

import sys
from qdrant_client import QdrantClient
from qdrant_client.models import VectorParams, Distance

from shared.config import get_settings


def init_collection():
    """Create papers collection in Qdrant."""
    settings = get_settings()

    client = QdrantClient(url=settings.qdrant_url)

    # Check if collection exists
    collections = client.get_collections().collections
    if any(c.name == settings.qdrant_collection for c in collections):
        print(f"Collection '{settings.qdrant_collection}' already exists.")
        return

    # Create collection
    client.create_collection(
        collection_name=settings.qdrant_collection,
        vectors_config=VectorParams(
            size=settings.embedding_dim,
            distance=Distance.COSINE,
        ),
    )
    print(f"Created collection '{settings.qdrant_collection}'")


if __name__ == "__main__":
    sys.path.insert(0, "src")
    init_collection()
```

**Step 2: 실행 테스트**

Run: `docker compose up -d qdrant && sleep 5 && PYTHONPATH=src python scripts/init_qdrant.py`
Expected: Created collection 'papers'

**Step 3: Commit**

```bash
git add scripts/init_qdrant.py
git commit -m "feat: add Qdrant collection init script"
```

---

## Task 10: 통합 테스트

**Files:**
- Create: `tests/integration/test_rag_e2e.py`

**Step 1: 통합 테스트 작성**

```python
"""End-to-end RAG integration test (requires running Qdrant)."""

import pytest
import os

# Skip if no Qdrant available
pytestmark = pytest.mark.skipif(
    os.getenv("SKIP_INTEGRATION") == "1",
    reason="Integration tests disabled",
)


class TestRAGIntegration:
    """Integration tests for RAG pipeline."""

    @pytest.fixture
    def setup_env(self, monkeypatch):
        """Set up environment for tests."""
        monkeypatch.setenv("QDRANT_URL", "http://localhost:6333")
        monkeypatch.setenv("QDRANT_COLLECTION_NAME", "test_papers")
        monkeypatch.setenv("OPENAI_API_KEY", os.getenv("OPENAI_API_KEY", "test"))

    def test_ingest_and_search_flow(self, setup_env):
        """Test complete ingest → search flow."""
        # This test requires:
        # 1. Running Qdrant (docker compose up -d qdrant)
        # 2. Valid OPENAI_API_KEY

        from agent.search.schemas import Candidate, IngestPolicy
        from agent.search.tools.rag import _rag_ingest_candidates_impl, _rag_preview_impl

        # Ingest a paper
        candidates = [
            Candidate(
                arxiv_id="test.00001",
                title="Graph Neural Networks for RAG Systems",
                year=2024,
                authors=["Test Author"],
                abstract="This paper explores graph neural networks for retrieval augmented generation.",
                url="https://arxiv.org/abs/test.00001",
            )
        ]

        result = _rag_ingest_candidates_impl(
            namespace="test",
            candidates=candidates,
            ingest_policy=IngestPolicy(),
        )

        assert result.new_docs_added == 1

        # Search for it
        snippets = _rag_preview_impl(
            namespace="test",
            query="graph neural network RAG",
            top_k=5,
        )

        assert len(snippets) >= 1
        assert any("test.00001" in s.arxiv_id for s in snippets)
```

**Step 2: 테스트 실행 (Docker + API key 필요)**

Run: `PYTHONPATH=src pytest tests/integration/test_rag_e2e.py -v`
Expected: PASS (or SKIP if no environment)

**Step 3: Commit**

```bash
mkdir -p tests/integration
git add tests/integration/
git commit -m "test: add RAG integration tests"
```

---

## Task 11: README 업데이트

**Files:**
- Modify: `README.md` or `docker/README.md`

**Step 1: RAG 설정 문서 추가**

Add section to docker/README.md:

```markdown
## RAG Setup

### 1. Start Infrastructure

```bash
docker compose up -d
```

### 2. Initialize Qdrant Collection

```bash
PYTHONPATH=src python scripts/init_qdrant.py
```

### 3. Verify

```bash
curl http://localhost:6333/collections/papers
```
```

**Step 2: Commit**

```bash
git add docker/README.md
git commit -m "docs: add RAG setup instructions"
```

---

## Summary

| Task | Description | Files |
|------|-------------|-------|
| 1 | 의존성 추가 | requirements.txt |
| 2 | RAG 설정 | src/shared/config.py |
| 3 | RAG 스키마 | src/shared/rag/ |
| 4 | Embedding 모듈 | src/shared/rag/embeddings.py |
| 5 | Qdrant 클라이언트 | src/shared/rag/client.py |
| 6 | Search Agent RAG | src/agent/search/tools/rag.py |
| 7 | Verifier RAG | src/agent/verify/tools/rag.py |
| 8 | Orchestrator 수정 | main.py |
| 9 | Init 스크립트 | scripts/init_qdrant.py |
| 10 | 통합 테스트 | tests/integration/ |
| 11 | 문서 업데이트 | docker/README.md |
