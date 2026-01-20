from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from main import DemoAgents


@dataclass(frozen=True)
class EvalSpec:
    name: str
    default_dataset: Path
    load_samples: Callable[[Path], list[dict[str, Any]]]
    build_input: Callable[[dict[str, Any]], Any]
    run_agent: Callable[[DemoAgents, Any], Any]
    score_output: Callable[[dict[str, Any], Any], dict[str, Any]]
    output_to_json: Callable[[Any], Any]
