from __future__ import annotations

import argparse
import inspect
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Optional

from .agents import DSPyAgents
from .clarifier import DSPyClarifier, prediction_to_output as clarify_pred_to_output
from .utils import configure_dspy, require_dspy, resolve_dspy_settings
from .visualizer import DSPyVisualizer, prediction_to_output as viz_pred_to_output
from env_loader import load_env
from evals.clarifier_eval import score_output as clarifier_score
from evals.io import load_jsonl
from evals.observability import write_json_artifact
from evals.registry import get_spec
from evals.runner import run_eval
from evals.visualizer_eval import score_output as visualizer_score


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run DSPy optimization loop.")
    parser.add_argument(
        "--agent",
        required=True,
        choices=["clarifier", "visualizer"],
        help="DSPy agent to optimize",
    )
    parser.add_argument(
        "--dataset",
        default=None,
        help="Path to JSONL dataset (defaults to agent's dataset)",
    )
    parser.add_argument(
        "--train-samples",
        type=int,
        default=None,
        help="Number of samples for DSPy training (overrides DSPY_TRAIN_SAMPLES)",
    )
    parser.add_argument(
        "--eval-samples",
        type=int,
        default=None,
        help="Number of samples for eval (overrides DSPY_EVAL_SAMPLES)",
    )
    parser.add_argument(
        "--max-rounds",
        type=int,
        default=None,
        help="Optimizer max rounds (overrides DSPY_OPT_MAX_ROUNDS)",
    )
    parser.add_argument(
        "--max-labeled-demos",
        type=int,
        default=None,
        help="Optimizer max labeled demos (overrides DSPY_OPT_MAX_LABELED_DEMOS)",
    )
    parser.add_argument(
        "--max-bootstrapped-demos",
        type=int,
        default=None,
        help="Optimizer max bootstrapped demos (overrides DSPY_OPT_MAX_BOOTSTRAPPED_DEMOS)",
    )
    parser.add_argument(
        "--run-tag",
        default=None,
        help="Optional tag for the artifact filename",
    )
    return parser.parse_args()


def _env_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if not value:
        return default
    try:
        return int(value)
    except ValueError:
        return default


def _resolve_bound(cli_value: Optional[int], env_name: str, default: int) -> int:
    if cli_value is not None:
        return max(1, cli_value)
    return max(1, _env_int(env_name, default))


def _build_optimizer(
    metric: Callable[[Any, Any], float],
    max_rounds: int,
    max_labeled_demos: int,
    max_bootstrapped_demos: int,
):
    dspy = require_dspy()
    optimizer_cls = getattr(dspy, "MIPROv2", None) or getattr(dspy, "MIPRO", None)
    if optimizer_cls is None:
        raise RuntimeError("DSPy optimizer (MIPROv2) is not available. Upgrade dspy.")

    kwargs = {"metric": metric}
    sig = inspect.signature(optimizer_cls)
    for name, value in [
        ("max_rounds", max_rounds),
        ("max_labeled_demos", max_labeled_demos),
        ("max_bootstrapped_demos", max_bootstrapped_demos),
    ]:
        if name in sig.parameters:
            kwargs[name] = value

    return optimizer_cls(**kwargs)


def _compile_module(optimizer: Any, module: Any, trainset: list[Any], valset: list[Any]) -> Any:
    compile_sig = inspect.signature(optimizer.compile)
    kwargs: dict[str, Any] = {}
    if "trainset" in compile_sig.parameters:
        kwargs["trainset"] = trainset
    if "valset" in compile_sig.parameters and valset:
        kwargs["valset"] = valset
    return optimizer.compile(module, **kwargs)


def _split_examples(examples: list[Any], train_count: int, eval_count: int) -> tuple[list[Any], list[Any]]:
    train = examples[:train_count]
    remaining = examples[train_count:]
    if eval_count <= 0:
        return train, remaining
    return train, remaining[:eval_count]


def _clarifier_examples(samples: list[dict[str, Any]]) -> list[Any]:
    dspy = require_dspy()
    examples: list[Any] = []
    for sample in samples:
        query = sample.get("query")
        if not isinstance(query, str):
            continue
        expect = sample.get("expect", {})
        example = dspy.Example(query=query, expect=expect).with_inputs("query")
        examples.append(example)
    return examples


def _clarifier_samples(samples: list[dict[str, Any]]) -> list[dict[str, Any]]:
    valid: list[dict[str, Any]] = []
    for sample in samples:
        query = sample.get("query")
        if isinstance(query, str):
            valid.append(sample)
    return valid


def _visualizer_examples(samples: list[dict[str, Any]]) -> list[Any]:
    dspy = require_dspy()
    examples: list[Any] = []
    for sample in samples:
        report = sample.get("report")
        if not isinstance(report, dict):
            continue
        expect = sample.get("expect", {})
        report_json = json.dumps(report, ensure_ascii=True)
        example = dspy.Example(report_json=report_json, expect=expect).with_inputs("report_json")
        examples.append(example)
    return examples


def _visualizer_samples(samples: list[dict[str, Any]]) -> list[dict[str, Any]]:
    valid: list[dict[str, Any]] = []
    for sample in samples:
        report = sample.get("report")
        if isinstance(report, dict):
            valid.append(sample)
    return valid


def _clarifier_metric(example: Any, prediction: Any) -> float:
    output = clarify_pred_to_output(prediction, example.query)
    sample = {"query": example.query, "expect": getattr(example, "expect", {})}
    score = clarifier_score(sample, output)
    return float(score.get("score", 0.0))


def _visualizer_metric(example: Any, prediction: Any) -> float:
    report = json.loads(example.report_json)
    output = viz_pred_to_output(prediction, report)
    sample = {"report": report, "expect": getattr(example, "expect", {})}
    score = visualizer_score(sample, output)
    return float(score.get("score", 0.0))


def _build_agents(agent: str, module: Any) -> DSPyAgents:
    if agent == "clarifier":
        return DSPyAgents(clarifier=DSPyClarifier(module=module, configure=False))
    if agent == "visualizer":
        return DSPyAgents(visualizer=DSPyVisualizer(module=module, configure=False))
    raise ValueError(f"Unsupported DSPy agent: {agent}")


def main() -> int:
    load_env(
        keys=[
            "OPENAI_API_KEY",
            "OPENAI_MODEL",
            "OPENAI_TEMPERATURE",
            "DSPY_MODEL",
            "DSPY_TEMPERATURE",
            "DSPY_MAX_TOKENS",
            "DSPY_TRAIN_SAMPLES",
            "DSPY_EVAL_SAMPLES",
            "DSPY_OPT_MAX_ROUNDS",
            "DSPY_OPT_MAX_LABELED_DEMOS",
            "DSPY_OPT_MAX_BOOTSTRAPPED_DEMOS",
            "EVAL_ARTIFACT_DIR",
        ]
    )
    args = parse_args()

    try:
        settings = resolve_dspy_settings()
        configure_dspy(settings)
    except RuntimeError as exc:
        print(str(exc))
        return 1

    spec = get_spec(args.agent)
    dataset_path = args.dataset or str(spec.default_dataset)

    if not os.path.exists(dataset_path):
        print(f"Dataset not found: {dataset_path}")
        return 1

    samples = load_jsonl(Path(dataset_path))
    if args.agent == "clarifier":
        from .clarifier import ClarifierModule

        valid_samples = _clarifier_samples(samples)
        examples = _clarifier_examples(valid_samples)
        metric = _clarifier_metric
        module = ClarifierModule()
    else:
        from .visualizer import VisualizerModule

        valid_samples = _visualizer_samples(samples)
        examples = _visualizer_examples(valid_samples)
        metric = _visualizer_metric
        module = VisualizerModule()

    if not examples:
        print("No valid examples found in dataset.")
        return 1

    train_count = _resolve_bound(args.train_samples, "DSPY_TRAIN_SAMPLES", 4)
    eval_count = _resolve_bound(args.eval_samples, "DSPY_EVAL_SAMPLES", 6)
    total_samples = len(valid_samples)
    if train_count > total_samples:
        train_count = total_samples
    remaining = max(0, total_samples - train_count)
    if eval_count > remaining:
        eval_count = remaining

    trainset, evalset = _split_examples(examples, train_count, eval_count)
    train_samples = valid_samples[:train_count]
    eval_samples = valid_samples[train_count : train_count + eval_count]

    max_rounds = _resolve_bound(args.max_rounds, "DSPY_OPT_MAX_ROUNDS", 3)
    max_labeled = _resolve_bound(args.max_labeled_demos, "DSPY_OPT_MAX_LABELED_DEMOS", 4)
    max_bootstrapped = _resolve_bound(
        args.max_bootstrapped_demos, "DSPY_OPT_MAX_BOOTSTRAPPED_DEMOS", 4
    )

    optimizer = _build_optimizer(metric, max_rounds, max_labeled, max_bootstrapped)
    optimized_module = _compile_module(optimizer, module, trainset, evalset)

    baseline_agents = _build_agents(args.agent, module)
    optimized_agents = _build_agents(args.agent, optimized_module)

    baseline_summary, baseline_results = run_eval(
        spec,
        baseline_agents,
        dataset_path,
        max_samples=len(eval_samples),
        samples=eval_samples,
    )
    optimized_summary, optimized_results = run_eval(
        spec,
        optimized_agents,
        dataset_path,
        max_samples=len(eval_samples),
        samples=eval_samples,
    )

    delta = round(
        float(optimized_summary.get("avg_score", 0.0))
        - float(baseline_summary.get("avg_score", 0.0)),
        4,
    )

    report = {
        "agent": args.agent,
        "dataset": dataset_path,
        "train_samples": len(train_samples),
        "eval_samples": len(eval_samples),
        "baseline": baseline_summary,
        "optimized": optimized_summary,
        "delta": delta,
    }

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    tag = args.run_tag or timestamp
    artifact_name = f"dspy-optimize-{args.agent}-{tag}.json"
    artifact = write_json_artifact(
        artifact_name,
        {
            "summary": report,
            "baseline_results": baseline_results,
            "optimized_results": optimized_results,
        },
    )
    print(f"Optimization report saved to {artifact}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
