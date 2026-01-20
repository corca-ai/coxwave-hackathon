from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from env_loader import load_env
from evals.observability import write_json_artifact
from evals.registry import get_spec, list_specs
from evals.runner import run_eval
from main import build_mock_agents


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run agent evals.")
    parser.add_argument(
        "--agent",
        required=True,
        choices=list_specs(),
        help="Agent name to evaluate",
    )
    parser.add_argument(
        "--engine",
        choices=["agents", "dspy"],
        default="agents",
        help="Execution engine for the agent (default: agents)",
    )
    parser.add_argument(
        "--dataset",
        default=None,
        help="Path to JSONL dataset (defaults to agent's dataset)",
    )
    parser.add_argument(
        "--max-samples",
        type=int,
        default=None,
        help="Max samples to evaluate (overrides EVAL_MAX_SAMPLES)",
    )
    parser.add_argument(
        "--mock",
        action="store_true",
        help="Use mock agents instead of real API calls",
    )
    parser.add_argument(
        "--run-tag",
        default=None,
        help="Optional tag for the artifact filename",
    )
    return parser.parse_args()


def resolve_max_samples(cli_value: Optional[int]) -> int:
    env_value = os.getenv("EVAL_MAX_SAMPLES")
    max_samples: int
    if cli_value is not None:
        max_samples = cli_value
    elif env_value:
        try:
            max_samples = int(env_value)
        except ValueError:
            max_samples = 20
    else:
        max_samples = 20

    if max_samples < 1:
        max_samples = 1
    return max_samples


def load_agents(engine: str, use_mock: bool, agent_name: str):
    if engine == "agents":
        if use_mock:
            return build_mock_agents()
        try:
            from agents_impl import build_agents
        except ImportError as exc:
            raise RuntimeError(
                "Failed to import agents_impl. Install dependencies or run with --mock."
            ) from exc
        return build_agents()

    if use_mock:
        raise RuntimeError("--mock is only supported with --engine agents.")

    try:
        from dspy_integration.agents import build_dspy_agents
    except ImportError as exc:
        raise RuntimeError("DSPy agents are unavailable.") from exc

    return build_dspy_agents(agent_name)


def main() -> int:
    load_env(
        keys=[
            "OPENAI_API_KEY",
            "OPENAI_MODEL",
            "OPENAI_TEMPERATURE",
            "EVAL_MAX_SAMPLES",
            "EVAL_ARTIFACT_DIR",
            "DSPY_MODEL",
            "DSPY_TEMPERATURE",
            "DSPY_MAX_TOKENS",
        ]
    )
    args = parse_args()
    spec = get_spec(args.agent)
    dataset_path = Path(args.dataset) if args.dataset else spec.default_dataset

    if not dataset_path.exists():
        print(f"Dataset not found: {dataset_path}")
        return 1

    try:
        agents = load_agents(args.engine, args.mock, args.agent)
    except RuntimeError as exc:
        print(str(exc))
        return 1
    max_samples = resolve_max_samples(args.max_samples)

    summary, results = run_eval(
        spec,
        agents,
        str(dataset_path),
        max_samples=max_samples,
    )

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    tag = args.run_tag or timestamp
    artifact_name = f"eval-{spec.name}-{tag}.json"
    artifact = write_json_artifact(
        artifact_name,
        {"summary": summary, "results": results},
    )
    print(f"Eval results saved to {artifact}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
