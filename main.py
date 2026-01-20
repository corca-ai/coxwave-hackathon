from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import asdict, dataclass, field, is_dataclass
from typing import AsyncGenerator, List, Optional, Protocol

from env_loader import load_env
from stream_events import StreamEvent, StreamEventTypes

@dataclass
class ClarifyOutput:
    is_clear_enough: bool
    clarifying_questions: List[str] = field(default_factory=list)
    interpreted_query: str = ""
    assumptions: List[str] = field(default_factory=list)


@dataclass
class PlanOutput:
    plan_summary: str
    steps: List[str] = field(default_factory=list)
    success_criteria: List[str] = field(default_factory=list)
    data_needs: List[str] = field(default_factory=list)


@dataclass
class Source:
    source_id: str
    title: str
    url: str
    snippet: str
    why_relevant: str


@dataclass
class SearchOutput:
    refined_query: str
    sources: List[Source] = field(default_factory=list)


@dataclass
class Claim:
    claim: str
    evidence: str
    source_id: str
    confidence: float


@dataclass
class ExtractOutput:
    claims: List[Claim] = field(default_factory=list)
    gaps: List[str] = field(default_factory=list)


@dataclass
class Verification:
    claim: str
    verdict: str
    rationale: str
    confidence: float
    source_id: Optional[str] = None
    required_evidence: List[str] = field(default_factory=list)


@dataclass
class NextAction:
    """Action recommended by Verifier for orchestrator routing."""
    action_type: str  # search_expand, search_more_papers, reextract, stop
    priority: int = 1
    why: str = ""
    suggested_queries: List[str] = field(default_factory=list)
    target_concepts: List[str] = field(default_factory=list)


@dataclass
class VerifyOutput:
    verdicts: List[Verification] = field(default_factory=list)
    is_enough: bool = False
    next_search_queries: List[str] = field(default_factory=list)
    next_actions: List[NextAction] = field(default_factory=list)


@dataclass
class ReportOutput:
    title: str
    executive_summary: str
    key_findings: List[str] = field(default_factory=list)
    limitations: List[str] = field(default_factory=list)
    citations: List[str] = field(default_factory=list)
    suggested_visuals: List[str] = field(default_factory=list)


@dataclass
class VisualComponent:
    type: str
    props: dict = field(default_factory=dict)


@dataclass
class VisualOutput:
    components: List[VisualComponent] = field(default_factory=list)
    rationale: str = ""


@dataclass
class OrchestratorConfig:
    max_loops: int = 3
    require_plan_approval: bool = True


@dataclass
class OrchestratorOutput:
    report: ReportOutput
    loops_used: int
    plan_approved: bool


class Clarifier(Protocol):
    def run(self, query: str) -> ClarifyOutput:
        raise NotImplementedError


class Planner(Protocol):
    def run(self, context: str) -> PlanOutput:
        raise NotImplementedError


class Searcher(Protocol):
    def run(self, context: str) -> SearchOutput:
        raise NotImplementedError


class Extractor(Protocol):
    def run(self, context: str) -> ExtractOutput:
        raise NotImplementedError


class Verifier(Protocol):
    def run(self, context: str) -> VerifyOutput:
        raise NotImplementedError


class Writer(Protocol):
    def run(self, context: str) -> ReportOutput:
        raise NotImplementedError


class Visualizer(Protocol):
    def run(self, context: str) -> VisualOutput:
        raise NotImplementedError


class Orchestrator(Protocol):
    def run(self, clarify_context: str, config: OrchestratorConfig) -> OrchestratorOutput:
        raise NotImplementedError


@dataclass
class DemoAgents:
    clarifier: Clarifier
    planner: Planner
    searcher: Searcher
    extractor: Extractor
    verifier: Verifier
    writer: Writer
    visualizer: Visualizer
    orchestrator: Orchestrator


def print_section(title: str) -> None:
    bar = "=" * len(title)
    print(f"\n{title}\n{bar}")


def print_json(label: str, data: object) -> None:
    print(f"{label}:")
    payload = asdict(data) if is_dataclass(data) else data
    print(json.dumps(payload, indent=2, ensure_ascii=True))


def ask(prompt: str) -> str:
    try:
        return input(prompt).strip()
    except EOFError:
        return ""


def ask_yes_no(prompt: str, default_no: bool = True) -> bool:
    raw = ask(prompt)
    if not raw:
        return not default_no
    return raw.lower() in {"y", "yes"}


class MockClarifier:
    def run(self, query: str) -> ClarifyOutput:
        tokens = query.split()
        if len(tokens) < 4:
            return ClarifyOutput(
                is_clear_enough=False,
                clarifying_questions=[
                    "What is the target domain or industry?",
                    "What time range or scope should we focus on?",
                ],
                interpreted_query=query,
                assumptions=[],
            )
        return ClarifyOutput(
            is_clear_enough=True,
            clarifying_questions=[],
            interpreted_query=query,
            assumptions=["Assuming general scope and recent literature"],
        )


class MockPlanner:
    def run(self, context: str) -> PlanOutput:
        return PlanOutput(
            plan_summary="Define scope, gather sources, extract claims, verify, summarize.",
            steps=[
                "Clarify scope and key terms",
                "Collect primary sources",
                "Extract claims and evidence",
                "Verify and synthesize",
            ],
            success_criteria=["At least 3 supported claims", "Clear limitations"],
            data_needs=["Primary sources", "Recent surveys"],
        )


class MockSearcher:
    def run(self, context: str) -> SearchOutput:
        return SearchOutput(
            refined_query="example research query",
            sources=[
                Source(
                    source_id="S1",
                    title="Example Primary Study",
                    url="https://example.com/study",
                    snippet="A study that reports key findings.",
                    why_relevant="Primary evidence for the core claim",
                ),
                Source(
                    source_id="S2",
                    title="Example Survey",
                    url="https://example.com/survey",
                    snippet="A survey of recent work.",
                    why_relevant="Provides context and comparisons",
                ),
            ],
        )


class MockExtractor:
    def run(self, context: str) -> ExtractOutput:
        return ExtractOutput(
            claims=[
                Claim(
                    claim="Example claim about the topic.",
                    evidence="The study reports a measurable improvement.",
                    source_id="S1",
                    confidence=0.62,
                )
            ],
            gaps=["Need more evidence on limitations"],
        )


class MockVerifier:
    def run(self, context: str) -> VerifyOutput:
        return VerifyOutput(
            verdicts=[
                Verification(
                    claim="Example claim about the topic.",
                    verdict="supported",
                    rationale="Evidence directly mentions the improvement.",
                    confidence=0.6,
                    source_id="S1",
                    required_evidence=[],
                )
            ],
            is_enough=True,
            next_search_queries=[],
        )


class MockWriter:
    def run(self, context: str) -> ReportOutput:
        return ReportOutput(
            title="Demo Report",
            executive_summary="This is a demo summary based on placeholder evidence.",
            key_findings=["Finding 1 from source S1"],
            limitations=["Limited sources in mock mode"],
            citations=["https://example.com/study"],
            suggested_visuals=["Bullet list of findings"],
        )


class MockVisualizer:
    def run(self, context: str) -> VisualOutput:
        return VisualOutput(
            components=[
                VisualComponent(type="heading", props={"text": "Demo Report", "level": 1}),
                VisualComponent(
                    type="paragraph",
                    props={"text": "This is a demo summary based on placeholder evidence."},
                ),
                VisualComponent(
                    type="bullets",
                    props={"items": ["Finding 1 from source S1"], "ordered": False},
                ),
                VisualComponent(
                    type="callout",
                    props={
                        "title": "Limitations",
                        "items": ["Limited sources in mock mode"],
                        "tone": "note",
                    },
                ),
                VisualComponent(
                    type="list",
                    props={"title": "Citations", "items": ["https://example.com/study"]},
                ),
            ],
            rationale="Basic structure to render the report quickly.",
        )


def _parse_search_output_from_dict(data: dict) -> SearchOutput:
    """Reconstruct SearchOutput with nested Source objects from dict."""
    sources = [
        Source(**s) if isinstance(s, dict) else s
        for s in data.get("sources", [])
    ]
    return SearchOutput(
        refined_query=data.get("refined_query", ""),
        sources=sources,
    )


def _parse_extract_output_from_dict(data: dict) -> ExtractOutput:
    """Reconstruct ExtractOutput with nested Claim objects from dict."""
    claims = [
        Claim(**c) if isinstance(c, dict) else c
        for c in data.get("claims", [])
    ]
    return ExtractOutput(
        claims=claims,
        gaps=data.get("gaps", []),
    )


def _parse_verify_output_from_dict(data: dict) -> VerifyOutput:
    """Reconstruct VerifyOutput with nested Verification/NextAction objects from dict."""
    verdicts = [
        Verification(**v) if isinstance(v, dict) else v
        for v in data.get("verdicts", [])
    ]
    next_actions = [
        NextAction(**a) if isinstance(a, dict) else a
        for a in data.get("next_actions", [])
    ]
    return VerifyOutput(
        verdicts=verdicts,
        is_enough=data.get("is_enough", False),
        next_search_queries=data.get("next_search_queries", []),
        next_actions=next_actions,
    )


class MockOrchestrator:
    """Orchestrator with action-based routing and state accumulation."""

    def __init__(
        self,
        planner: Planner,
        searcher: Searcher,
        extractor: Extractor,
        verifier: Verifier,
        writer: Writer,
        verbose: bool = True,
    ) -> None:
        self.planner = planner
        self.searcher = searcher
        self.extractor = extractor
        self.verifier = verifier
        self.writer = writer
        self.verbose = verbose

    def _log(self, section: str, label: str, data: object) -> None:
        if self.verbose:
            print_section(section)
            print_json(label, data)

    def _get_primary_action(self, verify_out: VerifyOutput) -> Optional[NextAction]:
        """Get the highest priority action from next_actions."""
        if not verify_out.next_actions:
            return None
        # Sort by priority (lower = higher priority) and return first
        sorted_actions = sorted(verify_out.next_actions, key=lambda a: a.priority)
        return sorted_actions[0] if sorted_actions else None

    def run(self, clarify_context: str, config: OrchestratorConfig) -> OrchestratorOutput:
        # === PLAN PHASE ===
        plan_out = self.planner.run(clarify_context)
        self._log("Plan", "Plan output", plan_out)

        # === STATE ACCUMULATION ===
        accumulated_sources: List[Source] = []
        accumulated_verdicts: List[Verification] = []
        loops_used = 0

        # Initial context
        clarifier_data = json.loads(clarify_context)
        search_context = json.dumps({"plan": asdict(plan_out), "clarifier": clarifier_data})

        # Current state
        search_out: Optional[SearchOutput] = None
        extract_out: Optional[ExtractOutput] = None
        verify_out: Optional[VerifyOutput] = None

        # === RESEARCH LOOP WITH ACTION-BASED ROUTING ===
        next_step = "search"  # Start with search

        for loop_idx in range(config.max_loops):
            loops_used = loop_idx + 1
            if self.verbose:
                print_section(f"Research Loop {loops_used}/{config.max_loops}")

            # === SEARCH (if needed) ===
            if next_step in ("search", "search_expand", "search_more_papers"):
                search_out = self.searcher.run(search_context)
                self._log("Search", "Search results", search_out)

                # Accumulate sources (avoid duplicates by source_id)
                existing_ids = {s.source_id for s in accumulated_sources}
                for source in search_out.sources:
                    if source.source_id not in existing_ids:
                        accumulated_sources.append(source)
                        existing_ids.add(source.source_id)

                if self.verbose:
                    print(f"Accumulated sources: {len(accumulated_sources)}")

            # === EXTRACT ===
            if next_step in ("search", "search_expand", "search_more_papers", "reextract"):
                # Use accumulated sources for extraction
                extract_input = SearchOutput(
                    refined_query=search_out.refined_query if search_out else "",
                    sources=accumulated_sources,
                )
                extract_out = self.extractor.run(json.dumps(asdict(extract_input)))
                self._log("Extract", "Extracted claims", extract_out)

            # === VERIFY ===
            if extract_out:
                verify_out = self.verifier.run(json.dumps(asdict(extract_out)))
                self._log("Verify", "Verification", verify_out)

                # Accumulate supported/weak verdicts (not unsupported)
                for verdict in verify_out.verdicts:
                    if verdict.verdict.lower() in ("supported", "weak"):
                        # Avoid duplicates
                        if not any(v.claim == verdict.claim for v in accumulated_verdicts):
                            accumulated_verdicts.append(verdict)

                if self.verbose:
                    print(f"Accumulated verdicts: {len(accumulated_verdicts)} (supported/weak)")

            # === CHECK QUALITY GATE ===
            if verify_out and verify_out.is_enough:
                if self.verbose:
                    print("Quality gate PASSED.")
                break

            # === ACTION-BASED ROUTING ===
            primary_action = self._get_primary_action(verify_out) if verify_out else None

            if primary_action:
                action_type = primary_action.action_type
                if self.verbose:
                    print(f"Action: {action_type} (priority={primary_action.priority})")
                    print(f"  Why: {primary_action.why}")

                if action_type == "stop":
                    if self.verbose:
                        print("Verifier requested STOP. Exiting loop.")
                    break

                elif action_type == "reextract":
                    # Skip search, just re-extract with existing sources
                    next_step = "reextract"
                    if self.verbose:
                        print("Re-extracting with existing sources...")
                    continue

                elif action_type in ("search_expand", "search_more_papers"):
                    next_step = action_type
                    # Build search context with action-specific guidance
                    search_context = json.dumps({
                        "plan": asdict(plan_out),
                        "clarifier": clarifier_data,
                        "previous_sources": [asdict(s) for s in accumulated_sources[-5:]],  # Last 5 sources
                        "action_type": action_type,
                        "target_concepts": primary_action.target_concepts,
                        "suggested_queries": primary_action.suggested_queries,
                        "next_queries": verify_out.next_search_queries if verify_out else [],
                    })
                    continue

            # Default: use next_search_queries for new search
            if verify_out and verify_out.next_search_queries:
                if self.verbose:
                    print(f"Quality gate FAILED. Next queries: {verify_out.next_search_queries}")
                next_step = "search"
                search_context = json.dumps({
                    "plan": asdict(plan_out),
                    "clarifier": clarifier_data,
                    "previous_sources": [asdict(s) for s in accumulated_sources[-5:]],
                    "next_queries": verify_out.next_search_queries,
                })
            else:
                # No guidance, continue with full search
                next_step = "search"

        # === WRITE PHASE ===
        # Use accumulated verdicts for final report
        supported = [v for v in accumulated_verdicts if v.verdict.lower() == "supported"]
        weak = [v for v in accumulated_verdicts if v.verdict.lower() == "weak"]

        writer_context = json.dumps({
            "clarifier": clarifier_data,
            "plan": asdict(plan_out),
            "supported_claims": [asdict(v) for v in supported],
            "weak_claims": [asdict(v) for v in weak],
            "total_sources": len(accumulated_sources),
            "loops_used": loops_used,
        })
        report_out = self.writer.run(writer_context)
        self._log("Write", "Report", report_out)

        return OrchestratorOutput(
            report=report_out,
            loops_used=loops_used,
            plan_approved=True,
        )

    async def run_stream(
        self, clarify_context: str, config: OrchestratorConfig
    ) -> AsyncGenerator[StreamEvent, None]:
        """Streaming version of run() that yields events for real-time updates."""
        seq = 0

        yield StreamEvent(
            type=StreamEventTypes.AGENT_START,
            payload={"config": asdict(config)},
            agent="orchestrator",
            sequence=seq,
        )
        seq += 1

        try:
            # === PLAN PHASE ===
            plan_out = self.planner.run(clarify_context)
            self._log("Plan", "Plan output", plan_out)

            yield StreamEvent(
                type="plan_complete",
                payload={"plan": asdict(plan_out)},
                agent="orchestrator",
                stage="plan",
                sequence=seq,
            )
            seq += 1

            # === STATE ACCUMULATION ===
            accumulated_sources: List[Source] = []
            accumulated_verdicts: List[Verification] = []
            loops_used = 0

            clarifier_data = json.loads(clarify_context)
            search_context = json.dumps({"plan": asdict(plan_out), "clarifier": clarifier_data})

            search_out: Optional[SearchOutput] = None
            extract_out: Optional[ExtractOutput] = None
            verify_out: Optional[VerifyOutput] = None

            next_step = "search"

            for loop_idx in range(config.max_loops):
                loops_used = loop_idx + 1

                yield StreamEvent(
                    type=StreamEventTypes.LOOP_START,
                    payload={"loop": loops_used, "max_loops": config.max_loops},
                    agent="orchestrator",
                    sequence=seq,
                )
                seq += 1

                # === SEARCH ===
                if next_step in ("search", "search_expand", "search_more_papers"):
                    if hasattr(self.searcher, "run_stream"):
                        async for event in self.searcher.run_stream(search_context):
                            event.sequence = seq
                            yield event
                            seq += 1
                            if event.type == StreamEventTypes.AGENT_COMPLETE:
                                output_data = event.payload.get("output", {})
                                search_out = _parse_search_output_from_dict(output_data)
                    else:
                        search_out = self.searcher.run(search_context)
                        yield StreamEvent(
                            type=StreamEventTypes.AGENT_COMPLETE,
                            payload={"output": asdict(search_out)},
                            agent="searcher",
                            stage="search",
                            sequence=seq,
                        )
                        seq += 1

                    if search_out:
                        existing_ids = {s.source_id for s in accumulated_sources}
                        for source in search_out.sources:
                            if source.source_id not in existing_ids:
                                accumulated_sources.append(source)
                                existing_ids.add(source.source_id)

                # === EXTRACT ===
                if next_step in ("search", "search_expand", "search_more_papers", "reextract"):
                    extract_input = SearchOutput(
                        refined_query=search_out.refined_query if search_out else "",
                        sources=accumulated_sources,
                    )
                    extract_context = json.dumps(asdict(extract_input))

                    if hasattr(self.extractor, "run_stream"):
                        async for event in self.extractor.run_stream(extract_context):
                            event.sequence = seq
                            yield event
                            seq += 1
                            if event.type == StreamEventTypes.AGENT_COMPLETE:
                                output_data = event.payload.get("output", {})
                                extract_out = _parse_extract_output_from_dict(output_data)
                    else:
                        extract_out = self.extractor.run(extract_context)
                        yield StreamEvent(
                            type=StreamEventTypes.AGENT_COMPLETE,
                            payload={"output": asdict(extract_out)},
                            agent="extractor",
                            stage="extract",
                            sequence=seq,
                        )
                        seq += 1

                # === VERIFY ===
                if extract_out:
                    verify_context = json.dumps(asdict(extract_out))

                    if hasattr(self.verifier, "run_stream"):
                        async for event in self.verifier.run_stream(verify_context):
                            event.sequence = seq
                            yield event
                            seq += 1
                            if event.type == StreamEventTypes.AGENT_COMPLETE:
                                output_data = event.payload.get("output", {})
                                verify_out = _parse_verify_output_from_dict(output_data)
                    else:
                        verify_out = self.verifier.run(verify_context)
                        yield StreamEvent(
                            type=StreamEventTypes.AGENT_COMPLETE,
                            payload={"output": asdict(verify_out)},
                            agent="verifier",
                            stage="verify",
                            sequence=seq,
                        )
                        seq += 1

                    for verdict in verify_out.verdicts:
                        if verdict.verdict.lower() in ("supported", "weak"):
                            if not any(v.claim == verdict.claim for v in accumulated_verdicts):
                                accumulated_verdicts.append(verdict)

                yield StreamEvent(
                    type=StreamEventTypes.LOOP_COMPLETE,
                    payload={
                        "loop": loops_used,
                        "accumulated_sources": len(accumulated_sources),
                        "accumulated_verdicts": len(accumulated_verdicts),
                    },
                    agent="orchestrator",
                    sequence=seq,
                )
                seq += 1

                # === CHECK QUALITY GATE ===
                if verify_out and verify_out.is_enough:
                    break

                # === ACTION-BASED ROUTING ===
                primary_action = self._get_primary_action(verify_out) if verify_out else None

                if primary_action:
                    action_type = primary_action.action_type

                    if action_type == "stop":
                        break
                    elif action_type == "reextract":
                        next_step = "reextract"
                        continue
                    elif action_type in ("search_expand", "search_more_papers"):
                        next_step = action_type
                        search_context = json.dumps({
                            "plan": asdict(plan_out),
                            "clarifier": clarifier_data,
                            "previous_sources": [asdict(s) for s in accumulated_sources[-5:]],
                            "action_type": action_type,
                            "target_concepts": primary_action.target_concepts,
                            "suggested_queries": primary_action.suggested_queries,
                            "next_queries": verify_out.next_search_queries if verify_out else [],
                        })
                        continue

                if verify_out and verify_out.next_search_queries:
                    next_step = "search"
                    search_context = json.dumps({
                        "plan": asdict(plan_out),
                        "clarifier": clarifier_data,
                        "previous_sources": [asdict(s) for s in accumulated_sources[-5:]],
                        "next_queries": verify_out.next_search_queries,
                    })
                else:
                    next_step = "search"

            # === WRITE PHASE ===
            supported = [v for v in accumulated_verdicts if v.verdict.lower() == "supported"]
            weak = [v for v in accumulated_verdicts if v.verdict.lower() == "weak"]

            writer_context = json.dumps({
                "clarifier": clarifier_data,
                "plan": asdict(plan_out),
                "supported_claims": [asdict(v) for v in supported],
                "weak_claims": [asdict(v) for v in weak],
                "total_sources": len(accumulated_sources),
                "loops_used": loops_used,
            })
            report_out = self.writer.run(writer_context)

            yield StreamEvent(
                type="write_complete",
                payload={"report": asdict(report_out)},
                agent="orchestrator",
                stage="write",
                sequence=seq,
            )
            seq += 1

            final_output = OrchestratorOutput(
                report=report_out,
                loops_used=loops_used,
                plan_approved=True,
            )

            yield StreamEvent(
                type=StreamEventTypes.AGENT_COMPLETE,
                payload={"output": asdict(final_output)},
                agent="orchestrator",
                sequence=seq,
            )
        except Exception as e:
            yield StreamEvent(
                type=StreamEventTypes.ERROR,
                payload={"error": str(e), "error_type": type(e).__name__},
                agent="orchestrator",
                sequence=seq,
            )
            raise


def build_mock_agents() -> DemoAgents:
    planner = MockPlanner()
    searcher = MockSearcher()
    extractor = MockExtractor()
    verifier = MockVerifier()
    writer = MockWriter()

    return DemoAgents(
        clarifier=MockClarifier(),
        planner=planner,
        searcher=searcher,
        extractor=extractor,
        verifier=verifier,
        writer=writer,
        visualizer=MockVisualizer(),
        orchestrator=MockOrchestrator(
            planner=planner,
            searcher=searcher,
            extractor=extractor,
            verifier=verifier,
            writer=writer,
        ),
    )


def load_agents(use_mock: bool) -> DemoAgents:
    if use_mock:
        return build_mock_agents()
    try:
        from agents_impl import build_agents  # type: ignore
    except ImportError as exc:
        raise SystemExit(
            "Missing agents_impl.py. Provide build_agents() or run with --mock."
        ) from exc
    agents = build_agents()
    return agents


def _run_clarifier_loop(agents: DemoAgents, query: str, max_rounds: int) -> tuple[ClarifyOutput, list[dict]]:
    rounds: list[dict] = []
    current_query = query
    last_output: Optional[ClarifyOutput] = None
    all_answers: list[dict] = []

    for idx in range(max_rounds):
        title = "Clarify" if idx == 0 else f"Clarify (Round {idx + 1})"
        print_section(title)
        try:
            clarify_out = agents.clarifier.run(current_query)
        except Exception as exc:
            print(f"Clarifier failed: {exc}")
            raise
        print_json("Clarifier output", clarify_out)
        last_output = clarify_out

        if clarify_out.is_clear_enough or not clarify_out.clarifying_questions:
            rounds.append(
                {
                    "input": current_query,
                    "output": asdict(clarify_out),
                    "answers": [],
                    "skipped": False,
                }
            )
            break

        skip = ask("Type 'fast' to skip clarifications, or press Enter to answer: ").lower()
        if skip in {"fast", "skip"}:
            rounds.append(
                {
                    "input": current_query,
                    "output": asdict(clarify_out),
                    "answers": [],
                    "skipped": True,
                }
            )
            break

        answers = []
        for question in clarify_out.clarifying_questions:
            answer = ask(f"{question}\n> ")
            answers.append({"question": question, "answer": answer})
        all_answers.extend(answers)
        rounds.append(
            {
                "input": current_query,
                "output": asdict(clarify_out),
                "answers": answers,
                "skipped": False,
            }
        )

        followup_lines = [f"Original query: {query}", "Clarifications:"]
        for entry in all_answers:
            followup_lines.append(f"Q: {entry['question']}")
            followup_lines.append(f"A: {entry['answer']}")
        current_query = "\n".join(followup_lines)

    if last_output is None:
        raise RuntimeError("Clarifier did not produce output.")
    return last_output, rounds


def run_demo(
    agents: DemoAgents,
    query: str,
    visualize: bool,
    max_clarify_rounds: int = 2,
    max_orchestrator_loops: int = 3,
    show_inputs: bool = True,
) -> int:
    print_section("Input")
    print(f"Query: {query}")

    # Phase 1: Clarifier (separate from orchestrator)
    try:
        clarify_out, clarifier_rounds = _run_clarifier_loop(
            agents, query, max_rounds=max_clarify_rounds
        )
    except Exception:
        return 1

    clarifier_payload = {
        "original_query": query,
        "rounds": clarifier_rounds,
        "final": asdict(clarify_out),
    }
    print_json("Clarifier context", clarifier_payload)
    clarified_context = json.dumps(clarifier_payload, ensure_ascii=True)

    # Phase 2: Orchestrator (Plan → Search → Extract → Verify → Write loop)
    print_section("Orchestrator")
    config = OrchestratorConfig(
        max_loops=max_orchestrator_loops,
        require_plan_approval=True,
    )
    if show_inputs:
        print_json("Orchestrator config", asdict(config))

    try:
        orchestrator_out = agents.orchestrator.run(clarified_context, config)
    except Exception as exc:
        print(f"Orchestrator failed: {exc}")
        return 1
    print_json("Orchestrator summary", {
        "loops_used": orchestrator_out.loops_used,
        "plan_approved": orchestrator_out.plan_approved,
    })

    # Phase 3: Visualizer (separate from orchestrator)
    if visualize:
        print_section("Visualize")
        visual_payload = asdict(orchestrator_out.report)
        if show_inputs:
            print_json("Visualize input", visual_payload)
        visual_input = json.dumps(visual_payload, ensure_ascii=True)
        try:
            visual_out = agents.visualizer.run(visual_input)
        except Exception as exc:
            print(f"Visualizer failed: {exc}")
            return 1
        print_json("Visualization spec", visual_out)

    print_section("Done")
    print("Demo complete.")
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the multi-agent demo scenario.")
    parser.add_argument("--query", help="Research question to run", default=None)
    parser.add_argument("--mock", action="store_true", help="Run with mock agent outputs")
    parser.add_argument("--no-visualize", action="store_true", help="Skip visualizer step")
    parser.add_argument(
        "--show-inputs",
        action="store_true",
        help="Print input payloads for each agent step (always on by default)",
    )
    parser.add_argument(
        "--clarify-rounds",
        type=int,
        default=None,
        help="Max clarifier rounds (overrides DEMO_MAX_CLARIFY_ROUNDS). Example: --clarify-rounds 3",
    )
    return parser.parse_args()


def main() -> int:
    load_env(keys=["DEMO_MAX_CLARIFY_ROUNDS"])
    args = parse_args()
    query = args.query or ask("Research question: ")
    if not query:
        print("No query provided.")
        return 1
    agents = load_agents(args.mock)
    env_rounds = os.getenv("DEMO_MAX_CLARIFY_ROUNDS")
    if args.clarify_rounds is not None:
        max_rounds = args.clarify_rounds
    elif env_rounds:
        try:
            max_rounds = int(env_rounds)
        except ValueError:
            max_rounds = 2
    else:
        max_rounds = 2

    if max_rounds < 1:
        max_rounds = 1

    return run_demo(
        agents,
        query,
        visualize=not args.no_visualize,
        max_clarify_rounds=max_rounds,
        show_inputs=True,
    )


if __name__ == "__main__":
    sys.exit(main())
