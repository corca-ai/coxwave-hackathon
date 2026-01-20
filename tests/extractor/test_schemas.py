from agent.extract.schemas import ExtractorRequest, ExtractorResult, ExtractorConstraints
from agent.search.schemas import SearchResult, QueryPlan, IngestSummary


def _empty_search_result() -> SearchResult:
    return SearchResult(
        query_plan=QueryPlan(queries=[], time_range="", categories=[]),
        selected_papers=[],
        ingest_summary=IngestSummary(new_docs_added=0, duplicates_skipped=0),
    )


def test_extractor_constraints_defaults():
    constraints = ExtractorConstraints()
    assert constraints.max_claims == 8
    assert constraints.min_evidence_chars == 20
    assert constraints.allow_weak_claims is True
    assert constraints.include_concepts is False


def test_extractor_request_defaults():
    req = ExtractorRequest(goal="test", search_result=_empty_search_result())
    assert req.namespace == "default"
    assert req.goal == "test"


def test_extractor_result_defaults():
    result = ExtractorResult()
    assert result.paper_cards == []
    assert result.claims == []
    assert result.concepts == []
