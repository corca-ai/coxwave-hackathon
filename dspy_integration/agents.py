from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from .clarifier import DSPyClarifier
from .extractor import DSPyExtractor
from .planner import DSPyPlanner
from .searcher import DSPySearcher
from .verifier import DSPyVerifier
from .visualizer import DSPyVisualizer
from .writer import DSPyWriter


@dataclass
class DSPyAgents:
    clarifier: Optional[DSPyClarifier] = None
    planner: Optional[DSPyPlanner] = None
    searcher: Optional[DSPySearcher] = None
    extractor: Optional[DSPyExtractor] = None
    verifier: Optional[DSPyVerifier] = None
    writer: Optional[DSPyWriter] = None
    visualizer: Optional[DSPyVisualizer] = None


def build_dspy_agents(agent_name: str) -> DSPyAgents:
    if agent_name == "clarifier":
        return DSPyAgents(clarifier=DSPyClarifier())
    if agent_name == "planner":
        return DSPyAgents(planner=DSPyPlanner())
    if agent_name == "searcher":
        return DSPyAgents(searcher=DSPySearcher())
    if agent_name == "extractor":
        return DSPyAgents(extractor=DSPyExtractor())
    if agent_name == "verifier":
        return DSPyAgents(verifier=DSPyVerifier())
    if agent_name == "writer":
        return DSPyAgents(writer=DSPyWriter())
    if agent_name == "visualizer":
        return DSPyAgents(visualizer=DSPyVisualizer())
    raise ValueError(f"Unsupported DSPy agent: {agent_name}")
