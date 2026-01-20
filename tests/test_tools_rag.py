"""Tests for RAG tools - rag_ingest_candidates and rag_preview."""

import json
import pytest

from agents.search.schemas import Candidate, IngestPolicy, IngestSummary, PreviewSnippet
from agents.search.tools.rag import (
    _rag_ingest_candidates_impl,
    _rag_preview_impl,
    rag_ingest_candidates,
    rag_preview,
    set_artifacts_dir,
)


def make_candidate(arxiv_id: str, title: str = "Test Paper") -> Candidate:
    """Helper function to create a Candidate instance for testing."""
    return Candidate(
        arxiv_id=arxiv_id,
        title=title,
        year=2024,
        authors=["Test Author"],
        abstract="Test abstract",
        url=f"https://arxiv.org/abs/{arxiv_id}",
    )


class TestRagIngestCandidates:
    """Tests for rag_ingest_candidates tool."""

    def test_rag_ingest_candidates(self, tmp_path):
        """Should ingest new candidates and return summary."""
        set_artifacts_dir(tmp_path)

        candidates = [
            make_candidate("2301.00001", "Paper 1"),
            make_candidate("2301.00002", "Paper 2"),
        ]
        policy = IngestPolicy()

        # Call the underlying implementation function
        result = _rag_ingest_candidates_impl(
            namespace="test-ns",
            candidates=candidates,
            ingest_policy=policy,
        )

        assert isinstance(result, IngestSummary)
        assert result.new_docs_added == 2
        assert result.duplicates_skipped == 0
        assert result.chunks_added == 0  # Mocked - always 0
        assert result.index_size == 2

        # Verify papers were saved to disk
        papers_file = tmp_path / "test-ns_papers.json"
        assert papers_file.exists()
        with open(papers_file, encoding="utf-8") as f:
            saved_papers = json.load(f)
        assert len(saved_papers) == 2
        assert saved_papers[0]["arxiv_id"] == "2301.00001"
        assert saved_papers[1]["arxiv_id"] == "2301.00002"

    def test_rag_ingest_duplicates(self, tmp_path):
        """Should skip duplicate candidates based on arxiv_id."""
        set_artifacts_dir(tmp_path)

        # Pre-populate with existing paper
        papers_file = tmp_path / "test-ns_papers.json"
        existing = [make_candidate("2301.00001", "Existing Paper").model_dump()]
        papers_file.write_text(json.dumps(existing), encoding="utf-8")

        # Try to ingest with one duplicate and one new
        candidates = [
            make_candidate("2301.00001", "Duplicate Paper"),  # duplicate
            make_candidate("2301.00002", "New Paper"),  # new
        ]
        policy = IngestPolicy()

        result = _rag_ingest_candidates_impl(
            namespace="test-ns",
            candidates=candidates,
            ingest_policy=policy,
        )

        assert result.new_docs_added == 1
        assert result.duplicates_skipped == 1
        assert result.index_size == 2

        # Verify original paper unchanged
        with open(papers_file, encoding="utf-8") as f:
            saved_papers = json.load(f)
        assert len(saved_papers) == 2
        assert saved_papers[0]["title"] == "Existing Paper"
        assert saved_papers[1]["arxiv_id"] == "2301.00002"


class TestRagPreview:
    """Tests for rag_preview tool."""

    def test_rag_preview_returns_empty(self, tmp_path):
        """Should return empty list (mocked implementation)."""
        set_artifacts_dir(tmp_path)

        # Call the underlying implementation function
        result = _rag_preview_impl(
            namespace="test-ns",
            query="test query",
            top_k=5,
        )

        assert isinstance(result, list)
        assert len(result) == 0

    def test_rag_preview_with_custom_top_k(self, tmp_path):
        """Should accept custom top_k parameter (still returns empty for v1.0)."""
        set_artifacts_dir(tmp_path)

        result = _rag_preview_impl(
            namespace="test-ns",
            query="machine learning",
            top_k=10,
        )

        assert isinstance(result, list)
        assert len(result) == 0
