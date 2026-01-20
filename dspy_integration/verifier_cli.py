from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path

from .verifier import DSPyVerifier
from env_loader import load_env


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the DSPy Verifier only.")
    parser.add_argument(
        "--input",
        required=True,
        help="Path to ExtractOutput JSON (use '-' to read from stdin)",
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
    load_env(keys=["OPENAI_API_KEY", "DSPY_MODEL", "DSPY_TEMPERATURE", "DSPY_MAX_TOKENS"])
    args = parse_args()
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

    print("Verifier input:")
    print(json.dumps(payload, indent=2, ensure_ascii=True))

    try:
        verifier = DSPyVerifier()
    except RuntimeError as exc:
        print(str(exc))
        return 1
    output = verifier.run(json.dumps(payload, ensure_ascii=True))
    print("Verifier output:")
    print(json.dumps(asdict(output), indent=2, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
