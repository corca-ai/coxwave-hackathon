"""Tests for candidate ranking logic."""

import pytest
from datetime import datetime
from unittest.mock import patch

from agents.search.ranking import calculate_score, rank_candidates
from agents.search.schemas import Candidate


def _make_candidate(
    arxiv_id: str,
    title: str = "Test Paper",
    abstract: str = "Test abstract",
    year: int = 2023,
) -> Candidate:
    """Helper to create a Candidate with minimal required fields."""
    return Candidate(
        arxiv_id=arxiv_id,
        title=title,
        year=year,
        authors=["Author"],
        abstract=abstract,
        url=f"https://arxiv.org/abs/{arxiv_id}",
    )


class TestCalculateScoreKeywordMatch:
    """Test keyword matching in score calculation."""

    def test_all_keywords_match_in_title(self):
        """calculate_score should give high keyword score when all keywords match in title."""
        candidate = _make_candidate(
            "2301.00001",
            title="Transformer Architecture for Natural Language Processing",
            abstract="A paper about neural networks.",
            year=datetime.now().year,
        )
        keywords = ["transformer", "natural", "language"]

        score = calculate_score(candidate, keywords)

        # All 3 keywords match: keyword_score = 1.0 * 0.6 = 0.6
        # Current year: recency_score = 1.0 * 0.4 = 0.4
        # Total = 1.0
        assert score == 1.0

    def test_keywords_match_in_abstract(self):
        """calculate_score should match keywords in abstract."""
        candidate = _make_candidate(
            "2301.00001",
            title="A Generic Title",
            abstract="This paper presents a transformer model for deep learning.",
            year=datetime.now().year,
        )
        keywords = ["transformer", "deep", "learning"]

        score = calculate_score(candidate, keywords)

        assert score == 1.0

    def test_partial_keyword_match(self):
        """calculate_score should handle partial keyword matches."""
        candidate = _make_candidate(
            "2301.00001",
            title="Transformer Architecture",
            abstract="Neural network model.",
            year=datetime.now().year,
        )
        keywords = ["transformer", "attention", "bert"]

        score = calculate_score(candidate, keywords)

        # 1/3 keywords match: keyword_score = 0.333 * 0.6 = 0.2
        # Current year: recency_score = 1.0 * 0.4 = 0.4
        # Total ~ 0.6
        assert 0.55 < score < 0.65

    def test_no_keyword_match(self):
        """calculate_score should handle no keyword matches."""
        candidate = _make_candidate(
            "2301.00001",
            title="Unrelated Paper",
            abstract="Something completely different.",
            year=datetime.now().year,
        )
        keywords = ["transformer", "attention", "bert"]

        score = calculate_score(candidate, keywords)

        # 0 keywords match: keyword_score = 0 * 0.6 = 0
        # Current year: recency_score = 1.0 * 0.4 = 0.4
        assert score == 0.4

    def test_case_insensitive_matching(self):
        """calculate_score should match keywords case-insensitively."""
        candidate = _make_candidate(
            "2301.00001",
            title="TRANSFORMER Architecture",
            abstract="ATTENTION mechanism.",
            year=datetime.now().year,
        )
        keywords = ["Transformer", "ATTENTION"]

        score = calculate_score(candidate, keywords)

        assert score == 1.0

    def test_empty_keywords(self):
        """calculate_score should handle empty keyword list."""
        candidate = _make_candidate(
            "2301.00001",
            title="Test Paper",
            year=datetime.now().year,
        )
        keywords = []

        score = calculate_score(candidate, keywords)

        # Empty keywords: keyword_score = 0 * 0.6 = 0
        # Current year: recency_score = 1.0 * 0.4 = 0.4
        assert score == 0.4


class TestCalculateScoreRecency:
    """Test recency scoring in score calculation."""

    def test_current_year_paper(self):
        """calculate_score should give max recency score for current year papers."""
        current_year = datetime.now().year
        candidate = _make_candidate(
            "2301.00001",
            title="Test",
            year=current_year,
        )

        score = calculate_score(candidate, [])

        # recency_score = 1.0 * 0.4 = 0.4
        assert score == 0.4

    def test_five_year_old_paper(self):
        """calculate_score should give medium recency score for 5-year-old papers."""
        current_year = datetime.now().year
        candidate = _make_candidate(
            "2301.00001",
            title="Test",
            year=current_year - 5,
        )

        score = calculate_score(candidate, [])

        # recency_score = (1 - 5/10) * 0.4 = 0.5 * 0.4 = 0.2
        assert score == 0.2

    def test_ten_year_old_paper(self):
        """calculate_score should give zero recency score for 10-year-old papers."""
        current_year = datetime.now().year
        candidate = _make_candidate(
            "2301.00001",
            title="Test",
            year=current_year - 10,
        )

        score = calculate_score(candidate, [])

        # recency_score = max(0, 1 - 10/10) * 0.4 = 0
        assert score == 0.0

    def test_very_old_paper(self):
        """calculate_score should cap recency score at zero for very old papers."""
        current_year = datetime.now().year
        candidate = _make_candidate(
            "2301.00001",
            title="Test",
            year=current_year - 20,
        )

        score = calculate_score(candidate, [])

        # recency_score = max(0, 1 - 20/10) = max(0, -1) = 0
        assert score == 0.0


class TestRankCandidatesByScore:
    """Test ranking candidates by computed score."""

    def test_rank_candidates_by_score(self):
        """rank_candidates should sort candidates by score descending."""
        current_year = datetime.now().year
        candidates = [
            _make_candidate("2301.00001", title="Paper A", year=current_year - 5),
            _make_candidate("2301.00002", title="Transformer Paper", year=current_year),
            _make_candidate("2301.00003", title="Old Paper", year=current_year - 10),
        ]
        keywords = ["transformer"]

        result = rank_candidates(candidates, keywords)

        assert result[0].arxiv_id == "2301.00002"  # Highest: keyword match + recent
        assert result[1].arxiv_id == "2301.00001"  # Medium: no match, medium recency
        assert result[2].arxiv_id == "2301.00003"  # Lowest: no match, no recency

    def test_rank_candidates_updates_scores(self):
        """rank_candidates should update score field on each candidate."""
        current_year = datetime.now().year
        candidates = [
            _make_candidate("2301.00001", title="Transformer", year=current_year),
        ]
        keywords = ["transformer"]

        result = rank_candidates(candidates, keywords)

        assert result[0].score == 1.0

    def test_rank_candidates_with_max_results(self):
        """rank_candidates should limit results when max_results is specified."""
        current_year = datetime.now().year
        candidates = [
            _make_candidate("2301.00001", title="Paper A", year=current_year),
            _make_candidate("2301.00002", title="Paper B", year=current_year),
            _make_candidate("2301.00003", title="Paper C", year=current_year),
            _make_candidate("2301.00004", title="Transformer", year=current_year),
        ]
        keywords = ["transformer"]

        result = rank_candidates(candidates, keywords, max_results=2)

        assert len(result) == 2
        assert result[0].arxiv_id == "2301.00004"  # Transformer match ranks highest

    def test_rank_candidates_empty_list(self):
        """rank_candidates should handle empty candidate list."""
        result = rank_candidates([], ["transformer"])

        assert result == []

    def test_rank_candidates_no_max_results(self):
        """rank_candidates should return all candidates when max_results is None."""
        current_year = datetime.now().year
        candidates = [
            _make_candidate("2301.00001", year=current_year),
            _make_candidate("2301.00002", year=current_year),
            _make_candidate("2301.00003", year=current_year),
        ]

        result = rank_candidates(candidates, [], max_results=None)

        assert len(result) == 3

    def test_rank_candidates_preserves_candidate_data(self):
        """rank_candidates should preserve all candidate data except score."""
        candidate = Candidate(
            arxiv_id="2301.00001",
            title="Test Paper",
            year=datetime.now().year,
            authors=["Alice", "Bob"],
            abstract="Test abstract content",
            url="https://arxiv.org/abs/2301.00001",
            pdf_url="https://arxiv.org/pdf/2301.00001.pdf",
            categories=["cs.AI", "cs.LG"],
            why_selected="Original reason",
        )

        result = rank_candidates([candidate], ["test"])

        assert result[0].arxiv_id == "2301.00001"
        assert result[0].title == "Test Paper"
        assert result[0].authors == ["Alice", "Bob"]
        assert result[0].abstract == "Test abstract content"
        assert result[0].pdf_url == "https://arxiv.org/pdf/2301.00001.pdf"
        assert result[0].categories == ["cs.AI", "cs.LG"]
        assert result[0].why_selected == "Original reason"
