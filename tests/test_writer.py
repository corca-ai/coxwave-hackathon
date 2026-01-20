import json
import os
import unittest
import warnings
from dataclasses import asdict
from pathlib import Path

from agents_impl import OpenAIWriter
from env_loader import load_env
from main import ReportOutput
from tests.observability import write_json_artifact


FIXTURE_PATH = Path("tests/fixtures/writer_input.json")


def ensure_fixture() -> dict:
    if FIXTURE_PATH.exists():
        return json.loads(FIXTURE_PATH.read_text())
    raise FileNotFoundError("writer_input.json fixture is missing")


class WriterAgentTests(unittest.TestCase):
    def setUp(self) -> None:
        warnings.filterwarnings("ignore", category=ResourceWarning)
        ensure_fixture()
        load_env(keys=["OPENAI_API_KEY"])
        if not os.getenv("OPENAI_API_KEY"):
            self.skipTest("OPENAI_API_KEY is not set")
        self.writer = OpenAIWriter()

    def test_writer_generates_report_output(self) -> None:
        input_payload = json.loads(FIXTURE_PATH.read_text())
        print("Writer input:")
        print(json.dumps(input_payload, indent=2, ensure_ascii=True))

        output = self.writer.run(json.dumps(input_payload, ensure_ascii=True))
        artifact = write_json_artifact(
            "writer_output.json",
            {"input": input_payload, "output": asdict(output)},
        )
        print(f"Writer output saved to {artifact}")
        print(json.dumps(asdict(output), indent=2, ensure_ascii=True))

        self.assertIsInstance(output, ReportOutput)
        self.assertIsInstance(output.title, str)
        self.assertIsInstance(output.executive_summary, str)
        self.assertIsInstance(output.key_findings, list)
        self.assertIsInstance(output.limitations, list)
        self.assertIsInstance(output.citations, list)
        self.assertIsInstance(output.suggested_visuals, list)
        self.assertGreaterEqual(len(output.citations), 1)

        sources = input_payload.get("sources", {}).get("sources", [])
        allowed = {s.get("url") for s in sources if s.get("url")}
        allowed.update({s.get("source_id") for s in sources if s.get("source_id")})
        for citation in output.citations:
            self.assertIn(citation, allowed)


if __name__ == "__main__":
    unittest.main()
