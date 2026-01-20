import io
import os
import unittest
import warnings
from contextlib import redirect_stdout
from unittest.mock import patch

from main import build_mock_agents, run_demo
from tests.observability import write_artifact


class DemoE2ETest(unittest.TestCase):
    def test_demo_runs_end_to_end_in_mock_mode(self) -> None:
        warnings.filterwarnings("ignore", category=ResourceWarning)
        agents = build_mock_agents()
        query = "Investigate how retrieval-augmented generation affects hallucination in legal QA"

        def fake_input(_prompt: str = "") -> str:
            return "y"

        buffer = io.StringIO()
        with patch("builtins.input", side_effect=fake_input), redirect_stdout(buffer):
            exit_code = run_demo(agents, query, visualize=False)

        output = buffer.getvalue()
        artifact = write_artifact("demo_e2e.log", output)
        print(f"Demo E2E output saved to {artifact}")
        if os.getenv("TEST_OBSERVE") == "1":
            print(output)

        for section in ["Clarify", "Plan", "Search", "Extract", "Verify", "Write", "Done"]:
            self.assertIn(section, output, msg=f"Missing section in output: {section}")

        self.assertEqual(exit_code, 0)


if __name__ == "__main__":
    unittest.main()
