from __future__ import annotations

import json
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any

from evals.specs import EvalSpec
from main import DemoAgents


def print_section(title: str) -> None:
    bar = "=" * len(title)
    print(f"\n{title}\n{bar}")


def _to_payload(value: Any) -> Any:
    return asdict(value) if is_dataclass(value) else value


def print_json(label: str, data: Any) -> None:
    print(f"{label}:")
    print(json.dumps(_to_payload(data), indent=2, ensure_ascii=True))


def run_eval(
    spec: EvalSpec,
    agents: DemoAgents,
    dataset_path: str,
    max_samples: int,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    samples = spec.load_samples(Path(dataset_path))
    results: list[dict[str, Any]] = []

    print_section(f"Eval: {spec.name}")
    print_json("Dataset", {"path": dataset_path, "total_samples": len(samples)})

    for idx, sample in enumerate(samples):
        if idx >= max_samples:
            break

        sample_id = sample.get("id", f"sample-{idx + 1}")
        print_section(f"Sample {idx + 1}: {sample_id}")
        print_json("Sample payload", sample)

        agent_input = spec.build_input(sample)
        print_json("Agent input", {"input": _to_payload(agent_input)})

        output = spec.run_agent(agents, agent_input)
        output_payload = _to_payload(spec.output_to_json(output))
        print_json("Agent output", output_payload)

        score = spec.score_output(sample, output)
        print_json("Score", score)

        results.append(
            {
                "id": sample_id,
                "input": agent_input,
                "output": output_payload,
                "score": score,
            }
        )

    total = len(results)
    passed = sum(1 for item in results if item["score"].get("passed"))
    avg_score = 0.0
    if total:
        avg_score = sum(item["score"].get("score", 0.0) for item in results) / total

    summary = {
        "agent": spec.name,
        "dataset": dataset_path,
        "total_samples": len(samples),
        "evaluated": total,
        "passed": passed,
        "avg_score": round(avg_score, 4),
    }
    print_section("Summary")
    print_json("Summary", summary)

    return summary, results
