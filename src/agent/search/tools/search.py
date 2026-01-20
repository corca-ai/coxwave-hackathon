"""Search tools for the search agent."""

from agents import function_tool

from agent.search.clients.arxiv_client import ArxivClient, ArxivSearchParams
from agent.search.dedup import dedupe_candidates
from agent.search.ranking import rank_candidates
from agent.search.schemas import Candidate


def _search_sources_impl(
    queries: list[str],
    sources: list[str] | None = None,
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
    if not queries:
        return []
    if isinstance(queries, str):
        queries = [queries]
    if not isinstance(queries, list):
        return []
    queries = [str(q).strip() for q in queries if str(q).strip()]
    if not queries:
        return []

    if sources is None:
        sources = ["arxiv"]
    if isinstance(sources, str):
        sources = [sources]
    if not isinstance(sources, list):
        sources = ["arxiv"]

    if max_results <= 0:
        return []
    if time_range_years <= 0:
        time_range_years = 0

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
            try:
                candidates = client.search(params)
            except Exception:
                candidates = []
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
