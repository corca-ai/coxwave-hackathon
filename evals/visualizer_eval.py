from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

from evals.io import load_jsonl
from evals.specs import EvalSpec
from main import DemoAgents, VisualOutput


def load_samples(path: Path) -> list[dict[str, Any]]:
    return load_jsonl(path)


def build_input(sample: dict[str, Any]) -> str:
    report = sample.get("report")
    if not isinstance(report, dict):
        raise ValueError("Sample is missing a report object")
    return json.dumps(report, ensure_ascii=True)


def run_agent(agents: DemoAgents, agent_input: str) -> VisualOutput:
    return agents.visualizer.run(agent_input)


def output_to_json(output: VisualOutput) -> dict[str, Any]:
    return asdict(output)


def _component_by_type(output: VisualOutput) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for comp in output.components:
        if not hasattr(comp, "type"):
            continue
        comp_type = str(comp.type)
        props = comp.props if isinstance(comp.props, dict) else {}
        result[comp_type] = props
    return result


def _items_len(props: dict[str, Any]) -> int:
    items = props.get("items")
    if not isinstance(items, list):
        return 0
    return len([item for item in items if str(item).strip()])


def score_output(sample: dict[str, Any], output: VisualOutput) -> dict[str, Any]:
    expected = sample.get("expect", {})
    required_types = expected.get("required_types", [])
    min_items = expected.get("min_items", {})

    checks: dict[str, bool] = {}
    notes: list[str] = []

    components = _component_by_type(output)

    for comp_type in required_types:
        checks[f"has_{comp_type}"] = comp_type in components
        if not checks[f"has_{comp_type}"]:
            notes.append(f"Missing component type: {comp_type}")

    heading_props = components.get("heading", {})
    checks["heading_text"] = bool(str(heading_props.get("text") or "").strip())
    if not checks["heading_text"]:
        notes.append("Missing heading text")

    paragraph_props = components.get("paragraph", {})
    checks["paragraph_text"] = bool(str(paragraph_props.get("text") or "").strip())
    if not checks["paragraph_text"]:
        notes.append("Missing paragraph text")

    bullets_props = components.get("bullets", {})
    min_bullets = int(min_items.get("bullets", 0))
    checks["bullets_items"] = _items_len(bullets_props) >= min_bullets
    if not checks["bullets_items"]:
        notes.append("Bullets items too short")

    callout_props = components.get("callout", {})
    min_callout = int(min_items.get("callout", 0))
    callout_len = _items_len(callout_props)
    callout_text = str(callout_props.get("text") or "").strip()
    checks["callout_items"] = callout_len >= min_callout or bool(callout_text)
    if not checks["callout_items"]:
        notes.append("Callout missing items/text")

    list_props = components.get("list", {})
    min_list = int(min_items.get("list", 0))
    checks["list_items"] = _items_len(list_props) >= min_list
    if not checks["list_items"]:
        notes.append("List items too short")

    checks["rationale_present"] = bool(str(output.rationale or "").strip())
    if not checks["rationale_present"]:
        notes.append("Missing rationale")

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
        name="visualizer",
        default_dataset=Path("evals/datasets/visualizer.jsonl"),
        load_samples=load_samples,
        build_input=build_input,
        run_agent=run_agent,
        score_output=score_output,
        output_to_json=output_to_json,
    )
