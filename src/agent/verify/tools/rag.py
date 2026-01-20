"""RAG tools for Verifier agent."""

import json
from dataclasses import dataclass
from pathlib import Path

from agents import function_tool

from shared.config import get_settings
from shared.rag import QdrantRAG, get_embedding

_artifacts_dir: Path = Path("artifacts")
_qdrant: QdrantRAG | None = None


def set_artifacts_dir(path: Path) -> None:
    """테스트용: artifacts 디렉토리 설정"""
    global _artifacts_dir
    _artifacts_dir = path


def get_artifacts_dir() -> Path:
    return _artifacts_dir


def get_qdrant_client() -> QdrantRAG:
    """Get the global Qdrant client."""
    global _qdrant
    if _qdrant is None:
        settings = get_settings()
        _qdrant = QdrantRAG(
            url=settings.qdrant_url,
            collection=settings.qdrant_collection,
            embedding_dim=settings.embedding_dim,
        )
    return _qdrant


def reset_qdrant_client() -> None:
    """Reset Qdrant client for testing purposes."""
    global _qdrant
    _qdrant = None


def _rag_get_chunk_impl(
    namespace: str,
    arxiv_id: str,
    chunk_id: str
) -> str | None:
    """실제 구현 로직 (테스트 가능)"""
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
    return _rag_get_chunk_impl(namespace, arxiv_id, chunk_id)


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
