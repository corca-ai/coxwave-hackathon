# Orchestrator Agent Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add Orchestrator agent that manages the Plan → Search → Extract → Verify → Write loop with dynamic re-search capability.

**Architecture:** Orchestrator sits between Clarifier and Visualizer, coordinating the research loop. When Verifier returns `is_enough=False` with `next_search_queries`, Orchestrator loops back to Search. Loop continues until quality gate passes or `max_loops` exhausted.

**Tech Stack:** Python dataclasses, Protocol typing, OpenAI Agent SDK (for future OpenAIOrchestrator)

---

## Task 1: Add Orchestrator Protocol and Config

**Files:**
- Modify: `main.py:96-139` (add after Visualizer protocol, before DemoAgents)

**Step 1: Write the failing test**

Create `tests/test_orchestrator.py`:

```python
import unittest
from main import (
    Orchestrator,
    OrchestratorConfig,
    OrchestratorOutput,
    ReportOutput,
)


class OrchestratorProtocolTest(unittest.TestCase):
    def test_orchestrator_config_defaults(self) -> None:
        config = OrchestratorConfig()
        self.assertEqual(config.max_loops, 3)
        self.assertTrue(config.require_plan_approval)

    def test_orchestrator_output_structure(self) -> None:
        report = ReportOutput(
            title="Test",
            executive_summary="Summary",
            key_findings=["Finding 1"],
            limitations=["Limit 1"],
            citations=["cite1"],
            suggested_visuals=[],
        )
        output = OrchestratorOutput(
            report=report,
            loops_used=2,
            plan_approved=True,
        )
        self.assertEqual(output.loops_used, 2)
        self.assertTrue(output.plan_approved)


if __name__ == "__main__":
    unittest.main()
```

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_orchestrator.py -v`
Expected: FAIL with "cannot import name 'Orchestrator'"

**Step 3: Write minimal implementation**

Add to `main.py` after line 93 (after VisualOutput class):

```python
@dataclass
class OrchestratorConfig:
    max_loops: int = 3
    require_plan_approval: bool = True


@dataclass
class OrchestratorOutput:
    report: ReportOutput
    loops_used: int
    plan_approved: bool


class Orchestrator(Protocol):
    def run(self, clarify_context: str, config: OrchestratorConfig) -> OrchestratorOutput:
        raise NotImplementedError
```

**Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_orchestrator.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add main.py tests/test_orchestrator.py
git commit -m "feat: add Orchestrator protocol and config dataclasses"
```

---

## Task 2: Implement MockOrchestrator

**Files:**
- Modify: `main.py` (add MockOrchestrator class after MockVisualizer)

**Step 1: Write the failing test**

Add to `tests/test_orchestrator.py`:

```python
from main import (
    MockOrchestrator,
    MockPlanner,
    MockSearcher,
    MockExtractor,
    MockVerifier,
    MockWriter,
    OrchestratorConfig,
)


class MockOrchestratorTest(unittest.TestCase):
    def test_mock_orchestrator_returns_report(self) -> None:
        orchestrator = MockOrchestrator(
            planner=MockPlanner(),
            searcher=MockSearcher(),
            extractor=MockExtractor(),
            verifier=MockVerifier(),
            writer=MockWriter(),
        )
        config = OrchestratorConfig()
        context = '{"original_query": "test query", "final": {"is_clear_enough": true}}'

        result = orchestrator.run(context, config)

        self.assertIsNotNone(result.report)
        self.assertEqual(result.report.title, "Demo Report")
        self.assertGreaterEqual(result.loops_used, 1)
        self.assertTrue(result.plan_approved)
```

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_orchestrator.py::MockOrchestratorTest -v`
Expected: FAIL with "cannot import name 'MockOrchestrator'"

**Step 3: Write minimal implementation**

Add to `main.py` after MockVisualizer class:

```python
class MockOrchestrator:
    def __init__(
        self,
        planner: Planner,
        searcher: Searcher,
        extractor: Extractor,
        verifier: Verifier,
        writer: Writer,
    ) -> None:
        self.planner = planner
        self.searcher = searcher
        self.extractor = extractor
        self.verifier = verifier
        self.writer = writer

    def run(self, clarify_context: str, config: OrchestratorConfig) -> OrchestratorOutput:
        # Plan
        plan_out = self.planner.run(clarify_context)

        loops_used = 0
        search_context = json.dumps({"plan": asdict(plan_out), "clarifier": json.loads(clarify_context)})
        verify_out: Optional[VerifyOutput] = None

        # Search-Extract-Verify loop
        for loop_idx in range(config.max_loops):
            loops_used = loop_idx + 1

            search_out = self.searcher.run(search_context)
            extract_out = self.extractor.run(json.dumps(asdict(search_out)))
            verify_out = self.verifier.run(json.dumps(asdict(extract_out)))

            if verify_out.is_enough:
                break

            # Prepare next search context with next_search_queries
            if verify_out.next_search_queries:
                search_context = json.dumps({
                    "plan": asdict(plan_out),
                    "previous_search": asdict(search_out),
                    "next_queries": verify_out.next_search_queries,
                })

        # Write
        supported = [v for v in (verify_out.verdicts if verify_out else []) if v.verdict.lower() == "supported"]
        writer_context = json.dumps({
            "clarifier": json.loads(clarify_context),
            "plan": asdict(plan_out),
            "supported_claims": [asdict(v) for v in supported],
        })
        report_out = self.writer.run(writer_context)

        return OrchestratorOutput(
            report=report_out,
            loops_used=loops_used,
            plan_approved=True,  # Mock always approves
        )
```

**Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_orchestrator.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add main.py tests/test_orchestrator.py
git commit -m "feat: implement MockOrchestrator with search-verify loop"
```

---

## Task 3: Test Orchestrator Loop Behavior

**Files:**
- Modify: `tests/test_orchestrator.py`

**Step 1: Write the failing test**

Add to `tests/test_orchestrator.py`:

```python
from main import VerifyOutput, Verification


class MockVerifierNotEnough:
    """Verifier that returns is_enough=False for first N calls."""
    def __init__(self, fail_count: int = 1) -> None:
        self.call_count = 0
        self.fail_count = fail_count

    def run(self, context: str) -> VerifyOutput:
        self.call_count += 1
        if self.call_count <= self.fail_count:
            return VerifyOutput(
                verdicts=[],
                is_enough=False,
                next_search_queries=["additional search query"],
            )
        return VerifyOutput(
            verdicts=[
                Verification(
                    claim="Test claim",
                    verdict="supported",
                    rationale="Test rationale",
                    confidence=0.9,
                )
            ],
            is_enough=True,
            next_search_queries=[],
        )


class OrchestratorLoopTest(unittest.TestCase):
    def test_orchestrator_loops_when_not_enough(self) -> None:
        verifier = MockVerifierNotEnough(fail_count=2)
        orchestrator = MockOrchestrator(
            planner=MockPlanner(),
            searcher=MockSearcher(),
            extractor=MockExtractor(),
            verifier=verifier,
            writer=MockWriter(),
        )
        config = OrchestratorConfig(max_loops=5)
        context = '{"original_query": "test", "final": {"is_clear_enough": true}}'

        result = orchestrator.run(context, config)

        self.assertEqual(verifier.call_count, 3)  # 2 failures + 1 success
        self.assertEqual(result.loops_used, 3)

    def test_orchestrator_stops_at_max_loops(self) -> None:
        verifier = MockVerifierNotEnough(fail_count=10)  # Always fails
        orchestrator = MockOrchestrator(
            planner=MockPlanner(),
            searcher=MockSearcher(),
            extractor=MockExtractor(),
            verifier=verifier,
            writer=MockWriter(),
        )
        config = OrchestratorConfig(max_loops=3)
        context = '{"original_query": "test", "final": {"is_clear_enough": true}}'

        result = orchestrator.run(context, config)

        self.assertEqual(verifier.call_count, 3)  # Stopped at max_loops
        self.assertEqual(result.loops_used, 3)
```

**Step 2: Run test to verify it passes**

Run: `python -m pytest tests/test_orchestrator.py::OrchestratorLoopTest -v`
Expected: PASS (implementation already supports this)

**Step 3: Commit**

```bash
git add tests/test_orchestrator.py
git commit -m "test: add orchestrator loop behavior tests"
```

---

## Task 4: Update DemoAgents and build_mock_agents

**Files:**
- Modify: `main.py` (DemoAgents dataclass and build_mock_agents function)

**Step 1: Write the failing test**

Add to `tests/test_orchestrator.py`:

```python
from main import build_mock_agents, DemoAgents


class DemoAgentsOrchestratorTest(unittest.TestCase):
    def test_demo_agents_has_orchestrator(self) -> None:
        agents = build_mock_agents()
        self.assertTrue(hasattr(agents, "orchestrator"))
        self.assertIsInstance(agents.orchestrator, MockOrchestrator)
```

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_orchestrator.py::DemoAgentsOrchestratorTest -v`
Expected: FAIL with "DemoAgents has no attribute 'orchestrator'"

**Step 3: Write minimal implementation**

Modify `DemoAgents` in `main.py`:

```python
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
```

Modify `build_mock_agents()` in `main.py`:

```python
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
```

**Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_orchestrator.py::DemoAgentsOrchestratorTest -v`
Expected: PASS

**Step 5: Commit**

```bash
git add main.py tests/test_orchestrator.py
git commit -m "feat: add orchestrator to DemoAgents"
```

---

## Task 5: Update agents_impl.py build_agents

**Files:**
- Modify: `agents_impl.py`

**Step 1: Write the failing test**

Add to `tests/test_orchestrator.py`:

```python
import os
import unittest


class AgentsImplOrchestratorTest(unittest.TestCase):
    @unittest.skipUnless(os.getenv("OPENAI_API_KEY"), "OPENAI_API_KEY not set")
    def test_build_agents_has_orchestrator(self) -> None:
        from agents_impl import build_agents
        agents = build_agents()
        self.assertTrue(hasattr(agents, "orchestrator"))
```

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_orchestrator.py::AgentsImplOrchestratorTest -v`
Expected: FAIL (missing orchestrator in build_agents)

**Step 3: Write minimal implementation**

Modify `agents_impl.py` imports:

```python
from main import (
    ClarifyOutput,
    DemoAgents,
    MockExtractor,
    MockOrchestrator,
    MockPlanner,
    MockSearcher,
    MockVerifier,
    MockWriter,
    VisualComponent,
    VisualOutput,
)
```

Modify `build_agents()` in `agents_impl.py`:

```python
def build_agents() -> DemoAgents:
    planner = MockPlanner()
    searcher = MockSearcher()
    extractor = MockExtractor()
    verifier = MockVerifier()
    writer = MockWriter()

    return DemoAgents(
        clarifier=OpenAIClarifier(),
        planner=planner,
        searcher=searcher,
        extractor=extractor,
        verifier=verifier,
        writer=writer,
        visualizer=OpenAIVisualizer(),
        orchestrator=MockOrchestrator(
            planner=planner,
            searcher=searcher,
            extractor=extractor,
            verifier=verifier,
            writer=writer,
        ),
    )
```

**Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_orchestrator.py::AgentsImplOrchestratorTest -v`
Expected: PASS (or SKIP if no API key)

**Step 5: Commit**

```bash
git add agents_impl.py tests/test_orchestrator.py
git commit -m "feat: add orchestrator to agents_impl build_agents"
```

---

## Task 6: Refactor run_demo to use Orchestrator

**Files:**
- Modify: `main.py` (run_demo function)

**Step 1: Write the failing test**

Modify `tests/test_demo_e2e.py` expected sections:

```python
# The test already exists, but we need to verify it still passes
# after refactoring run_demo to use Orchestrator
```

**Step 2: Refactor run_demo**

Replace the middle section of `run_demo()` (after clarifier, before visualizer) with Orchestrator call:

```python
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

    # Use Orchestrator for Plan -> Search -> Extract -> Verify -> Write
    print_section("Orchestrator")
    config = OrchestratorConfig(
        max_loops=max_orchestrator_loops,
        require_plan_approval=True,
    )
    if show_inputs:
        print_json("Orchestrator config", asdict(config))

    orchestrator_out = agents.orchestrator.run(clarified_context, config)
    print_json("Orchestrator result", {
        "loops_used": orchestrator_out.loops_used,
        "plan_approved": orchestrator_out.plan_approved,
    })
    print_json("Report", orchestrator_out.report)

    if visualize:
        print_section("Visualize")
        visual_payload = asdict(orchestrator_out.report)
        if show_inputs:
            print_json("Visualize input", visual_payload)
        visual_input = json.dumps(visual_payload, ensure_ascii=True)
        visual_out = agents.visualizer.run(visual_input)
        print_json("Visualization spec", visual_out)

    print_section("Done")
    print("Demo complete.")
    return 0
```

**Step 3: Run E2E test**

Run: `python -m pytest tests/test_demo_e2e.py -v`
Expected: PASS (may need to update expected sections)

**Step 4: Update E2E test for new sections**

Modify `tests/test_demo_e2e.py`:

```python
for section in [
    "Input",
    "Clarify",
    "Orchestrator",
    "Visualize",
    "Done",
]:
    self.assertIn(section, output, msg=f"Missing section in output: {section}")
```

**Step 5: Run test again**

Run: `python -m pytest tests/test_demo_e2e.py -v`
Expected: PASS

**Step 6: Commit**

```bash
git add main.py tests/test_demo_e2e.py
git commit -m "refactor: use Orchestrator in run_demo"
```

---

## Task 7: Add Orchestrator Observability (Logging)

**Files:**
- Modify: `main.py` (MockOrchestrator)

**Step 1: Add logging to MockOrchestrator**

Update `MockOrchestrator.run()` to print section headers:

```python
def run(self, clarify_context: str, config: OrchestratorConfig) -> OrchestratorOutput:
    # Plan
    print_section("Plan")
    plan_out = self.planner.run(clarify_context)
    print_json("Plan", plan_out)

    loops_used = 0
    search_context = json.dumps({"plan": asdict(plan_out), "clarifier": json.loads(clarify_context)})
    verify_out: Optional[VerifyOutput] = None

    # Search-Extract-Verify loop
    for loop_idx in range(config.max_loops):
        loops_used = loop_idx + 1
        print_section(f"Research Loop {loops_used}/{config.max_loops}")

        print_section("Search")
        search_out = self.searcher.run(search_context)
        print_json("Search results", search_out)

        print_section("Extract")
        extract_out = self.extractor.run(json.dumps(asdict(search_out)))
        print_json("Extracted claims", extract_out)

        print_section("Verify")
        verify_out = self.verifier.run(json.dumps(asdict(extract_out)))
        print_json("Verification", verify_out)

        if verify_out.is_enough:
            print("Quality gate PASSED. Proceeding to Write.")
            break

        print(f"Quality gate FAILED. Next queries: {verify_out.next_search_queries}")
        if verify_out.next_search_queries:
            search_context = json.dumps({
                "plan": asdict(plan_out),
                "previous_search": asdict(search_out),
                "next_queries": verify_out.next_search_queries,
            })

    # Write
    print_section("Write")
    supported = [v for v in (verify_out.verdicts if verify_out else []) if v.verdict.lower() == "supported"]
    writer_context = json.dumps({
        "clarifier": json.loads(clarify_context),
        "plan": asdict(plan_out),
        "supported_claims": [asdict(v) for v in supported],
    })
    report_out = self.writer.run(writer_context)
    print_json("Report", report_out)

    return OrchestratorOutput(
        report=report_out,
        loops_used=loops_used,
        plan_approved=True,
    )
```

**Step 2: Run E2E test**

Run: `python -m pytest tests/test_demo_e2e.py -v`
Expected: PASS

**Step 3: Update E2E test expected sections**

```python
for section in [
    "Input",
    "Clarify",
    "Orchestrator",
    "Plan",
    "Research Loop",
    "Search",
    "Extract",
    "Verify",
    "Write",
    "Visualize",
    "Done",
]:
    self.assertIn(section, output, msg=f"Missing section in output: {section}")
```

**Step 4: Commit**

```bash
git add main.py tests/test_demo_e2e.py
git commit -m "feat: add observability logging to Orchestrator"
```

---

## Task 8: Manual E2E Verification

**Step 1: Run mock demo**

```bash
python main.py --mock --query "How does attention mechanism work in transformers?"
```

Expected output:
- Input section with query
- Clarify section
- Orchestrator section
- Plan section
- Research Loop 1/3
- Search, Extract, Verify sections
- Write section
- Visualize section
- Done

**Step 2: Verify loop behavior**

The mock should complete in 1 loop (MockVerifier returns `is_enough=True`).

**Step 3: Commit final state**

```bash
git add -A
git commit -m "feat: complete Orchestrator implementation with loop support"
```

---

## Summary

| Task | Description | Status |
|------|-------------|--------|
| 1 | Add Orchestrator Protocol and Config | Pending |
| 2 | Implement MockOrchestrator | Pending |
| 3 | Test Orchestrator Loop Behavior | Pending |
| 4 | Update DemoAgents and build_mock_agents | Pending |
| 5 | Update agents_impl.py build_agents | Pending |
| 6 | Refactor run_demo to use Orchestrator | Pending |
| 7 | Add Orchestrator Observability | Pending |
| 8 | Manual E2E Verification | Pending |
