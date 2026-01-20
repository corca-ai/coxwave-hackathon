from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import asdict, dataclass, field, is_dataclass
from typing import List, Optional, Protocol

from env_loader import load_env

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
class VerifyOutput:
    verdicts: List[Verification] = field(default_factory=list)
    is_enough: bool = False
    next_search_queries: List[str] = field(default_factory=list)


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


@dataclass
class DemoAgents:
    clarifier: Clarifier
    planner: Planner
    searcher: Searcher
    extractor: Extractor
    verifier: Verifier
    writer: Writer
    visualizer: Visualizer


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
                VisualComponent(type="heading", props={"text": "Demo Report"}),
                VisualComponent(type="bullets", props={"items": ["Finding 1 from source S1"]}),
            ],
            rationale="Basic structure to render the report quickly.",
        )


def build_mock_agents() -> DemoAgents:
    return DemoAgents(
        clarifier=MockClarifier(),
        planner=MockPlanner(),
        searcher=MockSearcher(),
        extractor=MockExtractor(),
        verifier=MockVerifier(),
        writer=MockWriter(),
        visualizer=MockVisualizer(),
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
    show_inputs: bool = True,
) -> int:
    print_section("Input")
    print(f"Query: {query}")

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

    print_section("Plan")
    if show_inputs:
        print_json("Plan input", clarifier_payload)
    plan_out = agents.planner.run(clarified_context)
    print_json("Plan", plan_out)

    if not ask_yes_no("Approve this plan? [y/N]: "):
        feedback = ask("What should change in the plan? ")
        plan_input = f"{clarified_context}\nUser feedback: {feedback}"
        plan_out = agents.planner.run(plan_input)
        print_json("Revised plan", plan_out)
        if not ask_yes_no("Approve revised plan? [y/N]: "):
            print("Plan not approved. Exiting.")
            return 0

    print_section("Search")
    search_payload = {"plan": asdict(plan_out), "clarifier": clarifier_payload}
    if show_inputs:
        print_json("Search input", search_payload)
    search_input = json.dumps(search_payload, ensure_ascii=True)
    search_out = agents.searcher.run(search_input)
    print_json("Search results", search_out)

    print_section("Extract")
    extract_payload = asdict(search_out)
    if show_inputs:
        print_json("Extract input", extract_payload)
    extract_input = json.dumps(extract_payload, ensure_ascii=True)
    extract_out = agents.extractor.run(extract_input)
    print_json("Extracted claims", extract_out)

    print_section("Verify")
    verify_payload = asdict(extract_out)
    if show_inputs:
        print_json("Verify input", verify_payload)
    verify_input = json.dumps(verify_payload, ensure_ascii=True)
    verify_out = agents.verifier.run(verify_input)
    print_json("Verification", verify_out)

    if not verify_out.is_enough:
        print("Evidence is not enough for a final answer.")
        if verify_out.next_search_queries:
            print("Suggested next searches:")
            for q in verify_out.next_search_queries:
                print(f"- {q}")
        if not ask_yes_no("Continue to write a draft anyway? [y/N]: "):
            print("Stopping after verification.")
            return 0

    supported = [v for v in verify_out.verdicts if v.verdict.lower() == "supported"]
    writer_payload = {
        "clarifier": clarifier_payload,
        "plan": asdict(plan_out),
        "sources": asdict(search_out),
        "supported_claims": [asdict(v) for v in supported],
    }
    if show_inputs:
        print_json("Write input", writer_payload)
    writer_input = json.dumps(writer_payload, ensure_ascii=True)

    print_section("Write")
    report_out = agents.writer.run(writer_input)
    print_json("Report", report_out)

    if visualize:
        print_section("Visualize")
        visual_payload = asdict(report_out)
        if show_inputs:
            print_json("Visualize input", visual_payload)
        visual_input = json.dumps(visual_payload, ensure_ascii=True)
        visual_out = agents.visualizer.run(visual_input)
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
