from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any, Optional

from agents import Agent, AgentOutputSchema, ModelSettings, Runner

from main import (
    ClarifyOutput,
    DemoAgents,
    ExtractOutput,
    Claim as MainClaim,
    MockOrchestrator,
    MockWriter,
    NextAction as MainNextAction,
    PlanOutput,
    MockPlanner,
    SearchOutput,
    Source,
    Verification as MainVerification,
    VerifyOutput,
    ReportOutput,
    VisualComponent,
    VisualOutput,
)
from env_loader import load_env

# Add src/ to path for agent imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

from agent.search.agent import search_agent
from agent.search.schemas import (
    Candidate,
    Constraints,
    IngestSummary,
    QueryPlan,
    SearchRequest,
    SearchResult,
)
from agent.search.tools.rag import set_artifacts_dir as set_search_artifacts_dir
from agent.extract.agent import extract_agent
from agent.extract.schemas import (
    Claim as ExtractClaim,
    Evidence as ExtractEvidence,
    ExtractorRequest,
    ExtractorResult,
    PaperCard as ExtractPaperCard,
)
from agent.verify.agent import verifier_agent
from agent.verify.schemas import (
    Claim as VerifyClaim,
    Evidence as VerifyEvidence,
    ExtractorResult as VerifyExtractorResult,
    VerifierConstraints,
    PaperCard as VerifyPaperCard,
    VerifierRequest,
    VerifierResult,
)
from agent.verify.tools.rag import set_artifacts_dir as set_verify_artifacts_dir
from agent.plan.agent import plan_agent
from agent.plan.schemas import PlannerRequest, PlannerResult


@dataclass
class PipelineState:
    namespace: str = "default"
    goal: str | None = None
    search_result: SearchResult | None = None
    extractor_result: ExtractorResult | None = None


_PIPELINE_STATE = PipelineState()


def _model_supports_sampling_params(model: str) -> bool:
    normalized = model.strip().lower()
    if normalized.startswith("gpt-5.2") or normalized.startswith("gpt-5.1"):
        return True
    if normalized.startswith("gpt-5"):
        return False
    return True


def _build_model_settings(model: str, temperature: Optional[float]) -> ModelSettings:
    if temperature is None:
        return ModelSettings()
    if not _model_supports_sampling_params(model):
        return ModelSettings()
    return ModelSettings(temperature=temperature)


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
            model_settings=_build_model_settings(resolved_model, temp_value),
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

def _get_default_namespace() -> str:
    load_env(keys=["AGENTS_NAMESPACE"])
    return os.getenv("AGENTS_NAMESPACE", "default")


def _get_artifacts_dir() -> str:
    load_env(keys=["ARTIFACTS_DIR"])
    return os.getenv("ARTIFACTS_DIR", "artifacts")


def _extract_search_options(context: str) -> tuple[str, int]:
    namespace = _get_default_namespace()
    target_new_docs = 12
    try:
        payload = json.loads(context)
    except json.JSONDecodeError:
        return namespace, target_new_docs
    if not isinstance(payload, dict):
        return namespace, target_new_docs
    if isinstance(payload.get("namespace"), str) and payload["namespace"].strip():
        namespace = payload["namespace"].strip()
    constraints = payload.get("constraints")
    if isinstance(constraints, dict):
        target = constraints.get("target_new_docs")
        if isinstance(target, int) and target > 0:
            target_new_docs = target
    return namespace, target_new_docs


def _extract_goal_from_context(context: str) -> str:
    try:
        payload = json.loads(context)
    except json.JSONDecodeError:
        return context.strip() or "Unknown goal"
    if not isinstance(payload, dict):
        return "Unknown goal"
    clarifier = payload.get("clarifier") or {}
    if isinstance(clarifier, dict):
        final = clarifier.get("final") or {}
        if isinstance(final, dict):
            interpreted = final.get("interpreted_query")
            if isinstance(interpreted, str) and interpreted.strip():
                return interpreted.strip()
        original = clarifier.get("original_query")
        if isinstance(original, str) and original.strip():
            return original.strip()
    return "Unknown goal"


class OpenAIPlanner:
    """Wrapper for plan_agent that implements the Planner protocol."""

    def __init__(self) -> None:
        load_env(keys=["OPENAI_API_KEY", "OPENAI_MODEL"])

    def run(self, context: str) -> PlanOutput:
        load_env(keys=["OPENAI_API_KEY"])
        if not os.getenv("OPENAI_API_KEY"):
            raise RuntimeError("OPENAI_API_KEY is not set.")

        # Extract goal from context
        goal = _extract_goal_from_context(context)

        # Create PlannerRequest
        request = PlannerRequest(
            goal=goal,
            namespace=_get_default_namespace(),
        )

        # Run plan_agent
        result = Runner.run_sync(plan_agent, request.model_dump_json())
        output = result.final_output
        if not isinstance(output, PlannerResult):
            raise TypeError("Planner output is not PlannerResult")

        # Convert PlannerResult to main.py PlanOutput
        return PlanOutput(
            plan_summary=output.plan_summary,
            steps=output.steps,
            success_criteria=output.success_criteria,
            data_needs=output.data_needs,
        )


class OpenAISearcher:
    def __init__(self, model: Optional[str] = None) -> None:
        load_env(keys=["OPENAI_API_KEY", "OPENAI_MODEL"])
        self._model = model or os.getenv("OPENAI_MODEL", "gpt-4o-mini")

    def run(self, context: str) -> SearchOutput:
        load_env(keys=["OPENAI_API_KEY"])
        if not os.getenv("OPENAI_API_KEY"):
            raise RuntimeError("OPENAI_API_KEY is not set.")

        goal = _extract_goal_from_context(context)
        namespace, target_new_docs = _extract_search_options(context)
        artifacts_dir = _get_artifacts_dir()
        set_search_artifacts_dir(Path(artifacts_dir))

        _PIPELINE_STATE.namespace = namespace
        _PIPELINE_STATE.goal = goal
        _PIPELINE_STATE.search_result = None
        _PIPELINE_STATE.extractor_result = None

        request = SearchRequest(
            goal=goal,
            namespace=namespace,
            constraints=Constraints(target_new_docs=target_new_docs),
        )

        result = Runner.run_sync(search_agent, request.model_dump_json())
        output = result.final_output
        if not isinstance(output, SearchResult):
            raise TypeError("Search output is not SearchResult")

        _PIPELINE_STATE.search_result = output

        sources = [
            Source(
                source_id=paper.arxiv_id,
                title=paper.title,
                url=paper.url,
                snippet=paper.abstract,
                why_relevant=paper.why_selected or "Selected by search agent.",
            )
            for paper in output.selected_papers
        ]

        return SearchOutput(refined_query=goal, sources=sources)


class OpenAIExtractor:
    def __init__(self) -> None:
        load_env(keys=["OPENAI_API_KEY", "OPENAI_MODEL"])

    def run(self, context: str) -> ExtractOutput:
        load_env(keys=["OPENAI_API_KEY"])
        if not os.getenv("OPENAI_API_KEY"):
            raise RuntimeError("OPENAI_API_KEY is not set.")

        namespace = _PIPELINE_STATE.namespace or _get_default_namespace()
        goal = _PIPELINE_STATE.goal or "Unknown goal"
        search_result = _PIPELINE_STATE.search_result

        if search_result is None:
            search_result = _fallback_search_result(context)

        request = ExtractorRequest(
            goal=goal,
            namespace=namespace,
            search_result=search_result,
        )

        result = Runner.run_sync(extract_agent, request.model_dump_json())
        output = result.final_output
        if not isinstance(output, ExtractorResult):
            raise TypeError("Extractor output is not ExtractorResult")

        _PIPELINE_STATE.extractor_result = _normalize_extractor_result(output, search_result)

        claims: list[MainClaim] = []
        for claim in _PIPELINE_STATE.extractor_result.claims:
            if claim.evidence is None:
                continue
            claims.append(
                MainClaim(
                    claim=claim.text,
                    evidence=claim.evidence.quote,
                    source_id=claim.doc_id,
                    confidence=claim.confidence,
                )
            )

        gaps = [] if claims else ["No claims extracted."]

        return ExtractOutput(claims=claims, gaps=gaps)


class OpenAIVerifier:
    def __init__(self) -> None:
        load_env(keys=["OPENAI_API_KEY", "OPENAI_MODEL"])

    def run(self, context: str) -> VerifyOutput:
        load_env(keys=["OPENAI_API_KEY"])
        if not os.getenv("OPENAI_API_KEY"):
            raise RuntimeError("OPENAI_API_KEY is not set.")

        namespace = _PIPELINE_STATE.namespace or _get_default_namespace()
        goal = _PIPELINE_STATE.goal or "Unknown goal"
        artifacts_dir = _get_artifacts_dir()
        set_verify_artifacts_dir(Path(artifacts_dir))

        extractor_result = _PIPELINE_STATE.extractor_result
        if extractor_result is None:
            extractor_result = _fallback_extractor_result(context)

        request = VerifierRequest(
            goal=goal,
            namespace=namespace,
            extractor_result=_to_verify_extractor_result(extractor_result),
            constraints=VerifierConstraints(),
        )

        result = Runner.run_sync(verifier_agent, request.model_dump_json())
        output = result.final_output
        if not isinstance(output, VerifierResult):
            raise TypeError("Verifier output is not VerifierResult")

        claim_lookup = {claim.claim_id: claim for claim in request.extractor_result.claims}
        verdicts: list[MainVerification] = []
        for judgement in output.claim_judgements:
            claim = claim_lookup.get(judgement.claim_id)
            confidence = _confidence_from_status(judgement.status)
            verdicts.append(
                MainVerification(
                    claim=claim.text if claim else judgement.claim_id,
                    verdict=judgement.status,
                    rationale=judgement.reason,
                    confidence=confidence,
                    source_id=claim.doc_id if claim else None,
                    required_evidence=[],
                )
            )

        queries: list[str] = []
        for action in output.next_actions:
            for query in action.suggested_queries:
                if query not in queries:
                    queries.append(query)

        # Convert next_actions to main.py format
        next_actions: list[MainNextAction] = []
        for action in output.next_actions:
            # Skip human_review actions
            if action.type == "human_review":
                continue
            next_actions.append(
                MainNextAction(
                    action_type=action.type,
                    priority=action.priority,
                    why=action.why,
                    suggested_queries=action.suggested_queries,
                    target_concepts=action.target_concepts,
                )
            )

        return VerifyOutput(
            verdicts=verdicts,
            is_enough=output.quality_gate.passed,
            next_search_queries=queries,
            next_actions=next_actions,
        )


def _fallback_search_result(context: str) -> SearchResult:
    try:
        payload = json.loads(context)
    except json.JSONDecodeError:
        payload = {}
    sources = []
    if isinstance(payload, dict):
        sources = payload.get("sources", [])

    candidates: list[Candidate] = []
    for idx, source in enumerate(sources):
        if not isinstance(source, dict):
            continue
        arxiv_id = str(source.get("source_id") or f"unknown_{idx}")
        candidates.append(
            Candidate(
                arxiv_id=arxiv_id,
                title=str(source.get("title") or "Untitled"),
                year=0,
                authors=[],
                abstract=str(source.get("snippet") or ""),
                url=str(source.get("url") or ""),
                pdf_url=None,
                categories=[],
                score=0.0,
                why_selected=str(source.get("why_relevant") or ""),
            )
        )

    return SearchResult(
        query_plan=QueryPlan(queries=[], time_range="", categories=[]),
        selected_papers=candidates,
        ingest_summary=IngestSummary(new_docs_added=0, duplicates_skipped=0),
        preview_snippets=[],
        errors=[],
    )


def _fallback_extractor_result(context: str) -> ExtractorResult:
    try:
        payload = json.loads(context)
    except json.JSONDecodeError:
        payload = {}
    claims = []
    if isinstance(payload, dict):
        claims = payload.get("claims", [])

    extracted_claims: list[ExtractClaim] = []
    for idx, item in enumerate(claims):
        if not isinstance(item, dict):
            continue
        evidence_text = str(item.get("evidence") or "").strip()
        evidence = (
            ExtractEvidence(chunk_id="abstract", quote=evidence_text)
            if evidence_text
            else None
        )
        extracted_claims.append(
            ExtractClaim(
                claim_id=f"c{idx + 1}",
                doc_id=str(item.get("source_id") or f"unknown_{idx}"),
                text=str(item.get("claim") or ""),
                evidence=evidence,
                concept_tags=[],
                confidence=float(item.get("confidence") or 0.0),
            )
        )

    return ExtractorResult(paper_cards=[], claims=extracted_claims, concepts=[], graph=None)


def _normalize_extractor_result(
    result: ExtractorResult,
    search_result: SearchResult | None,
) -> ExtractorResult:
    paper_cards = list(result.paper_cards)
    if not paper_cards and search_result is not None:
        paper_cards = [
            ExtractPaperCard(
                arxiv_id=paper.arxiv_id,
                title=paper.title,
                year=paper.year,
                authors=paper.authors,
                abstract=paper.abstract,
            )
            for paper in search_result.selected_papers
        ]

    concepts = result.concepts or []
    graph = result.graph
    return ExtractorResult(
        paper_cards=paper_cards,
        claims=result.claims,
        concepts=concepts,
        graph=graph,
    )


def _to_verify_extractor_result(result: ExtractorResult) -> VerifyExtractorResult:
    paper_cards = [
        VerifyPaperCard(
            arxiv_id=card.arxiv_id,
            title=card.title,
            year=card.year,
            authors=card.authors,
            abstract=card.abstract,
        )
        for card in result.paper_cards
    ]
    claims = [
        VerifyClaim(
            claim_id=claim.claim_id,
            doc_id=claim.doc_id,
            text=claim.text,
            evidence=(
                VerifyEvidence(
                    chunk_id=claim.evidence.chunk_id,
                    quote=claim.evidence.quote,
                    page=claim.evidence.page,
                )
                if claim.evidence
                else None
            ),
            concept_tags=claim.concept_tags,
            confidence=claim.confidence,
        )
        for claim in result.claims
    ]

    return VerifyExtractorResult(
        paper_cards=paper_cards,
        claims=claims,
        concepts=[],
        graph=None,
    )


def _confidence_from_status(status: str) -> float:
    return {
        "supported": 0.7,
        "weak": 0.4,
        "unsupported": 0.1,
        "conflicting": 0.2,
    }.get(status, 0.0)


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
            model_settings=_build_model_settings(resolved_model, temp_value),
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
            model_settings=_build_model_settings(resolved_model, temp_value),
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
            "USE_DSPY_ALL",
            "USE_DSPY_CLARIFIER",
            "USE_DSPY_PLANNER",
            "USE_DSPY_SEARCHER",
            "USE_DSPY_EXTRACTOR",
            "USE_DSPY_VERIFIER",
            "USE_DSPY_WRITER",
            "USE_DSPY_VISUALIZER",
            "DSPY_MODEL",
            "DSPY_TEMPERATURE",
            "DSPY_MAX_TOKENS",
            "DSPY_CLARIFIER_MODEL",
            "DSPY_CLARIFIER_TEMPERATURE",
            "DSPY_CLARIFIER_MAX_TOKENS",
            "DSPY_PLANNER_MODEL",
            "DSPY_PLANNER_TEMPERATURE",
            "DSPY_PLANNER_MAX_TOKENS",
            "DSPY_SEARCHER_MODEL",
            "DSPY_SEARCHER_TEMPERATURE",
            "DSPY_SEARCHER_MAX_TOKENS",
            "DSPY_EXTRACTOR_MODEL",
            "DSPY_EXTRACTOR_TEMPERATURE",
            "DSPY_EXTRACTOR_MAX_TOKENS",
            "DSPY_VERIFIER_MODEL",
            "DSPY_VERIFIER_TEMPERATURE",
            "DSPY_VERIFIER_MAX_TOKENS",
            "DSPY_WRITER_MODEL",
            "DSPY_WRITER_TEMPERATURE",
            "DSPY_WRITER_MAX_TOKENS",
            "DSPY_VISUALIZER_MODEL",
            "DSPY_VISUALIZER_TEMPERATURE",
            "DSPY_VISUALIZER_MAX_TOKENS",
        ]
    )
    def _env_flag(name: str) -> bool:
        return os.getenv(name, "").lower() in {"1", "true", "yes"}

    use_dspy_all = _env_flag("USE_DSPY_ALL")

    clarifier = OpenAIClarifier()
    if use_dspy_all or _env_flag("USE_DSPY_CLARIFIER"):
        try:
            from dspy_integration.clarifier import DSPyClarifier
        except ImportError as exc:
            raise RuntimeError(
                "USE_DSPY_CLARIFIER is set but DSPy is unavailable."
            ) from exc
        clarifier = DSPyClarifier()

    planner = OpenAIPlanner()
    if use_dspy_all or _env_flag("USE_DSPY_PLANNER"):
        try:
            from dspy_integration.planner import DSPyPlanner
        except ImportError as exc:
            raise RuntimeError("USE_DSPY_PLANNER is set but DSPy is unavailable.") from exc
        planner = DSPyPlanner()

    searcher = OpenAISearcher()
    if use_dspy_all or _env_flag("USE_DSPY_SEARCHER"):
        try:
            from dspy_integration.searcher import DSPySearcher
        except ImportError as exc:
            raise RuntimeError("USE_DSPY_SEARCHER is set but DSPy is unavailable.") from exc
        searcher = DSPySearcher()

    extractor = OpenAIExtractor()
    if use_dspy_all or _env_flag("USE_DSPY_EXTRACTOR"):
        try:
            from dspy_integration.extractor import DSPyExtractor
        except ImportError as exc:
            raise RuntimeError("USE_DSPY_EXTRACTOR is set but DSPy is unavailable.") from exc
        extractor = DSPyExtractor()

    verifier = OpenAIVerifier()
    if use_dspy_all or _env_flag("USE_DSPY_VERIFIER"):
        try:
            from dspy_integration.verifier import DSPyVerifier
        except ImportError as exc:
            raise RuntimeError("USE_DSPY_VERIFIER is set but DSPy is unavailable.") from exc
        verifier = DSPyVerifier()

    writer = OpenAIWriter()
    if use_dspy_all or _env_flag("USE_DSPY_WRITER"):
        try:
            from dspy_integration.writer import DSPyWriter
        except ImportError as exc:
            raise RuntimeError("USE_DSPY_WRITER is set but DSPy is unavailable.") from exc
        writer = DSPyWriter()

    visualizer = OpenAIVisualizer()
    if use_dspy_all or _env_flag("USE_DSPY_VISUALIZER"):
        try:
            from dspy_integration.visualizer import DSPyVisualizer
        except ImportError as exc:
            raise RuntimeError(
                "USE_DSPY_VISUALIZER is set but DSPy is unavailable."
            ) from exc
        visualizer = DSPyVisualizer()

    return DemoAgents(
        clarifier=clarifier,
        planner=planner,
        searcher=searcher,
        extractor=extractor,
        verifier=verifier,
        writer=writer,
        visualizer=visualizer,
        orchestrator=MockOrchestrator(
            planner=planner,
            searcher=searcher,
            extractor=extractor,
            verifier=verifier,
            writer=writer,
        ),
    )
