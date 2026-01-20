import pytest
from research_agents.verifier.schemas import (
    VerifierRequest,
    VerifierResult,
    VerifierConstraints,
    QualityGate,
    QualityMetrics,
    ClaimJudgement,
    NextAction,
    ExtractorResult,
    Claim,
    Evidence,
)


def test_verifier_constraints_defaults():
    constraints = VerifierConstraints()
    assert constraints.evidence_min == 10
    assert constraints.unsupported_ratio_max == 0.25
    assert constraints.min_concept_coverage == 0.7
    assert constraints.max_loops == 3


def test_claim_judgement_status():
    judgement = ClaimJudgement(
        claim_id="claim_1",
        status="supported",
        evidence_valid=True,
        reason="Quote found in chunk"
    )
    assert judgement.status == "supported"


def test_next_action_types():
    action = NextAction(
        type="search_expand",
        priority=1,
        why="concept_coverage < 0.7",
        suggested_queries=["graph rag evaluation"],
        target_concepts=["Evaluation"]
    )
    assert action.type == "search_expand"
    assert len(action.suggested_queries) == 1


def test_quality_gate_pass():
    gate = QualityGate(passed=True, reasons=[])
    assert gate.passed is True


def test_verifier_result_structure():
    result = VerifierResult(
        quality_gate=QualityGate(passed=True, reasons=[]),
        metrics=QualityMetrics(),
        claim_judgements=[],
        next_actions=[]
    )
    assert result.quality_gate.passed is True
