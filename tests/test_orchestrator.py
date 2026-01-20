"""
Orchestrator Success Criteria Tests

These tests define the expected behavior of the Orchestrator agent.
Run with: pytest tests/test_orchestrator.py -v
"""
import json
import unittest
from dataclasses import asdict


class OrchestratorProtocolTest(unittest.TestCase):
    """Success Criteria 1: Protocol and Config exist with correct defaults."""

    def test_orchestrator_config_defaults(self) -> None:
        from main import OrchestratorConfig

        config = OrchestratorConfig()
        self.assertEqual(config.max_loops, 3)
        self.assertTrue(config.require_plan_approval)

    def test_orchestrator_output_structure(self) -> None:
        from main import OrchestratorOutput, ReportOutput

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


class MockOrchestratorTest(unittest.TestCase):
    """Success Criteria 2: MockOrchestrator returns valid report."""

    def test_mock_orchestrator_returns_report(self) -> None:
        from main import (
            MockOrchestrator,
            MockPlanner,
            MockSearcher,
            MockExtractor,
            MockVerifier,
            MockWriter,
            OrchestratorConfig,
        )

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


class OrchestratorLoopTest(unittest.TestCase):
    """Success Criteria 3: Orchestrator loops correctly on verify failure."""

    def test_orchestrator_loops_when_not_enough(self) -> None:
        from main import (
            MockOrchestrator,
            MockPlanner,
            MockSearcher,
            MockExtractor,
            MockWriter,
            OrchestratorConfig,
            VerifyOutput,
            Verification,
        )

        class MockVerifierNotEnough:
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
        from main import (
            MockOrchestrator,
            MockPlanner,
            MockSearcher,
            MockExtractor,
            MockWriter,
            OrchestratorConfig,
            VerifyOutput,
        )

        class MockVerifierAlwaysFails:
            def __init__(self) -> None:
                self.call_count = 0

            def run(self, context: str) -> VerifyOutput:
                self.call_count += 1
                return VerifyOutput(
                    verdicts=[],
                    is_enough=False,
                    next_search_queries=["query"],
                )

        verifier = MockVerifierAlwaysFails()
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

        self.assertEqual(verifier.call_count, 3)
        self.assertEqual(result.loops_used, 3)


class DemoAgentsOrchestratorTest(unittest.TestCase):
    """Success Criteria 4: DemoAgents includes orchestrator."""

    def test_demo_agents_has_orchestrator(self) -> None:
        from main import build_mock_agents, MockOrchestrator

        agents = build_mock_agents()
        self.assertTrue(hasattr(agents, "orchestrator"))


class E2EIntegrationTest(unittest.TestCase):
    """Success Criteria 5: E2E demo runs with Orchestrator."""

    def test_demo_runs_with_orchestrator(self) -> None:
        import io
        from contextlib import redirect_stdout
        from unittest.mock import patch
        from main import build_mock_agents, run_demo

        agents = build_mock_agents()
        query = "How does attention mechanism work in transformers?"

        def fake_input(_prompt: str = "") -> str:
            return "y"

        buffer = io.StringIO()
        with patch("builtins.input", side_effect=fake_input), redirect_stdout(buffer):
            exit_code = run_demo(agents, query, visualize=True)

        output = buffer.getvalue()

        # Must have these sections (new orchestrator-based flow)
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
            self.assertIn(section, output, msg=f"Missing section: {section}")

        # Verify orchestrator summary is printed
        self.assertIn("loops_used", output)
        self.assertIn("Quality gate PASSED", output)

        self.assertEqual(exit_code, 0)


if __name__ == "__main__":
    unittest.main()
