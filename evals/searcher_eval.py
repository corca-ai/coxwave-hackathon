from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

from evals.io import load_jsonl
from evals.specs import EvalSpec
from main import DemoAgents, SearchOutput


def load_samples(path: Path) -> list[dict[str, Any]]:
    return load_jsonl(path)


def build_input(sample: dict[str, Any]) -> str:
    context = sample.get("context")
    if not isinstance(context, dict):
        raise ValueError("Sample is missing a context object")
    return json.dumps(context, ensure_ascii=True)


def run_agent(agents: DemoAgents, agent_input: str) -> SearchOutput:
    return agents.searcher.run(agent_input)


def output_to_json(output: SearchOutput) -> dict[str, Any]:
    return asdict(output)


def _source_has_fields(source: Any) -> bool:
    if not hasattr(source, "source_id"):
        return False
    fields = [source.source_id, source.title, source.url, source.snippet, source.why_relevant]
    return all(bool(str(field).strip()) for field in fields)


def score_output(sample: dict[str, Any], output: SearchOutput) -> dict[str, Any]:
    expected = sample.get("expect", {})
    min_sources = int(expected.get("min_sources", 2))
    require_unique_ids = bool(expected.get("require_unique_ids", True))

    checks: dict[str, bool] = {}
    notes: list[str] = []

    checks["refined_query_present"] = bool(output.refined_query and output.refined_query.strip())
    if not checks["refined_query_present"]:
        notes.append("Missing refined_query")

    checks["min_sources"] = len(output.sources) >= min_sources
    if not checks["min_sources"]:
        notes.append(f"Expected >= {min_sources} sources")

    checks["sources_have_fields"] = all(_source_has_fields(source) for source in output.sources)
    if not checks["sources_have_fields"]:
        notes.append("Some sources missing required fields")

    if require_unique_ids:
        ids = [source.source_id for source in output.sources]
        checks["unique_source_ids"] = len(ids) == len(set(ids))
        if not checks["unique_source_ids"]:
            notes.append("Duplicate source_id values")
    else:
        checks["unique_source_ids"] = True

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
        name="searcher",
        default_dataset=Path("evals/datasets/searcher.jsonl"),
        load_samples=load_samples,
        build_input=build_input,
        run_agent=run_agent,
        score_output=score_output,
        output_to_json=output_to_json,
    )
