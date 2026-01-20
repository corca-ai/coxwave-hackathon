"""Tests for ArxivClient."""

from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from agent.search.clients.arxiv_client import ArxivClient, ArxivSearchParams
from agent.search.schemas import Candidate


class MockAuthor:
    """Mock arXiv author with proper string conversion."""

    def __init__(self, name: str):
        self.name = name

    def __str__(self) -> str:
        return self.name


def create_mock_result(
    entry_id: str,
    title: str,
    published: datetime,
    authors: list[str],
    summary: str,
    pdf_url: str | None,
    categories: list[str],
) -> MagicMock:
    """Create a mock arxiv.Result object."""
    mock_result = MagicMock()
    mock_result.entry_id = entry_id
    mock_result.title = title
    mock_result.published = published
    mock_result.authors = [MockAuthor(name) for name in authors]
    mock_result.summary = summary
    mock_result.pdf_url = pdf_url
    mock_result.categories = categories
    return mock_result


class TestBuildQuery:
    """Test query building functionality."""

    def test_build_query_simple(self):
        """Single query should produce simple all: query."""
        client = ArxivClient()
        params = ArxivSearchParams(queries=["transformer architecture"])

        query = client._build_query(params)

        assert query == 'all:"transformer architecture"'

    def test_build_query_multiple_queries(self):
        """Multiple queries should be joined with OR."""
        client = ArxivClient()
        params = ArxivSearchParams(queries=["transformer", "attention mechanism"])

        query = client._build_query(params)

        assert query == 'all:"transformer" OR all:"attention mechanism"'

    def test_build_query_with_categories(self):
        """Queries with categories should include category filter."""
        client = ArxivClient()
        params = ArxivSearchParams(
            queries=["deep learning"],
            categories=["cs.AI", "cs.LG"],
        )

        query = client._build_query(params)

        assert query == '(all:"deep learning") AND (cat:cs.AI OR cat:cs.LG)'

    def test_build_query_multiple_queries_with_categories(self):
        """Multiple queries with categories should combine correctly."""
        client = ArxivClient()
        params = ArxivSearchParams(
            queries=["transformer", "attention"],
            categories=["cs.CL"],
        )

        query = client._build_query(params)

        assert query == '(all:"transformer" OR all:"attention") AND (cat:cs.CL)'


class TestExtractArxivId:
    """Test arXiv ID extraction from entry URLs."""

    def test_extract_arxiv_id_new_format(self):
        """Should extract ID from new format entry_id."""
        client = ArxivClient()
        entry_id = "http://arxiv.org/abs/2301.00001v1"

        arxiv_id = client._extract_arxiv_id(entry_id)

        assert arxiv_id == "2301.00001"

    def test_extract_arxiv_id_five_digit(self):
        """Should extract 5-digit arXiv IDs."""
        client = ArxivClient()
        entry_id = "http://arxiv.org/abs/2301.12345v2"

        arxiv_id = client._extract_arxiv_id(entry_id)

        assert arxiv_id == "2301.12345"

    def test_extract_arxiv_id_old_format(self):
        """Should extract ID from old format (category/number)."""
        client = ArxivClient()
        entry_id = "http://arxiv.org/abs/hep-th/9901001v1"

        arxiv_id = client._extract_arxiv_id(entry_id)

        assert arxiv_id == "hep-th/9901001"

    def test_extract_arxiv_id_invalid_raises(self):
        """Should raise ValueError for invalid entry_id."""
        client = ArxivClient()
        entry_id = "http://example.com/invalid"

        with pytest.raises(ValueError, match="Cannot extract arxiv_id"):
            client._extract_arxiv_id(entry_id)


class TestParseResult:
    """Test parsing arxiv.Result to Candidate."""

    def test_parse_result(self):
        """Should correctly parse arxiv.Result into Candidate."""
        client = ArxivClient()

        mock_result = create_mock_result(
            entry_id="http://arxiv.org/abs/2301.00001v1",
            title="Test Paper\nWith Newline",
            published=datetime(2023, 1, 15),
            authors=["Alice Author"],
            summary="This is the\nabstract text.",
            pdf_url="http://arxiv.org/pdf/2301.00001v1",
            categories=["cs.AI", "cs.LG"],
        )

        candidate = client._parse_result(mock_result)

        assert candidate is not None
        assert candidate.arxiv_id == "2301.00001"
        assert candidate.title == "Test Paper With Newline"
        assert candidate.year == 2023
        assert candidate.abstract == "This is the abstract text."
        assert candidate.url == "http://arxiv.org/abs/2301.00001v1"
        assert candidate.pdf_url == "http://arxiv.org/pdf/2301.00001v1"
        assert candidate.categories == ["cs.AI", "cs.LG"]

    def test_parse_result_with_multiple_authors(self):
        """Should handle multiple authors correctly."""
        client = ArxivClient()

        mock_result = create_mock_result(
            entry_id="http://arxiv.org/abs/2301.00002v1",
            title="Multi-Author Paper",
            published=datetime(2023, 2, 20),
            authors=["First Author", "Second Author"],
            summary="Abstract text.",
            pdf_url=None,
            categories=["cs.CL"],
        )

        candidate = client._parse_result(mock_result)

        assert candidate is not None
        assert candidate.authors == ["First Author", "Second Author"]
        assert candidate.pdf_url is None

    def test_parse_result_exception_returns_none(self):
        """Should return None when parsing fails."""
        client = ArxivClient()

        mock_result = MagicMock()
        mock_result.entry_id = "invalid-entry-id"  # Will fail ID extraction

        candidate = client._parse_result(mock_result)

        assert candidate is None


class TestSearch:
    """Test the main search functionality."""

    @patch("agent.search.clients.arxiv_client.arxiv.Client")
    @patch("agent.search.clients.arxiv_client.arxiv.Search")
    def test_search_returns_candidates(self, mock_search_class, mock_client_class):
        """Search should return list of Candidate objects."""
        mock_result1 = create_mock_result(
            entry_id="http://arxiv.org/abs/2301.00001v1",
            title="Paper One",
            published=datetime(2023, 1, 1),
            authors=["Author One"],
            summary="Abstract one.",
            pdf_url="http://arxiv.org/pdf/2301.00001v1",
            categories=["cs.AI"],
        )

        mock_result2 = create_mock_result(
            entry_id="http://arxiv.org/abs/2301.00002v1",
            title="Paper Two",
            published=datetime(2023, 2, 1),
            authors=["Author Two"],
            summary="Abstract two.",
            pdf_url="http://arxiv.org/pdf/2301.00002v1",
            categories=["cs.LG"],
        )

        # Configure mock client to return results
        mock_client_instance = MagicMock()
        mock_client_instance.results.return_value = [mock_result1, mock_result2]
        mock_client_class.return_value = mock_client_instance

        client = ArxivClient()
        params = ArxivSearchParams(queries=["machine learning"])

        candidates = client.search(params)

        assert len(candidates) == 2
        assert all(isinstance(c, Candidate) for c in candidates)

    @patch("agent.search.clients.arxiv_client.arxiv.Client")
    @patch("agent.search.clients.arxiv_client.arxiv.Search")
    def test_search_respects_time_range(self, mock_search_class, mock_client_class):
        """Search should filter out papers outside the time range."""
        current_year = datetime.now().year
        recent = create_mock_result(
            entry_id="http://arxiv.org/abs/2401.00001v1",
            title="Recent Paper",
            published=datetime(current_year, 1, 1),
            authors=["Author One"],
            summary="Recent abstract.",
            pdf_url="http://arxiv.org/pdf/2401.00001v1",
            categories=["cs.AI"],
        )
        old = create_mock_result(
            entry_id="http://arxiv.org/abs/2001.00001v1",
            title="Old Paper",
            published=datetime(current_year - 2, 1, 1),
            authors=["Author Two"],
            summary="Old abstract.",
            pdf_url="http://arxiv.org/pdf/2001.00001v1",
            categories=["cs.AI"],
        )

        mock_client_instance = MagicMock()
        mock_client_instance.results.return_value = [recent, old]
        mock_client_class.return_value = mock_client_instance

        client = ArxivClient()
        params = ArxivSearchParams(queries=["test"], max_results=10, time_range_years=1)
        candidates = client.search(params)

        assert len(candidates) == 1
        assert candidates[0].title == "Recent Paper"
        assert candidates[0].arxiv_id == "2401.00001"

    @patch("agent.search.clients.arxiv_client.arxiv.Client")
    @patch("agent.search.clients.arxiv_client.arxiv.Search")
    def test_search_skips_invalid_results(self, mock_search_class, mock_client_class):
        """Search should skip results that fail to parse."""
        mock_valid = create_mock_result(
            entry_id="http://arxiv.org/abs/2301.00001v1",
            title="Valid Paper",
            published=datetime(2023, 1, 1),
            authors=["Author"],
            summary="Valid abstract.",
            pdf_url="http://arxiv.org/pdf/2301.00001v1",
            categories=["cs.AI"],
        )

        mock_invalid = MagicMock()
        mock_invalid.entry_id = "invalid-id"  # Will fail parsing

        mock_client_instance = MagicMock()
        mock_client_instance.results.return_value = [mock_valid, mock_invalid]
        mock_client_class.return_value = mock_client_instance

        client = ArxivClient()
        params = ArxivSearchParams(queries=["test"])

        candidates = client.search(params)

        assert len(candidates) == 1
        assert candidates[0].title == "Valid Paper"


class TestArxivSearchParams:
    """Test ArxivSearchParams dataclass."""

    def test_default_values(self):
        """Should have correct default values."""
        params = ArxivSearchParams(queries=["test query"])

        assert params.queries == ["test query"]
        assert params.max_results == 80
        assert params.time_range_years == 7
        assert params.categories is None

    def test_custom_values(self):
        """Should accept custom values."""
        params = ArxivSearchParams(
            queries=["query1", "query2"],
            max_results=100,
            time_range_years=5,
            categories=["cs.AI", "cs.LG"],
        )

        assert params.queries == ["query1", "query2"]
        assert params.max_results == 100
        assert params.time_range_years == 5
        assert params.categories == ["cs.AI", "cs.LG"]
