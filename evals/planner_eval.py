from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

from evals.io import load_jsonl
from evals.specs import EvalSpec
from main import DemoAgents, PlanOutput


def load_samples(path: Path) -> list[dict[str, Any]]:
    return load_jsonl(path)


def _get_context(sample: dict[str, Any]) -> dict[str, Any]:
    context = sample.get("context")
    if isinstance(context, dict):
        return context
    clarifier = sample.get("clarifier")
    if isinstance(clarifier, dict):
        return clarifier
    raise ValueError("Sample is missing a context/clarifier object")


def build_input(sample: dict[str, Any]) -> str:
    context = _get_context(sample)
    return json.dumps(context, ensure_ascii=True)


def run_agent(agents: DemoAgents, agent_input: str) -> PlanOutput:
    return agents.planner.run(agent_input)


def output_to_json(output: PlanOutput) -> dict[str, Any]:
    return asdict(output)


def _contains_terms(text: str, terms: list[str]) -> bool:
    haystack = text.lower()
    return all(term.lower() in haystack for term in terms)


def score_output(sample: dict[str, Any], output: PlanOutput) -> dict[str, Any]:
    expected = sample.get("expect", {})
    min_steps = int(expected.get("min_steps", 3))
    min_success = int(expected.get("min_success_criteria", 1))
    min_data = int(expected.get("min_data_needs", 1))
    must_include_terms = expected.get("must_include_terms", [])

    checks: dict[str, bool] = {}
    notes: list[str] = []

    checks["plan_summary_present"] = bool(output.plan_summary and output.plan_summary.strip())
    if not checks["plan_summary_present"]:
        notes.append("Missing plan_summary")

    checks["steps_min"] = len(output.steps) >= min_steps
    if not checks["steps_min"]:
        notes.append(f"Expected >= {min_steps} steps")

    checks["success_criteria_min"] = len(output.success_criteria) >= min_success
    if not checks["success_criteria_min"]:
        notes.append(f"Expected >= {min_success} success criteria")

    checks["data_needs_min"] = len(output.data_needs) >= min_data
    if not checks["data_needs_min"]:
        notes.append(f"Expected >= {min_data} data needs")

    if isinstance(must_include_terms, list) and must_include_terms:
        combined = " ".join([output.plan_summary] + output.steps)
        checks["terms_present"] = _contains_terms(combined, [str(t) for t in must_include_terms])
        if not checks["terms_present"]:
            notes.append("Missing required terms")
    else:
        checks["terms_present"] = True

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
        name="planner",
        default_dataset=Path("evals/datasets/planner.jsonl"),
        load_samples=load_samples,
        build_input=build_input,
        run_agent=run_agent,
        score_output=score_output,
        output_to_json=output_to_json,
    )
