"""Tests for LocalStore - JSON file based local storage for Search Agent."""

import json
import pytest

from agent.search.clients.local_store import LocalStore
from agent.search.schemas import (
    Candidate,
    IngestSummary,
    QueryPlan,
    SearchResult,
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


def make_search_result(papers: list[Candidate] | None = None) -> SearchResult:
    """Helper function to create a SearchResult instance for testing."""
    return SearchResult(
        query_plan=QueryPlan(
            queries=["test query"],
            time_range="2020-2024",
            categories=["cs.AI"],
        ),
        selected_papers=papers or [],
        ingest_summary=IngestSummary(new_docs_added=1, duplicates_skipped=0),
    )


class TestLoadExistingIds:
    """Tests for LocalStore.load_existing_ids method."""

    def test_load_existing_ids_empty(self, tmp_path):
        """Should return empty set when no papers file exists."""
        store = LocalStore(artifacts_dir=tmp_path)
        result = store.load_existing_ids("test-namespace")
        assert result == set()

    def test_load_existing_ids_with_papers(self, tmp_path):
        """Should return set of arxiv_ids from existing papers file."""
        store = LocalStore(artifacts_dir=tmp_path)
        papers_file = tmp_path / "test-namespace_papers.json"
        papers_file.write_text(
            json.dumps([
                {"arxiv_id": "2301.00001", "title": "Paper 1"},
                {"arxiv_id": "2301.00002", "title": "Paper 2"},
                {"arxiv_id": "2301.00003", "title": "Paper 3"},
            ]),
            encoding="utf-8",
        )

        result = store.load_existing_ids("test-namespace")
        assert result == {"2301.00001", "2301.00002", "2301.00003"}


class TestAppendPapers:
    """Tests for LocalStore.append_papers method."""

    def test_append_papers_new(self, tmp_path):
        """Should append new papers to empty store and return count."""
        store = LocalStore(artifacts_dir=tmp_path)
        candidates = [
            make_candidate("2301.00001", "Paper 1"),
            make_candidate("2301.00002", "Paper 2"),
        ]

        count = store.append_papers("test-namespace", candidates)

        assert count == 2
        papers_file = tmp_path / "test-namespace_papers.json"
        assert papers_file.exists()
        with open(papers_file, encoding="utf-8") as f:
            saved_papers = json.load(f)
        assert len(saved_papers) == 2
        assert saved_papers[0]["arxiv_id"] == "2301.00001"
        assert saved_papers[1]["arxiv_id"] == "2301.00002"

    def test_append_papers_duplicate(self, tmp_path):
        """Should skip duplicate papers based on arxiv_id."""
        store = LocalStore(artifacts_dir=tmp_path)
        papers_file = tmp_path / "test-namespace_papers.json"
        existing_paper = make_candidate("2301.00001", "Existing Paper")
        papers_file.write_text(
            json.dumps([existing_paper.model_dump()]),
            encoding="utf-8",
        )

        candidates = [
            make_candidate("2301.00001", "Duplicate Paper"),  # duplicate
            make_candidate("2301.00002", "New Paper"),  # new
        ]
        count = store.append_papers("test-namespace", candidates)

        assert count == 1  # Only new paper added
        with open(papers_file, encoding="utf-8") as f:
            saved_papers = json.load(f)
        assert len(saved_papers) == 2
        # First paper should be unchanged (existing)
        assert saved_papers[0]["title"] == "Existing Paper"
        # Second paper should be the new one
        assert saved_papers[1]["arxiv_id"] == "2301.00002"

    def test_append_papers_all_duplicates(self, tmp_path):
        """Should return 0 when all papers are duplicates."""
        store = LocalStore(artifacts_dir=tmp_path)
        papers_file = tmp_path / "test-namespace_papers.json"
        existing = [make_candidate("2301.00001").model_dump()]
        papers_file.write_text(json.dumps(existing), encoding="utf-8")

        candidates = [make_candidate("2301.00001")]
        count = store.append_papers("test-namespace", candidates)

        assert count == 0


class TestSaveResult:
    """Tests for LocalStore.save_result method."""

    def test_save_result(self, tmp_path):
        """Should save SearchResult to JSON file and return path."""
        store = LocalStore(artifacts_dir=tmp_path)
        papers = [make_candidate("2301.00001"), make_candidate("2301.00002")]
        result = make_search_result(papers)

        saved_path = store.save_result("test-namespace", result)

        assert saved_path == tmp_path / "test-namespace_search_result.json"
        assert saved_path.exists()
        with open(saved_path, encoding="utf-8") as f:
            loaded = json.load(f)
        assert loaded["query_plan"]["queries"] == ["test query"]
        assert len(loaded["selected_papers"]) == 2
        assert loaded["ingest_summary"]["new_docs_added"] == 1


class TestCountPapers:
    """Tests for LocalStore.count_papers method."""

    def test_count_papers_empty(self, tmp_path):
        """Should return 0 when no papers file exists."""
        store = LocalStore(artifacts_dir=tmp_path)
        count = store.count_papers("test-namespace")
        assert count == 0

    def test_count_papers(self, tmp_path):
        """Should return correct count of papers in the file."""
        store = LocalStore(artifacts_dir=tmp_path)
        papers_file = tmp_path / "test-namespace_papers.json"
        papers = [
            {"arxiv_id": "2301.00001"},
            {"arxiv_id": "2301.00002"},
            {"arxiv_id": "2301.00003"},
        ]
        papers_file.write_text(json.dumps(papers), encoding="utf-8")

        count = store.count_papers("test-namespace")
        assert count == 3


class TestArtifactsDirectory:
    """Tests for artifacts directory handling."""

    def test_creates_artifacts_dir_on_init(self, tmp_path):
        """Should create artifacts directory if it doesn't exist."""
        artifacts_dir = tmp_path / "new_artifacts"
        assert not artifacts_dir.exists()

        LocalStore(artifacts_dir=artifacts_dir)

        assert artifacts_dir.exists()

    def test_accepts_string_path(self, tmp_path):
        """Should accept string path and convert to Path."""
        store = LocalStore(artifacts_dir=str(tmp_path))
        assert store.artifacts_dir == tmp_path
