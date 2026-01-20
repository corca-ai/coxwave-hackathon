from __future__ import annotations

import json
import os
from dataclasses import replace
from typing import Any, Optional

from agents import Agent, AgentOutputSchema, ModelSettings, Runner

from main import (
    ClarifyOutput,
    DemoAgents,
    MockExtractor,
    MockPlanner,
    MockSearcher,
    MockVerifier,
    MockWriter,
    VisualComponent,
    VisualOutput,
)
from env_loader import load_env


class OpenAIClarifier:
    def __init__(self, model: Optional[str] = None, temperature: Optional[float] = None) -> None:
        load_env(keys=["OPENAI_API_KEY", "OPENAI_MODEL", "OPENAI_TEMPERATURE"])
        resolved_model = model or os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        temp_value = temperature
        if temp_value is None:
            temp_value = float(os.getenv("OPENAI_TEMPERATURE", "0.2"))
        self._agent = Agent(
            name="Clarifier",
            model=resolved_model,
            model_settings=ModelSettings(temperature=temp_value),
            output_type=ClarifyOutput,
            instructions=(
                "You clarify a research query for a serious user. "
                "If the query is ambiguous or too short, ask 1-3 clarifying questions and set "
                "is_clear_enough=false. Otherwise, set is_clear_enough=true. "
                "Always return interpreted_query and assumptions (can be empty list). "
                "Keep questions short and concrete."
            ),
        )

    def run(self, query: str) -> ClarifyOutput:
        load_env(keys=["OPENAI_API_KEY"])
        if not os.getenv("OPENAI_API_KEY"):
            raise RuntimeError("OPENAI_API_KEY is not set.")
        result = Runner.run_sync(self._agent, query)
        output = result.final_output
        if not isinstance(output, ClarifyOutput):
            raise TypeError("Clarifier output is not ClarifyOutput")
        return _normalize_clarify_output(output, query)


def _normalize_clarify_output(output: ClarifyOutput, query: str) -> ClarifyOutput:
    interpreted_query = output.interpreted_query or query
    assumptions = output.assumptions or []
    clarifying_questions = output.clarifying_questions or []
    is_clear_enough = output.is_clear_enough

    if clarifying_questions and is_clear_enough:
        is_clear_enough = False

    if _is_ambiguous(query):
        if not clarifying_questions:
            clarifying_questions = [
                "What is the target domain or industry?",
                "What time range or scope should we focus on?",
            ]
        is_clear_enough = False
    elif not is_clear_enough and not clarifying_questions:
        clarifying_questions = ["What specific scope or constraints should we use?"]

    if len(clarifying_questions) > 3:
        clarifying_questions = clarifying_questions[:3]

    return replace(
        output,
        interpreted_query=interpreted_query,
        assumptions=assumptions,
        clarifying_questions=clarifying_questions,
        is_clear_enough=is_clear_enough,
    )


def _is_ambiguous(query: str) -> bool:
    return len(query.split()) <= 4


class OpenAIVisualizer:
    def __init__(self, model: Optional[str] = None, temperature: Optional[float] = None) -> None:
        load_env(keys=["OPENAI_API_KEY", "OPENAI_MODEL", "OPENAI_TEMPERATURE"])
        resolved_model = model or os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        temp_value = temperature
        if temp_value is None:
            temp_value = float(os.getenv("OPENAI_TEMPERATURE", "0.2"))
        self._agent = Agent(
            name="Visualizer",
            model=resolved_model,
            model_settings=ModelSettings(temperature=temp_value),
            output_type=AgentOutputSchema(VisualOutput, strict_json_schema=False),
            instructions=(
                "You convert a report JSON into a UI component spec. "
                "Return components with type+props only, JSON-serializable. "
                "Use types: heading, paragraph, bullets, callout, list. "
                "Map title->heading.text, executive_summary->paragraph.text, "
                "key_findings->bullets.items, limitations->callout.items, citations->list.items. "
                "Keep props simple and avoid markdown."
            ),
        )

    def run(self, context: str) -> VisualOutput:
        load_env(keys=["OPENAI_API_KEY"])
        if not os.getenv("OPENAI_API_KEY"):
            raise RuntimeError("OPENAI_API_KEY is not set.")
        report = _parse_report_context(context)
        result = Runner.run_sync(self._agent, context)
        output = result.final_output
        if not isinstance(output, VisualOutput):
            raise TypeError("Visualizer output is not VisualOutput")
        return _normalize_visual_output(output, report)


def _parse_report_context(context: str) -> dict[str, Any]:
    try:
        payload = json.loads(context)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Visualizer input must be JSON: {exc}") from exc
    if not isinstance(payload, dict):
        raise ValueError("Visualizer input JSON must be an object.")
    return payload


def _coerce_str_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item) for item in value if str(item).strip()]
    return [str(value)]


def _default_visual_output(report: dict[str, Any]) -> VisualOutput:
    title = str(report.get("title") or "Report")
    executive_summary = str(report.get("executive_summary") or "")
    key_findings = _coerce_str_list(report.get("key_findings"))
    limitations = _coerce_str_list(report.get("limitations"))
    citations = _coerce_str_list(report.get("citations"))

    components = [
        VisualComponent(type="heading", props={"text": title, "level": 1}),
        VisualComponent(type="paragraph", props={"text": executive_summary}),
        VisualComponent(type="bullets", props={"items": key_findings, "ordered": False}),
        VisualComponent(
            type="callout",
            props={"title": "Limitations", "items": limitations, "tone": "note"},
        ),
        VisualComponent(type="list", props={"title": "Citations", "items": citations}),
    ]
    return VisualOutput(components=components, rationale="Generated from report structure.")


def _normalize_props(
    component_type: str, props: Any, defaults: dict[str, Any]
) -> dict[str, Any]:
    merged: dict[str, Any] = dict(defaults)
    if not isinstance(props, dict):
        return merged

    if component_type == "heading":
        text = props.get("text")
        if isinstance(text, str) and text.strip():
            merged["text"] = text
        elif text is not None:
            merged["text"] = str(text)
        level = props.get("level")
        if isinstance(level, int) and 1 <= level <= 6:
            merged["level"] = level
    elif component_type == "paragraph":
        text = props.get("text")
        if isinstance(text, str) and text.strip():
            merged["text"] = text
        elif text is not None:
            merged["text"] = str(text)
    elif component_type in {"bullets", "list"}:
        merged["items"] = _coerce_str_list(props.get("items")) or merged.get("items", [])
        if component_type == "bullets":
            ordered = props.get("ordered")
            if isinstance(ordered, bool):
                merged["ordered"] = ordered
        if component_type == "list":
            title = props.get("title")
            if isinstance(title, str) and title.strip():
                merged["title"] = title
            elif title is not None:
                merged["title"] = str(title)
    elif component_type == "callout":
        title = props.get("title")
        if isinstance(title, str) and title.strip():
            merged["title"] = title
        elif title is not None:
            merged["title"] = str(title)
        text = props.get("text")
        if isinstance(text, str) and text.strip():
            merged["text"] = text
        elif text is not None:
            merged["text"] = str(text)
        items = _coerce_str_list(props.get("items"))
        if items:
            merged["items"] = items
        tone = props.get("tone")
        if tone in {"note", "info", "warning"}:
            merged["tone"] = tone

    for key, value in props.items():
        if key not in merged and value is not None:
            merged[key] = value
    return merged


def _normalize_visual_output(output: VisualOutput, report: dict[str, Any]) -> VisualOutput:
    default = _default_visual_output(report)
    raw_components = output.components or []
    components: list[VisualComponent] = []
    for comp in raw_components:
        if not isinstance(comp, VisualComponent):
            continue
        comp_type = (comp.type or "").strip()
        if not comp_type:
            continue
        props = comp.props if isinstance(comp.props, dict) else {}
        components.append(VisualComponent(type=comp_type, props=props))

    if not components:
        components = default.components

    by_type: dict[str, VisualComponent] = {comp.type: comp for comp in components}
    normalized: list[VisualComponent] = []
    for comp in components:
        if comp.type in {"heading", "paragraph", "bullets", "callout", "list"}:
            default_comp = next((d for d in default.components if d.type == comp.type), None)
            defaults = default_comp.props if default_comp else {}
            props = _normalize_props(comp.type, comp.props, defaults)
            normalized.append(VisualComponent(type=comp.type, props=props))
        else:
            normalized.append(comp)

    for default_comp in default.components:
        if default_comp.type not in by_type:
            normalized.append(default_comp)

    rationale = output.rationale.strip() if output.rationale else ""
    if not rationale:
        rationale = default.rationale

    return VisualOutput(components=normalized, rationale=rationale)


def build_agents() -> DemoAgents:
    return DemoAgents(
        clarifier=OpenAIClarifier(),
        planner=MockPlanner(),
        searcher=MockSearcher(),
        extractor=MockExtractor(),
        verifier=MockVerifier(),
        writer=MockWriter(),
        visualizer=OpenAIVisualizer(),
    )
