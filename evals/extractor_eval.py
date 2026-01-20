from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

from evals.io import load_jsonl
from evals.specs import EvalSpec
from main import DemoAgents, ExtractOutput


def load_samples(path: Path) -> list[dict[str, Any]]:
    return load_jsonl(path)


def build_input(sample: dict[str, Any]) -> str:
    search = sample.get("search")
    if not isinstance(search, dict):
        raise ValueError("Sample is missing a search object")
    return json.dumps(search, ensure_ascii=True)


def run_agent(agents: DemoAgents, agent_input: str) -> ExtractOutput:
    return agents.extractor.run(agent_input)


def output_to_json(output: ExtractOutput) -> dict[str, Any]:
    return asdict(output)


def score_output(sample: dict[str, Any], output: ExtractOutput) -> dict[str, Any]:
    expected = sample.get("expect", {})
    min_claims = int(expected.get("min_claims", 1))
    min_confidence = float(expected.get("min_confidence", 0.0))
    sources = sample.get("search", {}).get("sources", [])
    source_ids = {str(item.get("source_id")) for item in sources if isinstance(item, dict)}

    checks: dict[str, bool] = {}
    notes: list[str] = []

    checks["min_claims"] = len(output.claims) >= min_claims
    if not checks["min_claims"]:
        notes.append(f"Expected >= {min_claims} claims")

    field_ok = True
    confidence_ok = True
    source_ok = True
    for claim in output.claims:
        if not (claim.claim and claim.evidence and claim.source_id):
            field_ok = False
        if claim.confidence < min_confidence or claim.confidence > 1.0:
            confidence_ok = False
        if source_ids and claim.source_id not in source_ids:
            source_ok = False

    checks["claim_fields"] = field_ok
    if not field_ok:
        notes.append("Some claims missing required fields")

    checks["confidence_range"] = confidence_ok
    if not confidence_ok:
        notes.append("Some claims confidence out of range")

    checks["source_id_match"] = source_ok
    if not source_ok:
        notes.append("Claim source_id not in sources")

    score_total = sum(1 for value in checks.values() if value)
    score = score_total / len(checks) if checks else 0.0

    return {
        "passed": all(checks.values()),
        "score": round(score, 4),
        "checks": checks,
        "notes": notes,
        "expected": expected,
    }


def build_spec() -> EvalSpec:
    return EvalSpec(
        name="extractor",
        default_dataset=Path("evals/datasets/extractor.jsonl"),
        load_samples=load_samples,
        build_input=build_input,
        run_agent=run_agent,
        score_output=score_output,
        output_to_json=output_to_json,
    )
