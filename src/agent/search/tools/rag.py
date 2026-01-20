"""RAG tools for ingesting and previewing documents in knowledge base."""

from pathlib import Path

from agents import function_tool

from agent.search.clients.local_store import LocalStore
from agent.search.schemas import Candidate, IngestPolicy, IngestSummary, PreviewSnippet

_store: LocalStore | None = None


def get_store() -> LocalStore:
    """Get the global LocalStore instance, creating if needed."""
    global _store
    if _store is None:
        _store = LocalStore()
    return _store


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

    v1.0: Saves to local JSON. Vector indexing is mocked.

    Args:
        namespace: The namespace to store documents under.
        candidates: List of candidate papers to ingest.
        ingest_policy: Policy controlling how documents are ingested.
    """
    store = get_store()
    existing_ids = store.load_existing_ids(namespace)
    seen = set(existing_ids)
    new_candidates: list[Candidate] = []
    duplicates = 0
    for c in candidates:
        if c.arxiv_id in seen:
            duplicates += 1
            continue
        seen.add(c.arxiv_id)
        new_candidates.append(c)
    new_docs_added = store.append_papers(namespace, new_candidates)
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

    v1.0: Mocked - returns empty list.

    Args:
        namespace: The namespace to search in.
        query: The search query.
        top_k: Maximum number of snippets to return.
    """
    return []


# Wrap the implementation functions as FunctionTools for use with Agent
rag_ingest_candidates = function_tool(_rag_ingest_candidates_impl)
rag_preview = function_tool(_rag_preview_impl)
