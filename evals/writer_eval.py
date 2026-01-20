from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

from evals.io import load_jsonl
from evals.specs import EvalSpec
from main import DemoAgents, ReportOutput


def load_samples(path: Path) -> list[dict[str, Any]]:
    return load_jsonl(path)


def build_input(sample: dict[str, Any]) -> str:
    context = sample.get("context")
    if not isinstance(context, dict):
        raise ValueError("Sample is missing a context object")
    return json.dumps(context, ensure_ascii=True)


def run_agent(agents: DemoAgents, agent_input: str) -> ReportOutput:
    return agents.writer.run(agent_input)


def output_to_json(output: ReportOutput) -> dict[str, Any]:
    return asdict(output)


def score_output(sample: dict[str, Any], output: ReportOutput) -> dict[str, Any]:
    expected = sample.get("expect", {})
    min_key_findings = int(expected.get("min_key_findings", 1))
    min_citations = int(expected.get("min_citations", 1))
    require_limitations = bool(expected.get("require_limitations", False))

    checks: dict[str, bool] = {}
    notes: list[str] = []

    checks["title_present"] = bool(output.title and output.title.strip())
    if not checks["title_present"]:
        notes.append("Missing title")

    checks["summary_present"] = bool(output.executive_summary and output.executive_summary.strip())
    if not checks["summary_present"]:
        notes.append("Missing executive_summary")

    checks["min_key_findings"] = len(output.key_findings) >= min_key_findings
    if not checks["min_key_findings"]:
        notes.append(f"Expected >= {min_key_findings} key findings")

    checks["min_citations"] = len(output.citations) >= min_citations
    if not checks["min_citations"]:
        notes.append(f"Expected >= {min_citations} citations")

    if require_limitations:
        checks["limitations_present"] = len(output.limitations) > 0
        if not checks["limitations_present"]:
            notes.append("Missing limitations")
    else:
        checks["limitations_present"] = True

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
        name="writer",
        default_dataset=Path("evals/datasets/writer.jsonl"),
        load_samples=load_samples,
        build_input=build_input,
        run_agent=run_agent,
        score_output=score_output,
        output_to_json=output_to_json,
    )
