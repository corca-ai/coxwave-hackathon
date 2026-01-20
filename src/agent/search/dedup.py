"""Deduplication logic for candidate papers."""

from agent.search.schemas import Candidate


def dedupe_candidates(
    candidates: list[Candidate],
    existing_ids: set[str] | None = None,
) -> list[Candidate]:
    """Remove duplicate candidates based on arxiv_id, preserving order.

    Args:
        candidates: List of candidate papers to deduplicate.
        existing_ids: Optional set of arxiv_ids to exclude from results.

    Returns:
        List of unique candidates in their original order.
    """
    seen: set[str] = existing_ids.copy() if existing_ids else set()
    result: list[Candidate] = []
    for c in candidates:
        if c.arxiv_id not in seen:
            seen.add(c.arxiv_id)
            result.append(c)
    return result
