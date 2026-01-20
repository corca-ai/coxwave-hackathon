"""Tests for candidate deduplication logic."""

import pytest

from agents.search.dedup import dedupe_candidates
from agents.search.schemas import Candidate


def _make_candidate(arxiv_id: str, title: str = "Test Paper") -> Candidate:
    """Helper to create a Candidate with minimal required fields."""
    return Candidate(
        arxiv_id=arxiv_id,
        title=title,
        year=2023,
        authors=["Author"],
        abstract="Test abstract",
        url=f"https://arxiv.org/abs/{arxiv_id}",
    )


class TestDedupeByArxivId:
    """Test deduplication by arxiv_id."""

    def test_dedupe_removes_duplicates(self):
        """dedupe_candidates should remove duplicate arxiv_ids."""
        candidates = [
            _make_candidate("2301.00001", "Paper A"),
            _make_candidate("2301.00002", "Paper B"),
            _make_candidate("2301.00001", "Paper A Duplicate"),
            _make_candidate("2301.00003", "Paper C"),
            _make_candidate("2301.00002", "Paper B Duplicate"),
        ]

        result = dedupe_candidates(candidates)

        assert len(result) == 3
        arxiv_ids = [c.arxiv_id for c in result]
        assert arxiv_ids == ["2301.00001", "2301.00002", "2301.00003"]

    def test_dedupe_keeps_first_occurrence(self):
        """dedupe_candidates should keep the first occurrence of each arxiv_id."""
        candidates = [
            _make_candidate("2301.00001", "First Version"),
            _make_candidate("2301.00001", "Second Version"),
        ]

        result = dedupe_candidates(candidates)

        assert len(result) == 1
        assert result[0].title == "First Version"

    def test_dedupe_with_no_duplicates(self):
        """dedupe_candidates should return all candidates when no duplicates exist."""
        candidates = [
            _make_candidate("2301.00001"),
            _make_candidate("2301.00002"),
            _make_candidate("2301.00003"),
        ]

        result = dedupe_candidates(candidates)

        assert len(result) == 3

    def test_dedupe_empty_list(self):
        """dedupe_candidates should handle empty list."""
        result = dedupe_candidates([])

        assert result == []


class TestDedupePreservesOrder:
    """Test that deduplication preserves original order."""

    def test_dedupe_preserves_order(self):
        """dedupe_candidates should preserve the order of first occurrences."""
        candidates = [
            _make_candidate("2301.00003", "Third"),
            _make_candidate("2301.00001", "First"),
            _make_candidate("2301.00002", "Second"),
            _make_candidate("2301.00001", "First Dup"),
        ]

        result = dedupe_candidates(candidates)

        titles = [c.title for c in result]
        assert titles == ["Third", "First", "Second"]


class TestDedupeWithExistingIds:
    """Test deduplication with pre-existing IDs to exclude."""

    def test_dedupe_excludes_existing_ids(self):
        """dedupe_candidates should exclude candidates with existing arxiv_ids."""
        candidates = [
            _make_candidate("2301.00001"),
            _make_candidate("2301.00002"),
            _make_candidate("2301.00003"),
        ]
        existing_ids = {"2301.00001", "2301.00003"}

        result = dedupe_candidates(candidates, existing_ids=existing_ids)

        assert len(result) == 1
        assert result[0].arxiv_id == "2301.00002"

    def test_dedupe_with_empty_existing_ids(self):
        """dedupe_candidates should work with empty existing_ids set."""
        candidates = [
            _make_candidate("2301.00001"),
            _make_candidate("2301.00002"),
        ]

        result = dedupe_candidates(candidates, existing_ids=set())

        assert len(result) == 2

    def test_dedupe_with_none_existing_ids(self):
        """dedupe_candidates should work with None existing_ids."""
        candidates = [
            _make_candidate("2301.00001"),
            _make_candidate("2301.00002"),
        ]

        result = dedupe_candidates(candidates, existing_ids=None)

        assert len(result) == 2

    def test_dedupe_does_not_modify_existing_ids(self):
        """dedupe_candidates should not modify the existing_ids set."""
        candidates = [
            _make_candidate("2301.00001"),
            _make_candidate("2301.00002"),
        ]
        existing_ids = {"2301.00003"}
        original_existing = existing_ids.copy()

        dedupe_candidates(candidates, existing_ids=existing_ids)

        assert existing_ids == original_existing
