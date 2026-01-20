"""Ranking logic for candidate papers."""

from datetime import datetime

from agents.search.schemas import Candidate


def calculate_score(candidate: Candidate, keywords: list[str]) -> float:
    """Calculate ranking score for a candidate paper.

    Score is composed of:
    - keyword_match (60%): Proportion of keywords found in title/abstract
    - recency (40%): Papers from current year get 1.0, decreasing by 0.1 per year

    Args:
        candidate: The candidate paper to score.
        keywords: List of keywords to match against.

    Returns:
        Score between 0.0 and 1.0, rounded to 4 decimal places.
    """
    text = f"{candidate.title} {candidate.abstract}".lower()
    keyword_hits = sum(1 for kw in keywords if kw.lower() in text)
    keyword_score = min(keyword_hits / max(len(keywords), 1), 1.0)

    current_year = datetime.now().year
    years_old = current_year - candidate.year
    recency_score = max(0, 1 - (years_old / 10))

    return round((keyword_score * 0.6) + (recency_score * 0.4), 4)


def rank_candidates(
    candidates: list[Candidate],
    keywords: list[str],
    max_results: int | None = None,
) -> list[Candidate]:
    """Rank and sort candidate papers by computed score.

    Args:
        candidates: List of candidate papers to rank.
        keywords: Keywords to use for scoring.
        max_results: Optional limit on number of results to return.

    Returns:
        List of candidates sorted by score in descending order.
    """
    for c in candidates:
        c.score = calculate_score(c, keywords)
    sorted_candidates = sorted(candidates, key=lambda c: c.score, reverse=True)
    if max_results:
        return sorted_candidates[:max_results]
    return sorted_candidates
