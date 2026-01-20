from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict

from dspy_visualizer import DSPyVisualizer
from env_loader import load_env


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the DSPy Visualizer only.")
    parser.add_argument(
        "--report-json",
        required=True,
        help="Report JSON to visualize",
    )
    return parser.parse_args()


def main() -> int:
    load_env(keys=["OPENAI_API_KEY", "DSPY_MODEL", "DSPY_TEMPERATURE", "DSPY_MAX_TOKENS"])
    args = parse_args()
    try:
        visualizer = DSPyVisualizer()
    except RuntimeError as exc:
        print(str(exc))
        return 1
    output = visualizer.run(args.report_json)
    print(json.dumps(asdict(output), indent=2, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
