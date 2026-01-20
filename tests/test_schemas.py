"""Tests for Search Agent Pydantic schemas."""

import pytest
from pydantic import ValidationError

from agent.search.schemas import (
    Candidate,
    Constraints,
    IngestPolicy,
    IngestSummary,
    LoopDecision,
    PreviewSnippet,
    QueryPlan,
    SearchError,
    SearchRequest,
    SearchResult,
)


class TestSearchRequestDefaults:
    """Test SearchRequest with only goal provided, verifying all defaults."""

    def test_minimal_request_with_goal_only(self):
        """SearchRequest should work with only goal provided."""
        request = SearchRequest(goal="Find papers on transformer architectures")

        assert request.goal == "Find papers on transformer architectures"
        assert request.namespace == "default"

    def test_constraints_default_values(self):
        """Constraints should have correct default values."""
        request = SearchRequest(goal="test")

        assert request.constraints.target_new_docs == 12
        assert request.constraints.max_candidates == 80
        assert request.constraints.max_selected == 20
        assert request.constraints.time_range_years == 7
        assert request.constraints.loop_budget == 2
        assert request.constraints.categories is None
        assert request.constraints.preview_top_k == 5

    def test_ingest_policy_default_values(self):
        """IngestPolicy should have correct default values."""
        request = SearchRequest(goal="test")
        policy = request.constraints.ingest_policy

        assert policy.mode == "abstract_only"
        assert policy.chunk_size == 512
        assert policy.chunk_overlap == 50

    def test_custom_namespace(self):
        """SearchRequest should accept custom namespace."""
        request = SearchRequest(goal="test", namespace="ml-research")

        assert request.namespace == "ml-research"

    def test_custom_constraints(self):
        """SearchRequest should accept custom constraints."""
        custom_constraints = Constraints(
            target_new_docs=20,
            max_candidates=100,
            categories=["cs.AI", "cs.LG"],
        )
        request = SearchRequest(goal="test", constraints=custom_constraints)

        assert request.constraints.target_new_docs == 20
        assert request.constraints.max_candidates == 100
        assert request.constraints.categories == ["cs.AI", "cs.LG"]


class TestCandidateRequiredFields:
    """Test Candidate model required fields and defaults."""

    def test_candidate_with_required_fields_only(self):
        """Candidate should work with only required fields."""
        candidate = Candidate(
            arxiv_id="2301.00001",
            title="Test Paper",
            year=2023,
            authors=["Alice", "Bob"],
            abstract="This is a test abstract.",
            url="https://arxiv.org/abs/2301.00001",
        )

        assert candidate.arxiv_id == "2301.00001"
        assert candidate.title == "Test Paper"
        assert candidate.year == 2023
        assert candidate.authors == ["Alice", "Bob"]
        assert candidate.abstract == "This is a test abstract."
        assert candidate.url == "https://arxiv.org/abs/2301.00001"

    def test_candidate_default_values(self):
        """Candidate should have correct default values for optional fields."""
        candidate = Candidate(
            arxiv_id="2301.00001",
            title="Test Paper",
            year=2023,
            authors=["Alice"],
            abstract="Test abstract.",
            url="https://arxiv.org/abs/2301.00001",
        )

        assert candidate.pdf_url is None
        assert candidate.categories == []
        assert candidate.score == 0.0
        assert candidate.why_selected == ""

    def test_candidate_with_all_fields(self):
        """Candidate should accept all optional fields."""
        candidate = Candidate(
            arxiv_id="2301.00001",
            title="Test Paper",
            year=2023,
            authors=["Alice", "Bob"],
            abstract="Test abstract.",
            url="https://arxiv.org/abs/2301.00001",
            pdf_url="https://arxiv.org/pdf/2301.00001.pdf",
            categories=["cs.AI", "cs.LG"],
            score=0.95,
            why_selected="Highly relevant to search query",
        )

        assert candidate.pdf_url == "https://arxiv.org/pdf/2301.00001.pdf"
        assert candidate.categories == ["cs.AI", "cs.LG"]
        assert candidate.score == 0.95
        assert candidate.why_selected == "Highly relevant to search query"

    def test_candidate_missing_required_field_raises_error(self):
        """Candidate should raise ValidationError when required field is missing."""
        with pytest.raises(ValidationError):
            Candidate(
                arxiv_id="2301.00001",
                title="Test Paper",
                # missing year, authors, abstract, url
            )


class TestSearchResultStructure:
    """Test SearchResult complete structure."""

    def test_search_result_minimal(self):
        """SearchResult should work with required fields and empty lists."""
        query_plan = QueryPlan(
            queries=["transformer architecture"],
            time_range="2017-2024",
            categories=["cs.AI"],
        )
        ingest_summary = IngestSummary(
            new_docs_added=5,
            duplicates_skipped=2,
        )
        result = SearchResult(
            query_plan=query_plan,
            selected_papers=[],
            ingest_summary=ingest_summary,
        )

        assert result.query_plan.queries == ["transformer architecture"]
        assert result.selected_papers == []
        assert result.ingest_summary.new_docs_added == 5
        assert result.preview_snippets == []
        assert result.errors == []

    def test_search_result_with_papers(self):
        """SearchResult should handle list of Candidate papers."""
        query_plan = QueryPlan(
            queries=["attention mechanism"],
            time_range="2020-2024",
            categories=["cs.LG"],
        )
        papers = [
            Candidate(
                arxiv_id="2301.00001",
                title="Paper 1",
                year=2023,
                authors=["Author 1"],
                abstract="Abstract 1",
                url="https://arxiv.org/abs/2301.00001",
                score=0.9,
            ),
            Candidate(
                arxiv_id="2301.00002",
                title="Paper 2",
                year=2023,
                authors=["Author 2"],
                abstract="Abstract 2",
                url="https://arxiv.org/abs/2301.00002",
                score=0.85,
            ),
        ]
        ingest_summary = IngestSummary(
            new_docs_added=2,
            duplicates_skipped=0,
            chunks_added=10,
            index_size=100,
        )
        result = SearchResult(
            query_plan=query_plan,
            selected_papers=papers,
            ingest_summary=ingest_summary,
        )

        assert len(result.selected_papers) == 2
        assert result.selected_papers[0].arxiv_id == "2301.00001"
        assert result.selected_papers[1].score == 0.85
        assert result.ingest_summary.chunks_added == 10

    def test_search_result_with_preview_snippets(self):
        """SearchResult should handle preview snippets."""
        query_plan = QueryPlan(
            queries=["test"],
            time_range="2020-2024",
            categories=[],
        )
        ingest_summary = IngestSummary(new_docs_added=1, duplicates_skipped=0)
        snippets = [
            PreviewSnippet(
                arxiv_id="2301.00001",
                chunk_id="chunk_001",
                score=0.95,
                snippet="This is a relevant text snippet from the paper.",
            ),
        ]
        result = SearchResult(
            query_plan=query_plan,
            selected_papers=[],
            ingest_summary=ingest_summary,
            preview_snippets=snippets,
        )

        assert len(result.preview_snippets) == 1
        assert result.preview_snippets[0].chunk_id == "chunk_001"

    def test_search_result_with_errors(self):
        """SearchResult should handle error list."""
        query_plan = QueryPlan(
            queries=["test"],
            time_range="2020-2024",
            categories=[],
        )
        ingest_summary = IngestSummary(new_docs_added=0, duplicates_skipped=0)
        errors = [
            SearchError(
                code="ARXIV_RATE_LIMIT",
                message="Rate limited by arXiv API",
                retryable=True,
            ),
            SearchError(
                code="INVALID_QUERY",
                message="Query syntax error",
                retryable=False,
            ),
        ]
        result = SearchResult(
            query_plan=query_plan,
            selected_papers=[],
            ingest_summary=ingest_summary,
            errors=errors,
        )

        assert len(result.errors) == 2
        assert result.errors[0].retryable is True
        assert result.errors[1].code == "INVALID_QUERY"

    def test_query_plan_with_loop_decisions(self):
        """QueryPlan should handle loop decisions."""
        query_plan = QueryPlan(
            queries=["initial query", "refined query"],
            time_range="2020-2024",
            categories=["cs.AI"],
            loop_decisions=[
                LoopDecision(
                    iteration=1,
                    action="expand",
                    reason="Not enough results found",
                ),
                LoopDecision(
                    iteration=2,
                    action="stop",
                    reason="Sufficient papers collected",
                ),
            ],
        )

        assert len(query_plan.loop_decisions) == 2
        assert query_plan.loop_decisions[0].action == "expand"
        assert query_plan.loop_decisions[1].iteration == 2


class TestIngestSummaryDefaults:
    """Test IngestSummary default values."""

    def test_ingest_summary_minimal(self):
        """IngestSummary should work with only required fields."""
        summary = IngestSummary(new_docs_added=5, duplicates_skipped=3)

        assert summary.new_docs_added == 5
        assert summary.duplicates_skipped == 3
        assert summary.chunks_added == 0
        assert summary.index_size == 0

    def test_ingest_summary_full(self):
        """IngestSummary should accept all fields."""
        summary = IngestSummary(
            new_docs_added=10,
            duplicates_skipped=2,
            chunks_added=50,
            index_size=1000,
        )

        assert summary.chunks_added == 50
        assert summary.index_size == 1000
