"""arXiv API client for paper search."""

import re
from datetime import datetime
from dataclasses import dataclass

import arxiv

from agent.search.schemas import Candidate


@dataclass
class ArxivSearchParams:
    """Parameters for arXiv search."""

    queries: list[str]
    max_results: int = 80
    time_range_years: int = 7
    categories: list[str] | None = None


class ArxivClient:
    """Client for searching papers on arXiv."""

    def __init__(self):
        """Initialize the arXiv client."""
        self.client = arxiv.Client()

    def search(self, params: ArxivSearchParams) -> list[Candidate]:
        """Search arXiv for papers matching the given parameters.

        Args:
            params: Search parameters including queries and filters.

        Returns:
            List of Candidate objects representing matching papers.
        """
        query = self._build_query(params)
        search = arxiv.Search(
            query=query,
            max_results=params.max_results,
            sort_by=arxiv.SortCriterion.SubmittedDate,
            sort_order=arxiv.SortOrder.Descending,
        )
        candidates = []
        min_year = None
        if params.time_range_years and params.time_range_years > 0:
            current_year = datetime.now().year
            min_year = current_year - params.time_range_years + 1
        for result in self.client.results(search):
            candidate = self._parse_result(result)
            if candidate is None:
                continue
            if min_year is not None and candidate.year < min_year:
                continue
            candidates.append(candidate)
        return candidates

    def _build_query(self, params: ArxivSearchParams) -> str:
        """Build the arXiv query string from search parameters.

        Args:
            params: Search parameters.

        Returns:
            Query string for arXiv API.
        """
        query_parts = [f'all:"{q}"' for q in params.queries]
        query = " OR ".join(query_parts)
        if params.categories:
            cat_parts = [f"cat:{cat}" for cat in params.categories]
            cat_query = " OR ".join(cat_parts)
            query = f"({query}) AND ({cat_query})"
        return query

    def _parse_result(self, result) -> Candidate | None:
        """Parse an arxiv.Result into a Candidate object.

        Args:
            result: An arxiv.Result object from the API.

        Returns:
            Candidate object or None if parsing fails.
        """
        try:
            arxiv_id = self._extract_arxiv_id(result.entry_id)
            return Candidate(
                arxiv_id=arxiv_id,
                title=result.title.replace("\n", " ").strip(),
                year=result.published.year,
                authors=[str(a) for a in result.authors],
                abstract=result.summary.replace("\n", " ").strip(),
                url=result.entry_id,
                pdf_url=result.pdf_url,
                categories=list(result.categories),
            )
        except Exception:
            return None

    def _extract_arxiv_id(self, entry_id: str) -> str:
        """Extract the arXiv ID from an entry URL.

        Args:
            entry_id: The full entry URL (e.g., http://arxiv.org/abs/2301.00001v1).

        Returns:
            The extracted arXiv ID (e.g., 2301.00001).

        Raises:
            ValueError: If the ID cannot be extracted.
        """
        # Try new format (YYMM.NNNNN)
        match = re.search(r"(\d{4}\.\d{4,5})", entry_id)
        if match:
            return match.group(1)
        # Try old format (category/number)
        match = re.search(r"([a-z-]+/\d+)", entry_id)
        if match:
            return match.group(1)
        raise ValueError(f"Cannot extract arxiv_id from {entry_id}")
