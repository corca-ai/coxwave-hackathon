"""Tests for search_sources tool."""

from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from agents.search.schemas import Candidate
from agents.search.tools.search import _search_sources_impl, search_sources


def create_mock_candidate(
    arxiv_id: str,
    title: str,
    year: int = 2024,
    abstract: str = "Test abstract",
) -> Candidate:
    """Create a mock Candidate for testing."""
    return Candidate(
        arxiv_id=arxiv_id,
        title=title,
        year=year,
        authors=["Test Author"],
        abstract=abstract,
        url=f"http://arxiv.org/abs/{arxiv_id}",
        pdf_url=f"http://arxiv.org/pdf/{arxiv_id}",
        categories=["cs.AI"],
    )


class TestSearchSourcesArxiv:
    """Test search_sources with arxiv source."""

    @patch("agents.search.tools.search.ArxivClient")
    def test_search_sources_arxiv(self, mock_arxiv_client_class):
        """search_sources should search arxiv and return candidates."""
        mock_candidates = [
            create_mock_candidate("2401.00001", "Deep Learning Paper"),
            create_mock_candidate("2401.00002", "Machine Learning Study"),
        ]

        mock_client = MagicMock()
        mock_client.search.return_value = mock_candidates
        mock_arxiv_client_class.return_value = mock_client

        # Call the underlying implementation function
        result = _search_sources_impl(
            queries=["deep learning"],
            sources=["arxiv"],
            max_results=10,
        )

        assert len(result) == 2
        assert all(isinstance(c, Candidate) for c in result)
        mock_client.search.assert_called_once()

        # Verify search was called with correct params
        call_args = mock_client.search.call_args[0][0]
        assert call_args.queries == ["deep learning"]
        assert call_args.max_results == 10

    @patch("agents.search.tools.search.ArxivClient")
    def test_search_sources_with_categories(self, mock_arxiv_client_class):
        """search_sources should pass categories to arxiv client."""
        mock_client = MagicMock()
        mock_client.search.return_value = []
        mock_arxiv_client_class.return_value = mock_client

        _search_sources_impl(
            queries=["transformer"],
            sources=["arxiv"],
            categories=["cs.AI", "cs.CL"],
        )

        call_args = mock_client.search.call_args[0][0]
        assert call_args.categories == ["cs.AI", "cs.CL"]

    @patch("agents.search.tools.search.ArxivClient")
    def test_search_sources_with_time_range(self, mock_arxiv_client_class):
        """search_sources should pass time_range_years to arxiv client."""
        mock_client = MagicMock()
        mock_client.search.return_value = []
        mock_arxiv_client_class.return_value = mock_client

        _search_sources_impl(
            queries=["attention"],
            sources=["arxiv"],
            time_range_years=3,
        )

        call_args = mock_client.search.call_args[0][0]
        assert call_args.time_range_years == 3


class TestSearchSourcesUnknownSource:
    """Test search_sources with unknown source."""

    @patch("agents.search.tools.search.ArxivClient")
    def test_search_sources_unknown_source(self, mock_arxiv_client_class):
        """search_sources should ignore unknown sources."""
        mock_client = MagicMock()
        mock_client.search.return_value = []
        mock_arxiv_client_class.return_value = mock_client

        result = _search_sources_impl(
            queries=["test"],
            sources=["unknown_source"],
        )

        assert result == []
        mock_client.search.assert_not_called()

    @patch("agents.search.tools.search.ArxivClient")
    def test_search_sources_mixed_sources(self, mock_arxiv_client_class):
        """search_sources should process known sources and ignore unknown ones."""
        mock_candidates = [
            create_mock_candidate("2401.00001", "Test Paper"),
        ]

        mock_client = MagicMock()
        mock_client.search.return_value = mock_candidates
        mock_arxiv_client_class.return_value = mock_client

        result = _search_sources_impl(
            queries=["test"],
            sources=["arxiv", "unknown_source", "internal"],
        )

        # Should return arxiv results, ignore unknown, and skip internal (not implemented)
        assert len(result) == 1
        mock_client.search.assert_called_once()


class TestSearchSourcesAppliesRanking:
    """Test that search_sources applies ranking and deduplication."""

    @patch("agents.search.tools.search.ArxivClient")
    def test_search_sources_applies_ranking(self, mock_arxiv_client_class):
        """search_sources should rank candidates by keyword match and recency."""
        # Create candidates where ranking should reorder them
        candidate_low_match = create_mock_candidate(
            "2401.00001",
            "Random Title",
            year=2024,
            abstract="Nothing related",
        )
        candidate_high_match = create_mock_candidate(
            "2401.00002",
            "Deep Learning Transformers",
            year=2024,
            abstract="Deep learning with transformers",
        )

        mock_client = MagicMock()
        mock_client.search.return_value = [candidate_low_match, candidate_high_match]
        mock_arxiv_client_class.return_value = mock_client

        result = _search_sources_impl(
            queries=["deep learning transformers"],
            sources=["arxiv"],
        )

        # High match candidate should be ranked first
        assert len(result) == 2
        assert result[0].arxiv_id == "2401.00002"
        assert result[0].score > result[1].score

    @patch("agents.search.tools.search.ArxivClient")
    def test_search_sources_deduplicates(self, mock_arxiv_client_class):
        """search_sources should remove duplicate candidates."""
        duplicate_candidate = create_mock_candidate("2401.00001", "Test Paper")

        mock_client = MagicMock()
        # Return duplicates
        mock_client.search.return_value = [duplicate_candidate, duplicate_candidate]
        mock_arxiv_client_class.return_value = mock_client

        result = _search_sources_impl(
            queries=["test"],
            sources=["arxiv"],
        )

        # Should deduplicate
        assert len(result) == 1

    @patch("agents.search.tools.search.ArxivClient")
    def test_search_sources_respects_max_results(self, mock_arxiv_client_class):
        """search_sources should limit results to max_results."""
        mock_candidates = [
            create_mock_candidate(f"2401.0000{i}", f"Paper {i}")
            for i in range(10)
        ]

        mock_client = MagicMock()
        mock_client.search.return_value = mock_candidates
        mock_arxiv_client_class.return_value = mock_client

        result = _search_sources_impl(
            queries=["test"],
            sources=["arxiv"],
            max_results=5,
        )

        assert len(result) == 5


class TestSearchSourcesDefaultValues:
    """Test search_sources default parameter values."""

    @patch("agents.search.tools.search.ArxivClient")
    def test_search_sources_default_values(self, mock_arxiv_client_class):
        """search_sources should use default values when not specified."""
        mock_client = MagicMock()
        mock_client.search.return_value = []
        mock_arxiv_client_class.return_value = mock_client

        _search_sources_impl(queries=["test"])

        call_args = mock_client.search.call_args[0][0]
        assert call_args.max_results == 80
        assert call_args.time_range_years == 7
        assert call_args.categories is None
