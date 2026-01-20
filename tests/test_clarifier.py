import json
import os
import unittest
import warnings
from dataclasses import asdict

from agents_impl import build_agents
from env_loader import load_env
from tests.observability import write_json_artifact
from main import ClarifyOutput


class ClarifierAgentTests(unittest.TestCase):
    def setUp(self) -> None:
        warnings.filterwarnings("ignore", category=ResourceWarning)
        load_env(keys=["OPENAI_API_KEY"])
        if not os.getenv("OPENAI_API_KEY"):
            self.skipTest("OPENAI_API_KEY is not set")
        self.agents = build_agents()

    def test_ambiguous_query_prompts_questions(self) -> None:
        query = "AI alignment"
        print(f"Clarifier input: {query}")
        output = self.agents.clarifier.run(query)
        artifact = write_json_artifact(
            "clarifier_ambiguous.json",
            {"input": query, "output": asdict(output)},
        )
        print(f"Clarifier ambiguous output saved to {artifact}")
        print(json.dumps(asdict(output), indent=2, ensure_ascii=True))
        self.assertIsInstance(output, ClarifyOutput)
        self.assertGreaterEqual(len(output.clarifying_questions), 1)
        self.assertFalse(output.is_clear_enough)
        self.assertTrue(output.interpreted_query)

    def test_output_has_assumptions_field(self) -> None:
        query = "Fast LLM evals"
        print(f"Clarifier input: {query}")
        output = self.agents.clarifier.run(query)
        artifact = write_json_artifact(
            "clarifier_assumptions.json",
            {"input": query, "output": asdict(output)},
        )
        print(f"Clarifier assumptions output saved to {artifact}")
        print(json.dumps(asdict(output), indent=2, ensure_ascii=True))
        self.assertIsInstance(output, ClarifyOutput)
        self.assertIsNotNone(output.assumptions)


if __name__ == "__main__":
    unittest.main()
