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


def reset_qdrant_client() -> None:
    """Reset Qdrant client for testing purposes."""
    global _qdrant
    _qdrant = None


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
