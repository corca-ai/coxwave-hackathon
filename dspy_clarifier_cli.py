from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict

from dspy_clarifier import DSPyClarifier
from env_loader import load_env


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the DSPy Clarifier only.")
    parser.add_argument("--query", required=True, help="Research question to clarify")
    return parser.parse_args()


def main() -> int:
    load_env(keys=["OPENAI_API_KEY", "DSPY_MODEL", "DSPY_TEMPERATURE", "DSPY_MAX_TOKENS"])
    args = parse_args()
    try:
        clarifier = DSPyClarifier()
    except RuntimeError as exc:
        print(str(exc))
        return 1
    output = clarifier.run(args.query)
    print(json.dumps(asdict(output), indent=2, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
