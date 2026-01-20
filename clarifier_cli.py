from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import asdict

from agents_impl import OpenAIClarifier
from env_loader import load_env


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the Clarifier agent only.")
    parser.add_argument("--query", required=True, help="Research question to clarify")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    load_env(keys=["OPENAI_API_KEY", "OPENAI_MODEL", "OPENAI_TEMPERATURE"])
    if not os.getenv("OPENAI_API_KEY"):
        print("OPENAI_API_KEY is not set.")
        return 1
    print("Clarifier input:")
    print(json.dumps({"query": args.query}, indent=2, ensure_ascii=True))
    clarifier = OpenAIClarifier()
    output = clarifier.run(args.query)
    print(json.dumps(asdict(output), indent=2, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
