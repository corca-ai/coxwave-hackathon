from __future__ import annotations

from evals.clarifier_eval import build_spec
from evals.specs import EvalSpec


EVAL_SPECS: dict[str, EvalSpec] = {
    "clarifier": build_spec(),
}


def list_specs() -> list[str]:
    return sorted(EVAL_SPECS.keys())


def get_spec(name: str) -> EvalSpec:
    try:
        return EVAL_SPECS[name]
    except KeyError as exc:
        available = ", ".join(list_specs())
        raise KeyError(f"Unknown agent '{name}'. Available: {available}") from exc
