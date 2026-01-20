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
    ReportOutput,
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


class OpenAIWriter:
    def __init__(self, model: Optional[str] = None, temperature: Optional[float] = None) -> None:
        load_env(keys=["OPENAI_API_KEY", "OPENAI_MODEL", "OPENAI_TEMPERATURE"])
        resolved_model = model or os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        temp_value = temperature
        if temp_value is None:
            temp_value = float(os.getenv("OPENAI_TEMPERATURE", "0.2"))
        self._agent = Agent(
            name="Writer",
            model=resolved_model,
            model_settings=ModelSettings(temperature=temp_value),
            output_type=ReportOutput,
            instructions=(
                "You synthesize a research report from the provided JSON input. "
                "Return a ReportOutput JSON with fields: title, executive_summary, key_findings, "
                "limitations, citations, suggested_visuals. "
                "Use supported_claims and sources to ground findings. "
                "Citations must be only URLs or source_id values present in sources. "
                "If evidence is limited, mention it in limitations. "
                "Keep findings concise and factual."
            ),
        )

    def run(self, context: str) -> ReportOutput:
        load_env(keys=["OPENAI_API_KEY"])
        if not os.getenv("OPENAI_API_KEY"):
            raise RuntimeError("OPENAI_API_KEY is not set.")
        payload = _parse_writer_context(context)
        result = Runner.run_sync(self._agent, context)
        output = result.final_output
        if not isinstance(output, ReportOutput):
            raise TypeError("Writer output is not ReportOutput")
        return _normalize_report_output(output, payload)


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


def _parse_writer_context(context: str) -> dict[str, Any]:
    try:
        payload = json.loads(context)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Writer input must be JSON: {exc}") from exc
    if not isinstance(payload, dict):
        raise ValueError("Writer input JSON must be an object.")
    return payload


def _extract_sources(payload: dict[str, Any]) -> list[dict[str, Any]]:
    sources_block = payload.get("sources")
    if isinstance(sources_block, dict):
        raw_sources = sources_block.get("sources")
    else:
        raw_sources = None
    sources: list[dict[str, Any]] = []
    if isinstance(raw_sources, list):
        for item in raw_sources:
            if isinstance(item, dict):
                sources.append(item)
    return sources


def _extract_supported_claims(payload: dict[str, Any]) -> list[str]:
    raw_claims = payload.get("supported_claims")
    claims: list[str] = []
    if isinstance(raw_claims, list):
        for item in raw_claims:
            if isinstance(item, dict):
                text = item.get("claim")
                if text:
                    claims.append(str(text))
            elif item:
                claims.append(str(item))
    return claims


def _allowed_citations(sources: list[dict[str, Any]]) -> list[str]:
    allowed: list[str] = []
    for source in sources:
        url = source.get("url")
        if url:
            allowed.append(str(url))
        source_id = source.get("source_id")
        if source_id:
            allowed.append(str(source_id))
    return allowed


def _dedupe(items: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        cleaned = item.strip()
        if not cleaned or cleaned in seen:
            continue
        seen.add(cleaned)
        result.append(cleaned)
    return result


def _default_report_output(payload: dict[str, Any]) -> ReportOutput:
    clarifier = payload.get("clarifier") if isinstance(payload.get("clarifier"), dict) else {}
    original_query = ""
    interpreted_query = ""
    if isinstance(clarifier, dict):
        original_query = str(clarifier.get("original_query") or "")
        final_block = clarifier.get("final")
        if isinstance(final_block, dict):
            interpreted_query = str(final_block.get("interpreted_query") or "")

    query = interpreted_query or original_query or "Research Report"
    title = f"Report: {query}" if query else "Research Report"

    sources = _extract_sources(payload)
    supported_claims = _extract_supported_claims(payload)

    if supported_claims:
        key_findings = supported_claims
        executive_summary = (
            f"Summary based on {len(supported_claims)} supported claims "
            f"and {len(sources)} sources."
        )
    else:
        key_findings = []
        executive_summary = "No supported claims were provided; summary is limited."

    limitations = ["Limited to the provided sources and supported claims."]
    if not supported_claims:
        limitations.append("No supported claims were provided.")
    if not sources:
        limitations.append("No sources were provided.")

    citations = _allowed_citations(sources)
    if not citations:
        citations = []

    suggested_visuals = []
    if key_findings:
        suggested_visuals.append("Bullet list of key findings")
    if citations:
        suggested_visuals.append("Citations list")
    if not suggested_visuals:
        suggested_visuals.append("Summary paragraph")

    return ReportOutput(
        title=title,
        executive_summary=executive_summary,
        key_findings=_dedupe(_coerce_str_list(key_findings)),
        limitations=_dedupe(_coerce_str_list(limitations)),
        citations=_dedupe(_coerce_str_list(citations)),
        suggested_visuals=_dedupe(_coerce_str_list(suggested_visuals)),
    )


def _normalize_report_output(output: ReportOutput, payload: dict[str, Any]) -> ReportOutput:
    default = _default_report_output(payload)
    title = output.title.strip() if output.title else default.title
    executive_summary = (
        output.executive_summary.strip()
        if output.executive_summary
        else default.executive_summary
    )
    key_findings = _dedupe(_coerce_str_list(output.key_findings)) or default.key_findings
    limitations = _dedupe(_coerce_str_list(output.limitations)) or default.limitations
    citations = _dedupe(_coerce_str_list(output.citations)) or default.citations
    suggested_visuals = (
        _dedupe(_coerce_str_list(output.suggested_visuals)) or default.suggested_visuals
    )

    allowed = _allowed_citations(_extract_sources(payload))
    if allowed:
        citations = [item for item in citations if item in allowed]
        if not citations:
            citations = default.citations

    if not key_findings:
        if "No supported claims were provided." not in limitations:
            limitations.append("No supported claims were provided.")

    if not _extract_sources(payload):
        if "No sources were provided." not in limitations:
            limitations.append("No sources were provided.")

    return ReportOutput(
        title=title,
        executive_summary=executive_summary,
        key_findings=_dedupe(key_findings),
        limitations=_dedupe(limitations),
        citations=_dedupe(citations),
        suggested_visuals=_dedupe(suggested_visuals),
    )


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
    load_env(
        keys=[
            "USE_DSPY_CLARIFIER",
            "DSPY_MODEL",
            "DSPY_TEMPERATURE",
            "DSPY_MAX_TOKENS",
        ]
    )
    clarifier = OpenAIClarifier()
    use_dspy = os.getenv("USE_DSPY_CLARIFIER", "").lower() in {"1", "true", "yes"}
    if use_dspy:
        try:
            from dspy_clarifier import DSPyClarifier
        except ImportError as exc:
            raise RuntimeError(
                "USE_DSPY_CLARIFIER is set but DSPy is unavailable."
            ) from exc
        clarifier = DSPyClarifier()
    return DemoAgents(
        clarifier=clarifier,
        planner=MockPlanner(),
        searcher=MockSearcher(),
        extractor=MockExtractor(),
        verifier=MockVerifier(),
        writer=OpenAIWriter(),
        visualizer=OpenAIVisualizer(),
    )
