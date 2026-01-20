from __future__ import annotations

import json
import os
from typing import Any, Optional

from main import SearchOutput, Source

from .utils import configure_dspy, dspy, require_dspy, resolve_dspy_settings

try:
    from agent.search.tools.search import _search_sources_impl
except Exception:  # pragma: no cover - optional dependency
    _search_sources_impl = None


def _coerce_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str):
        return [value] if value.strip() else []
    return [str(value)]


def _parse_context(context: str) -> dict[str, Any]:
    try:
        payload = json.loads(context)
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def _extract_goal(context: str, payload: dict[str, Any]) -> str:
    clarifier = payload.get("clarifier")
    if isinstance(clarifier, dict):
        final = clarifier.get("final")
        if isinstance(final, dict):
            interpreted = final.get("interpreted_query")
            if isinstance(interpreted, str) and interpreted.strip():
                return interpreted.strip()
        original = clarifier.get("original_query")
        if isinstance(original, str) and original.strip():
            return original.strip()
    original = payload.get("original_query")
    if isinstance(original, str) and original.strip():
        return original.strip()
    return context.strip() or "Unknown goal"


def _env_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if not value:
        return default
    try:
        return int(value)
    except ValueError:
        return default


def _select_queries(payload: dict[str, Any], goal: str) -> list[str]:
    for key in ("next_queries", "suggested_queries"):
        raw = payload.get(key)
        if isinstance(raw, list):
            queries = [str(item).strip() for item in raw if str(item).strip()]
            if queries:
                return queries
    return [goal]


def _candidate_to_source(candidate: Any, idx: int) -> Source:
    source_id = str(getattr(candidate, "arxiv_id", None) or f"candidate_{idx + 1}")
    title = str(getattr(candidate, "title", None) or "Untitled")
    url = str(getattr(candidate, "url", None) or "")
    snippet = str(getattr(candidate, "abstract", None) or "")
    why = str(getattr(candidate, "why_selected", None) or "Selected by DSPy searcher.")
    return Source(
        source_id=source_id,
        title=title,
        url=url,
        snippet=snippet,
        why_relevant=why,
    )


def _placeholder_sources(goal: str) -> list[Source]:
    return [
        Source(
            source_id="placeholder-1",
            title=f"Placeholder source for {goal}",
            url="https://example.com/placeholder-1",
            snippet=f"Auto-generated placeholder for {goal}.",
            why_relevant="Placeholder source (no external search results).",
        ),
        Source(
            source_id="placeholder-2",
            title=f"Secondary placeholder for {goal}",
            url="https://example.com/placeholder-2",
            snippet=f"Backup placeholder for {goal}.",
            why_relevant="Placeholder source (no external search results).",
        ),
    ]


def _sources_from_previous(payload: dict[str, Any]) -> list[Source]:
    previous = payload.get("previous_sources")
    if not isinstance(previous, list):
        return []
    sources: list[Source] = []
    for item in previous:
        if not isinstance(item, dict):
            continue
        source_id = str(item.get("source_id") or "")
        title = str(item.get("title") or "")
        url = str(item.get("url") or "")
        snippet = str(item.get("snippet") or "")
        why = str(item.get("why_relevant") or "")
        if not source_id or not title:
            continue
        sources.append(
            Source(
                source_id=source_id,
                title=title,
                url=url,
                snippet=snippet,
                why_relevant=why or "Reused from previous sources.",
            )
        )
    return sources


def prediction_to_queries(prediction: Any) -> tuple[str, list[str]]:
    refined_query = str(getattr(prediction, "refined_query", "") or "").strip()
    queries = _coerce_list(getattr(prediction, "search_queries", None))
    return refined_query, queries


if dspy is not None:

    class SearchSignature(dspy.Signature):
        """Generate refined search query and candidate queries from context JSON."""

        context_json: str = dspy.InputField(desc="Context JSON from planner/clarifier")
        refined_query: str = dspy.OutputField(desc="Refined search query")
        search_queries: list[str] = dspy.OutputField(desc="2-4 search queries")


    class SearcherModule(dspy.Module):
        def __init__(self) -> None:
            super().__init__()
            self.predict = dspy.ChainOfThought(SearchSignature)

        def forward(self, context_json: str) -> Any:
            return self.predict(context_json=context_json)


class DSPySearcher:
    def __init__(
        self,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        module: Optional[Any] = None,
        configure: bool = True,
    ) -> None:
        require_dspy()
        settings = resolve_dspy_settings(
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            agent_name="searcher",
        )
        if configure:
            configure_dspy(settings)
        self._module = module or SearcherModule()

    def run(self, context: str) -> SearchOutput:
        payload = _parse_context(context)
        goal = _extract_goal(context, payload)
        prediction = self._module(context_json=json.dumps(payload, ensure_ascii=True))
        refined_query, queries = prediction_to_queries(prediction)

        refined_query = refined_query or goal
        if not queries:
            queries = _select_queries(payload, refined_query)

        sources: list[Source] = []
        max_sources = max(1, _env_int("DSPY_SEARCH_MAX_SOURCES", 8))

        candidates: list[Any] = []
        if _search_sources_impl is not None:
            try:
                candidates = _search_sources_impl(
                    queries=queries,
                    max_results=max_sources * 4,
                    time_range_years=7,
                )
            except Exception:
                candidates = []

        for idx, candidate in enumerate(candidates[:max_sources]):
            sources.append(_candidate_to_source(candidate, idx))

        if not sources:
            sources = _sources_from_previous(payload)

        if not sources:
            sources = _placeholder_sources(refined_query)

        return SearchOutput(refined_query=refined_query, sources=sources)
