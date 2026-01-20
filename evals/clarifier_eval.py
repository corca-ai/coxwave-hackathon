from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import Any

from evals.io import load_jsonl
from evals.specs import EvalSpec
from main import ClarifyOutput, DemoAgents


def load_samples(path: Path) -> list[dict[str, Any]]:
    return load_jsonl(path)


def build_input(sample: dict[str, Any]) -> str:
    query = sample.get("query")
    if not isinstance(query, str) or not query.strip():
        raise ValueError("Sample is missing a non-empty 'query' string")
    return query


def run_agent(agents: DemoAgents, agent_input: str) -> ClarifyOutput:
    return agents.clarifier.run(agent_input)


def output_to_json(output: ClarifyOutput) -> dict[str, Any]:
    return asdict(output)


def score_output(sample: dict[str, Any], output: ClarifyOutput) -> dict[str, Any]:
    expected = sample.get("expect", {})
    expect_clear = expected.get("is_clear_enough")
    min_questions = expected.get("min_questions", 0)

    if not isinstance(min_questions, int) or min_questions < 0:
        raise ValueError("'min_questions' must be a non-negative int")

    checks: dict[str, bool] = {}
    notes: list[str] = []

    if expect_clear is None:
        checks["is_clear_enough_match"] = True
    else:
        checks["is_clear_enough_match"] = output.is_clear_enough == expect_clear
        if not checks["is_clear_enough_match"]:
            notes.append(
                f"Expected is_clear_enough={expect_clear} but got {output.is_clear_enough}"
            )

    question_count = len(output.clarifying_questions)
    checks["min_questions_ok"] = question_count >= min_questions
    if not checks["min_questions_ok"]:
        notes.append(
            f"Expected >= {min_questions} clarifying questions but got {question_count}"
        )

    checks["interpreted_query_present"] = bool(output.interpreted_query)
    if not checks["interpreted_query_present"]:
        notes.append("interpreted_query is empty")

    checks["assumptions_is_list"] = isinstance(output.assumptions, list)
    if not checks["assumptions_is_list"]:
        notes.append("assumptions is not a list")

    score_total = sum(1 for value in checks.values() if value)
    score = score_total / len(checks) if checks else 0.0

    return {
        "passed": all(checks.values()),
        "score": round(score, 4),
        "checks": checks,
        "notes": notes,
        "expected": expected,
        "question_count": question_count,
    }


def build_spec() -> EvalSpec:
    return EvalSpec(
        name="clarifier",
        default_dataset=Path("evals/datasets/clarifier.jsonl"),
        load_samples=load_samples,
        build_input=build_input,
        run_agent=run_agent,
        score_output=score_output,
        output_to_json=output_to_json,
    )
