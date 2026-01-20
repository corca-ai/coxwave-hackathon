import json
import os
import unittest
import warnings
from dataclasses import asdict
from pathlib import Path

from agents_impl import OpenAIVisualizer
from env_loader import load_env
from main import ReportOutput, VisualOutput
from tests.observability import write_json_artifact


FIXTURE_PATH = Path("tests/fixtures/visualizer_report.json")


def ensure_fixture() -> dict:
    if FIXTURE_PATH.exists():
        return json.loads(FIXTURE_PATH.read_text())

    FIXTURE_PATH.parent.mkdir(parents=True, exist_ok=True)
    report = ReportOutput(
        title="Demo Report",
        executive_summary="Short executive summary for testing.",
        key_findings=["Finding A", "Finding B"],
        limitations=["Limited sources"],
        citations=["https://example.com/a", "https://example.com/b"],
        suggested_visuals=["Bullets"],
    )
    payload = asdict(report)
    FIXTURE_PATH.write_text(json.dumps(payload, indent=2, ensure_ascii=True))
    return payload


class VisualizerAgentTests(unittest.TestCase):
    def setUp(self) -> None:
        warnings.filterwarnings("ignore", category=ResourceWarning)
        ensure_fixture()
        load_env(keys=["OPENAI_API_KEY"])
        if not os.getenv("OPENAI_API_KEY"):
            self.skipTest("OPENAI_API_KEY is not set")
        self.visualizer = OpenAIVisualizer()

    def test_visualizer_generates_required_components(self) -> None:
        input_payload = json.loads(FIXTURE_PATH.read_text())
        print("Visualizer input:")
        print(json.dumps(input_payload, indent=2, ensure_ascii=True))

        output = self.visualizer.run(json.dumps(input_payload, ensure_ascii=True))
        artifact = write_json_artifact(
            "visualizer_output.json",
            {"input": input_payload, "output": asdict(output)},
        )
        print(f"Visualizer output saved to {artifact}")
        print(json.dumps(asdict(output), indent=2, ensure_ascii=True))

        self.assertIsInstance(output, VisualOutput)
        self.assertGreaterEqual(len(output.components), 1)

        component_types = {component.type for component in output.components}
        for required in ["heading", "paragraph", "bullets", "callout", "list"]:
            self.assertIn(required, component_types)

        for component in output.components:
            if component.type == "heading":
                self.assertIsInstance(component.props.get("text"), str)
            if component.type == "paragraph":
                self.assertIsInstance(component.props.get("text"), str)
            if component.type in {"bullets", "list"}:
                self.assertIsInstance(component.props.get("items"), list)


if __name__ == "__main__":
    unittest.main()
