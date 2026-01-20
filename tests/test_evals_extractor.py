import io
import json
import unittest
import warnings
from contextlib import redirect_stdout
from pathlib import Path

from evals.registry import get_spec
from evals.runner import run_eval
from main import build_mock_agents
from tests.observability import write_artifact


class EvalsExtractorTests(unittest.TestCase):
    def test_extractor_eval_runs_with_mock_agents(self) -> None:
        warnings.filterwarnings("ignore", category=ResourceWarning)
        spec = get_spec("extractor")
        dataset_path = Path("evals/datasets/extractor.jsonl")
        agents = build_mock_agents()

        buffer = io.StringIO()
        with redirect_stdout(buffer):
            summary, results = run_eval(spec, agents, str(dataset_path), max_samples=2)

        output = buffer.getvalue()
        artifact = write_artifact("evals_extractor_mock.log", output)
        print(f"Evals extractor output saved to {artifact}")
        print(output)

        self.assertEqual(summary["agent"], "extractor")
        self.assertEqual(summary["evaluated"], 2)
        self.assertEqual(len(results), 2)

        first = results[0]
        self.assertIn("score", first)
        self.assertTrue(first["score"].get("passed"))
        self.assertIn("output", first)

        json.dumps(first)


if __name__ == "__main__":
    unittest.main()
