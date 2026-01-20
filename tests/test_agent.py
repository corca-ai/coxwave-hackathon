"""Tests for SearchAgent definition."""


def test_agent_has_correct_name():
    from agents.search.agent import search_agent

    assert search_agent.name == "SearchAgent"


def test_agent_has_tools():
    from agents.search.agent import search_agent

    tool_names = [t.name for t in search_agent.tools]
    assert "_search_sources_impl" in tool_names


def test_agent_has_all_required_tools():
    from agents.search.agent import search_agent

    tool_names = [t.name for t in search_agent.tools]
    assert "_search_sources_impl" in tool_names
    assert "_rag_ingest_candidates_impl" in tool_names
    assert "_rag_preview_impl" in tool_names


def test_agent_has_output_type():
    from agents.search.agent import search_agent
    from agents.search.schemas import SearchResult

    assert search_agent.output_type == SearchResult


def test_agent_has_model():
    from agents.search.agent import search_agent

    assert search_agent.model == "gpt-4o-mini"


def test_agent_has_instructions():
    from agents.search.agent import search_agent

    assert "연구 논문 검색 에이전트" in search_agent.instructions
    assert "search_sources" in search_agent.instructions
    assert "rag_ingest_candidates" in search_agent.instructions
