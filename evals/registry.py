from __future__ import annotations

from evals.clarifier_eval import build_spec as build_clarifier_spec
from evals.extractor_eval import build_spec as build_extractor_spec
from evals.planner_eval import build_spec as build_planner_spec
from evals.searcher_eval import build_spec as build_searcher_spec
from evals.verifier_eval import build_spec as build_verifier_spec
from evals.visualizer_eval import build_spec as build_visualizer_spec
from evals.writer_eval import build_spec as build_writer_spec
from evals.specs import EvalSpec


EVAL_SPECS: dict[str, EvalSpec] = {
    "clarifier": build_clarifier_spec(),
    "planner": build_planner_spec(),
    "searcher": build_searcher_spec(),
    "extractor": build_extractor_spec(),
    "verifier": build_verifier_spec(),
    "writer": build_writer_spec(),
    "visualizer": build_visualizer_spec(),
}


def list_specs() -> list[str]:
    return sorted(EVAL_SPECS.keys())


def get_spec(name: str) -> EvalSpec:
    try:
        return EVAL_SPECS[name]
    except KeyError as exc:
        available = ", ".join(list_specs())
        raise KeyError(f"Unknown agent '{name}'. Available: {available}") from exc
