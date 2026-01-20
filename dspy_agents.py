from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from dspy_clarifier import DSPyClarifier
from dspy_visualizer import DSPyVisualizer


@dataclass
class DSPyAgents:
    clarifier: Optional[DSPyClarifier] = None
    visualizer: Optional[DSPyVisualizer] = None


def build_dspy_agents(agent_name: str) -> DSPyAgents:
    if agent_name == "clarifier":
        return DSPyAgents(clarifier=DSPyClarifier())
    if agent_name == "visualizer":
        return DSPyAgents(visualizer=DSPyVisualizer())
    raise ValueError(f"Unsupported DSPy agent: {agent_name}")
