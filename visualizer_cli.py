from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import asdict
from pathlib import Path

from agents_impl import OpenAIVisualizer
from env_loader import load_env


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the Visualizer agent only.")
    parser.add_argument(
        "--input",
        required=True,
        help="Path to ReportOutput JSON (use '-' to read from stdin)",
    )
    return parser.parse_args()


def read_input(path: str) -> str:
    if path == "-":
        return sys.stdin.read()
    file_path = Path(path)
    if not file_path.exists():
        raise FileNotFoundError(path)
    return file_path.read_text()


def main() -> int:
    args = parse_args()
    load_env(keys=["OPENAI_API_KEY", "OPENAI_MODEL", "OPENAI_TEMPERATURE"])
    if not os.getenv("OPENAI_API_KEY"):
        print("OPENAI_API_KEY is not set.")
        return 1

    try:
        raw = read_input(args.input)
    except FileNotFoundError:
        print(f"Input file not found: {args.input}")
        return 1
    except OSError as exc:
        print(f"Failed to read input: {exc}")
        return 1
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        print(f"Input must be JSON: {exc}")
        return 1

    print("Visualizer input:")
    print(json.dumps(payload, indent=2, ensure_ascii=True))

    visualizer = OpenAIVisualizer()
    output = visualizer.run(json.dumps(payload, ensure_ascii=True))
    print("Visualizer output:")
    print(json.dumps(asdict(output), indent=2, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
