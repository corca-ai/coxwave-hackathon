import pytest
from agent.verify.agent import verifier_agent, VERIFIER_AGENT_INSTRUCTIONS


def test_agent_has_correct_name():
    assert verifier_agent.name == "VerifierAgent"


def test_agent_has_tools():
    tool_names = [t.name for t in verifier_agent.tools]
    assert "rag_get_chunk" in tool_names
    assert "kg_query" in tool_names


def test_agent_has_output_type():
    from agent.verify.schemas import VerifierResult
    assert verifier_agent.output_type == VerifierResult


def test_instructions_contain_key_concepts():
    assert "rag_get_chunk" in VERIFIER_AGENT_INSTRUCTIONS
    assert "quality_gate" in VERIFIER_AGENT_INSTRUCTIONS.lower()
    assert "next_actions" in VERIFIER_AGENT_INSTRUCTIONS
