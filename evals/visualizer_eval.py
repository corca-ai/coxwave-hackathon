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


def _items_min_chars(props: dict[str, Any], min_chars: int) -> bool:
    if min_chars <= 0:
        return True
    items = props.get("items")
    if not isinstance(items, list):
        return False
    cleaned = [str(item).strip() for item in items if str(item).strip()]
    if not cleaned:
        return False
    return all(len(item) >= min_chars for item in cleaned)


def _component_order(output: VisualOutput) -> list[str]:
    order: list[str] = []
    for comp in output.components:
        if hasattr(comp, "type"):
            order.append(str(comp.type))
    return order


def _order_matches(expected: list[str], actual: list[str]) -> bool:
    if not expected:
        return True
    index = 0
    for comp_type in actual:
        if comp_type == expected[index]:
            index += 1
            if index >= len(expected):
                return True
    return False


def _looks_like_url(value: str) -> bool:
    lowered = value.lower()
    return lowered.startswith("http://") or lowered.startswith("https://")


def score_output(sample: dict[str, Any], output: VisualOutput) -> dict[str, Any]:
    expected = sample.get("expect", {})
    required_types = expected.get("required_types", [])
    min_items = expected.get("min_items", {})
    min_item_chars = expected.get("min_item_chars", {})
    component_order = expected.get("component_order", [])
    require_callout_title = bool(expected.get("require_callout_title", False))
    validate_urls = bool(expected.get("validate_urls", False))
    min_rationale_chars = int(expected.get("min_rationale_chars", 0))

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
    if require_callout_title:
        checks["callout_title"] = bool(str(callout_props.get("title") or "").strip())
        if not checks["callout_title"]:
            notes.append("Callout missing title")
    else:
        checks["callout_title"] = True

    list_props = components.get("list", {})
    min_list = int(min_items.get("list", 0))
    checks["list_items"] = _items_len(list_props) >= min_list
    if not checks["list_items"]:
        notes.append("List items too short")
    if validate_urls and _items_len(list_props) > 0:
        items = list_props.get("items")
        checks["list_urls"] = isinstance(items, list) and all(
            _looks_like_url(str(item).strip()) for item in items if str(item).strip()
        )
        if not checks["list_urls"]:
            notes.append("List items are not valid URLs")
    else:
        checks["list_urls"] = True

    bullets_min_chars = int(min_item_chars.get("bullets", 0))
    checks["bullets_min_chars"] = _items_min_chars(bullets_props, bullets_min_chars)
    if not checks["bullets_min_chars"]:
        notes.append("Bullets items too short (chars)")

    callout_min_chars = int(min_item_chars.get("callout", 0))
    checks["callout_min_chars"] = _items_min_chars(callout_props, callout_min_chars)
    if not checks["callout_min_chars"]:
        notes.append("Callout items too short (chars)")

    list_min_chars = int(min_item_chars.get("list", 0))
    checks["list_min_chars"] = _items_min_chars(list_props, list_min_chars)
    if not checks["list_min_chars"]:
        notes.append("List items too short (chars)")

    checks["component_order"] = _order_matches(component_order, _component_order(output))
    if not checks["component_order"]:
        notes.append("Component order mismatch")

    rationale = str(output.rationale or "").strip()
    checks["rationale_present"] = bool(rationale)
    if not checks["rationale_present"]:
        notes.append("Missing rationale")
    if min_rationale_chars > 0:
        checks["rationale_min_chars"] = len(rationale) >= min_rationale_chars
        if not checks["rationale_min_chars"]:
            notes.append("Rationale too short")
    else:
        checks["rationale_min_chars"] = True

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
