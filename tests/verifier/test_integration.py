"""
통합 테스트: 실제 API 호출 포함 (CI에서는 skip)
로컬에서 OPENAI_API_KEY 설정 후 실행:
  pytest tests/verifier/test_integration.py -v -m integration
"""
import pytest
import json
import os
from pathlib import Path


@pytest.fixture
def has_api_key():
    return bool(os.getenv("OPENAI_API_KEY"))


@pytest.fixture
def sample_extractor_result(tmp_path):
    """테스트용 Extractor 결과 생성"""
    papers = [
        {
            "arxiv_id": "2401.00001",
            "title": "Graph RAG for Scientific Papers",
            "year": 2024,
            "authors": ["Author A"],
            "abstract": "We propose a novel method for graph-based retrieval augmented generation. Our approach achieves 95% accuracy on benchmark datasets."
        }
    ]
    papers_file = tmp_path / "test_papers.json"
    with open(papers_file, "w") as f:
        json.dump(papers, f)

    extractor_result = {
        "paper_cards": papers,
        "claims": [
            {
                "claim_id": "c1",
                "doc_id": "2401.00001",
                "text": "Graph RAG achieves 95% accuracy",
                "evidence": {
                    "chunk_id": "abstract",
                    "quote": "achieves 95% accuracy on benchmark datasets"
                },
                "concept_tags": ["Performance", "Graph RAG"]
            }
        ],
        "concepts": [
            {"concept_id": "concept_1", "name": "Graph RAG", "description": ""}
        ],
        "graph": None
    }

    result_file = tmp_path / "extractor_result.json"
    with open(result_file, "w") as f:
        json.dump(extractor_result, f)

    return tmp_path, result_file


@pytest.mark.integration
def test_verifier_agent_full_flow(has_api_key, sample_extractor_result):
    if not has_api_key:
        pytest.skip("OPENAI_API_KEY not set")

    from agents import Runner
    from agent.verify.agent import verifier_agent
    from agent.verify.schemas import VerifierRequest, ExtractorResult
    from agent.verify.tools.rag import set_artifacts_dir

    tmp_path, result_file = sample_extractor_result
    set_artifacts_dir(tmp_path)

    with open(result_file) as f:
        extractor_data = json.load(f)

    request = VerifierRequest(
        goal="Graph RAG performance evaluation",
        namespace="test",
        extractor_result=ExtractorResult(**extractor_data)
    )

    # Agent 실행
    result = Runner.run_sync(verifier_agent, request.model_dump_json())

    # 검증
    assert result.final_output is not None
    assert hasattr(result.final_output, 'quality_gate')
    assert hasattr(result.final_output, 'metrics')
    assert hasattr(result.final_output, 'claim_judgements')

    # claim이 1개이고 evidence가 유효하면 supported여야 함
    if result.final_output.claim_judgements:
        judgement = result.final_output.claim_judgements[0]
        assert judgement.claim_id == "c1"
        # evidence_valid가 True면 supported 또는 weak
        if judgement.evidence_valid:
            assert judgement.status in ["supported", "weak"]


@pytest.mark.integration
def test_verifier_agent_empty_claims(has_api_key, tmp_path):
    """빈 claims도 정상 처리되어야 함"""
    if not has_api_key:
        pytest.skip("OPENAI_API_KEY not set")

    from agents import Runner
    from agent.verify.agent import verifier_agent
    from agent.verify.schemas import VerifierRequest, ExtractorResult
    from agent.verify.tools.rag import set_artifacts_dir

    set_artifacts_dir(tmp_path)

    # 빈 extractor result
    extractor_result = ExtractorResult(
        paper_cards=[],
        claims=[],
        concepts=[],
        graph=None
    )

    request = VerifierRequest(
        goal="Test empty claims",
        namespace="test",
        extractor_result=extractor_result
    )

    result = Runner.run_sync(verifier_agent, request.model_dump_json())

    # 빈 claims면 passed=true
    assert result.final_output is not None
    assert result.final_output.metrics.total_claims == 0
