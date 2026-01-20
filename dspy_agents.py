from __future__ import annotations

from dataclasses import dataclass

from dspy_clarifier import DSPyClarifier


@dataclass
class DSPyAgents:
    clarifier: DSPyClarifier


def build_dspy_agents() -> DSPyAgents:
    return DSPyAgents(clarifier=DSPyClarifier())
