from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

from evals.io import load_jsonl
from evals.specs import EvalSpec
from main import DemoAgents, VerifyOutput


def load_samples(path: Path) -> list[dict[str, Any]]:
    return load_jsonl(path)


def build_input(sample: dict[str, Any]) -> str:
    extract = sample.get("extract")
    if not isinstance(extract, dict):
        raise ValueError("Sample is missing an extract object")
    return json.dumps(extract, ensure_ascii=True)


def run_agent(agents: DemoAgents, agent_input: str) -> VerifyOutput:
    return agents.verifier.run(agent_input)


def output_to_json(output: VerifyOutput) -> dict[str, Any]:
    return asdict(output)


def score_output(sample: dict[str, Any], output: VerifyOutput) -> dict[str, Any]:
    expected = sample.get("expect", {})
    min_verdicts = int(expected.get("min_verdicts", 1))
    require_next_actions = bool(expected.get("require_next_actions", False))
    expected_is_enough = expected.get("is_enough")

    checks: dict[str, bool] = {}
    notes: list[str] = []

    checks["min_verdicts"] = len(output.verdicts) >= min_verdicts
    if not checks["min_verdicts"]:
        notes.append(f"Expected >= {min_verdicts} verdicts")

    allowed = {"supported", "weak", "unsupported", "conflicting"}
    verdict_fields_ok = True
    for verdict in output.verdicts:
        if not (verdict.claim and verdict.verdict and verdict.rationale):
            verdict_fields_ok = False
            break
        if verdict.verdict not in allowed:
            verdict_fields_ok = False
            break
        if verdict.confidence < 0.0 or verdict.confidence > 1.0:
            verdict_fields_ok = False
            break
    checks["verdict_fields"] = verdict_fields_ok
    if not verdict_fields_ok:
        notes.append("Invalid verdict fields")

    if expected_is_enough is None:
        checks["is_enough_match"] = True
    else:
        checks["is_enough_match"] = output.is_enough == expected_is_enough
        if not checks["is_enough_match"]:
            notes.append("is_enough mismatch")

    if require_next_actions and not output.is_enough:
        checks["has_next_actions"] = bool(output.next_actions or output.next_search_queries)
        if not checks["has_next_actions"]:
            notes.append("Missing next actions or queries")
    else:
        checks["has_next_actions"] = True

    score_total = sum(1 for value in checks.values() if value)
    score = score_total / len(checks) if checks else 0.0

    return {
        "passed": all(checks.values()),
        "score": round(score, 4),
        "checks": checks,
        "notes": notes,
        "expected": expected,
    }


def build_spec() -> EvalSpec:
    return EvalSpec(
        name="verifier",
        default_dataset=Path("evals/datasets/verifier.jsonl"),
        load_samples=load_samples,
        build_input=build_input,
        run_agent=run_agent,
        score_output=score_output,
        output_to_json=output_to_json,
    )
