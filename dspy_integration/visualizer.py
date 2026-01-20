from __future__ import annotations

import json
from dataclasses import asdict, replace
from typing import Any, AsyncGenerator, Optional

from .utils import configure_dspy, dspy, require_dspy, resolve_dspy_settings
from main import VisualComponent, VisualOutput
from stream_events import StreamEvent, StreamEventTypes


def _coerce_str_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item) for item in value if str(item).strip()]
    return [str(value)]


def _parse_report_context(context: str) -> dict[str, Any]:
    try:
        payload = json.loads(context)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Visualizer input must be JSON: {exc}") from exc
    if not isinstance(payload, dict):
        raise ValueError("Visualizer input JSON must be an object.")
    return payload


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
        if isinstance(comp, VisualComponent):
            comp_type = (comp.type or "").strip()
            if not comp_type:
                continue
            props = comp.props if isinstance(comp.props, dict) else {}
            components.append(VisualComponent(type=comp_type, props=props))
        elif isinstance(comp, dict):
            comp_type = str(comp.get("type") or "").strip()
            if not comp_type:
                continue
            props = comp.get("props") if isinstance(comp.get("props"), dict) else {}
            components.append(VisualComponent(type=comp_type, props=props))

    components = _schema_validate_components(components)

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


def _schema_validate_components(components: list[VisualComponent]) -> list[VisualComponent]:
    """Light schema validation pass to drop malformed components."""
    valid: list[VisualComponent] = []
    for comp in components:
        if not isinstance(comp, VisualComponent):
            continue
        comp_type = (comp.type or "").strip()
        if not comp_type:
            continue
        props = comp.props if isinstance(comp.props, dict) else {}
        if comp_type == "heading":
            if not str(props.get("text") or "").strip():
                continue
        elif comp_type == "paragraph":
            if not str(props.get("text") or "").strip():
                continue
        elif comp_type in {"bullets", "list"}:
            items = props.get("items")
            if not isinstance(items, list) or not [item for item in items if str(item).strip()]:
                continue
        elif comp_type == "callout":
            has_items = isinstance(props.get("items"), list) and [item for item in props.get("items") if str(item).strip()]
            has_text = bool(str(props.get("text") or "").strip())
            if not (has_items or has_text):
                continue
        valid.append(comp)
    return valid


def prediction_to_output(prediction: Any, report: dict[str, Any]) -> VisualOutput:
    components = getattr(prediction, "components", None)
    rationale = getattr(prediction, "rationale", "")
    output = VisualOutput(
        components=components if isinstance(components, list) else [],
        rationale=str(rationale) if rationale is not None else "",
    )
    return _normalize_visual_output(output, report)


if dspy is not None:

    class VisualizeSignature(dspy.Signature):
        """Convert report JSON into UI components."""

        report_json: str = dspy.InputField(desc="Report JSON string")
        components: list[dict] = dspy.OutputField(desc="List of UI components")
        rationale: str = dspy.OutputField(desc="Why these components were chosen")


    class VisualizerModule(dspy.Module):
        def __init__(self) -> None:
            super().__init__()
            self.predict = dspy.ChainOfThought(VisualizeSignature)

        def forward(self, report_json: str) -> Any:
            return self.predict(report_json=report_json)


class DSPyVisualizer:
    def __init__(
        self,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        module: Optional[Any] = None,
        configure: bool = True,
    ) -> None:
        require_dspy()
        settings = resolve_dspy_settings(
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            agent_name="visualizer",
        )
        if configure:
            configure_dspy(settings)
        self._module = module or VisualizerModule()

    def run(self, context: str) -> VisualOutput:
        report = _parse_report_context(context)
        prediction = self._module(report_json=json.dumps(report, ensure_ascii=True))
        return prediction_to_output(prediction, report)

    async def run_stream(self, context: str) -> AsyncGenerator[StreamEvent, None]:
        seq = 0
        yield StreamEvent(
            type=StreamEventTypes.AGENT_START,
            payload={"input": context},
            agent="visualizer",
            sequence=seq,
        )
        seq += 1
        try:
            output = self.run(context)
            yield StreamEvent(
                type=StreamEventTypes.AGENT_COMPLETE,
                payload={"output": asdict(output)},
                agent="visualizer",
                sequence=seq,
            )
        except Exception as exc:
            yield StreamEvent(
                type=StreamEventTypes.ERROR,
                payload={"error": str(exc), "error_type": type(exc).__name__},
                agent="visualizer",
                sequence=seq,
            )
            raise
