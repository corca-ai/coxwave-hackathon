from __future__ import annotations

import json
from typing import Any, Optional

from main import ReportOutput

from .utils import configure_dspy, dspy, require_dspy, resolve_dspy_settings


def _coerce_str_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item) for item in value if str(item).strip()]
    return [str(value)]


def _parse_context(context: str) -> dict[str, Any]:
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
    if isinstance(payload.get("sources"), list):
        for item in payload.get("sources"):
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
    else:
        citations = default.citations

    if not key_findings:
        if "No supported claims were provided." not in limitations:
            limitations.append("No supported claims were provided.")
    elif len(key_findings) < 3:
        note = "Fewer than 3 key findings due to limited supported claims."
        if note not in limitations:
            limitations.append(note)

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


def prediction_to_output(prediction: Any, payload: dict[str, Any]) -> ReportOutput:
    output = ReportOutput(
        title=str(getattr(prediction, "title", "") or ""),
        executive_summary=str(getattr(prediction, "executive_summary", "") or ""),
        key_findings=_coerce_str_list(getattr(prediction, "key_findings", None)),
        limitations=_coerce_str_list(getattr(prediction, "limitations", None)),
        citations=_coerce_str_list(getattr(prediction, "citations", None)),
        suggested_visuals=_coerce_str_list(getattr(prediction, "suggested_visuals", None)),
    )
    return _normalize_report_output(output, payload)


if dspy is not None:

    class WriterSignature(dspy.Signature):
        """Synthesize a report from writer context JSON."""

        context_json: str = dspy.InputField(desc="Writer context JSON")
        title: str = dspy.OutputField(desc="Report title")
        executive_summary: str = dspy.OutputField(desc="Executive summary")
        key_findings: list[str] = dspy.OutputField(desc="Key findings")
        limitations: list[str] = dspy.OutputField(desc="Limitations")
        citations: list[str] = dspy.OutputField(desc="Citations list")
        suggested_visuals: list[str] = dspy.OutputField(desc="Suggested visuals")


    class WriterModule(dspy.Module):
        def __init__(self) -> None:
            super().__init__()
            self.predict = dspy.ChainOfThought(WriterSignature)

        def forward(self, context_json: str) -> Any:
            return self.predict(context_json=context_json)


class DSPyWriter:
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
            agent_name="writer",
        )
        if configure:
            configure_dspy(settings)
        self._module = module or WriterModule()

    def run(self, context: str) -> ReportOutput:
        payload = _parse_context(context)
        prediction = self._module(context_json=json.dumps(payload, ensure_ascii=True))
        return prediction_to_output(prediction, payload)
