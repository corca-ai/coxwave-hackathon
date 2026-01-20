"""Search tools for the search agent."""

from agents import function_tool

from agents.search.clients.arxiv_client import ArxivClient, ArxivSearchParams
from agents.search.dedup import dedupe_candidates
from agents.search.ranking import rank_candidates
from agents.search.schemas import Candidate


def _search_sources_impl(
    queries: list[str],
    sources: list[str] = ["arxiv"],
    max_results: int = 80,
    time_range_years: int = 7,
    categories: list[str] | None = None,
) -> list[Candidate]:
    """
    Search for documents across specified sources.

    Args:
        queries: List of search queries (combined with OR).
        sources: List of sources to search ["arxiv", "internal"].
        max_results: Maximum number of candidates to return.
        time_range_years: Search time range (last N years).
        categories: Category filters (e.g., ["cs.AI", "cs.CL"]).

    Returns:
        List of candidate documents (ranked and deduplicated).
    """
    all_candidates: list[Candidate] = []

    for source in sources:
        if source == "arxiv":
            client = ArxivClient()
            params = ArxivSearchParams(
                queries=queries,
                max_results=max_results,
                time_range_years=time_range_years,
                categories=categories,
            )
            candidates = client.search(params)
            all_candidates.extend(candidates)
        elif source == "internal":
            pass  # TODO: v1.1

    deduped = dedupe_candidates(all_candidates)

    keywords = []
    for q in queries:
        keywords.extend(q.lower().split())
    ranked = rank_candidates(deduped, keywords, max_results=max_results)

    return ranked


# Wrap the implementation function as a FunctionTool for use with Agent
search_sources = function_tool(_search_sources_impl)
