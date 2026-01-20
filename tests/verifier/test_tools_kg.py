import pytest
from agent.verify.tools.kg import kg_query, _kg_query_impl


def test_kg_query_returns_empty():
    result = _kg_query_impl("SELECT ?s WHERE { ?s ?p ?o }")
    assert result == []


def test_kg_query_is_function_tool():
    from agents import FunctionTool
    assert isinstance(kg_query, FunctionTool)
