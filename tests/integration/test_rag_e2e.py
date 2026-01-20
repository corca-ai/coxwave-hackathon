"""End-to-end RAG integration test (requires running Qdrant)."""

import os

import pytest

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

    @pytest.mark.skipif(
        not os.getenv("OPENAI_API_KEY"),
        reason="OPENAI_API_KEY not set",
    )
    def test_ingest_and_search_flow(self, setup_env):
        """Test complete ingest -> search flow."""
        # This test requires:
        # 1. Running Qdrant (docker compose up -d qdrant)
        # 2. Valid OPENAI_API_KEY

        from agent.search.schemas import Candidate, IngestPolicy
        from agent.search.tools.rag import (
            _rag_ingest_candidates_impl,
            _rag_preview_impl,
            reset_qdrant_client,
        )

        # Reset client to pick up test env
        reset_qdrant_client()

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
