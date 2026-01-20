from __future__ import annotations

import os
from dataclasses import replace
from typing import Optional

from agents import Agent, ModelSettings, Runner

from main import (
    ClarifyOutput,
    DemoAgents,
    MockExtractor,
    MockPlanner,
    MockSearcher,
    MockVerifier,
    MockVisualizer,
    MockWriter,
)
from env_loader import load_env


class OpenAIClarifier:
    def __init__(self, model: Optional[str] = None, temperature: Optional[float] = None) -> None:
        load_env(keys=["OPENAI_API_KEY", "OPENAI_MODEL", "OPENAI_TEMPERATURE"])
        resolved_model = model or os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        temp_value = temperature
        if temp_value is None:
            temp_value = float(os.getenv("OPENAI_TEMPERATURE", "0.2"))
        self._agent = Agent(
            name="Clarifier",
            model=resolved_model,
            model_settings=ModelSettings(temperature=temp_value),
            output_type=ClarifyOutput,
            instructions=(
                "You clarify a research query for a serious user. "
                "If the query is ambiguous or too short, ask 1-3 clarifying questions and set "
                "is_clear_enough=false. Otherwise, set is_clear_enough=true. "
                "Always return interpreted_query and assumptions (can be empty list). "
                "Keep questions short and concrete."
            ),
        )

    def run(self, query: str) -> ClarifyOutput:
        load_env(keys=["OPENAI_API_KEY"])
        if not os.getenv("OPENAI_API_KEY"):
            raise RuntimeError("OPENAI_API_KEY is not set.")
        result = Runner.run_sync(self._agent, query)
        output = result.final_output
        if not isinstance(output, ClarifyOutput):
            raise TypeError("Clarifier output is not ClarifyOutput")
        return _normalize_clarify_output(output, query)


def _normalize_clarify_output(output: ClarifyOutput, query: str) -> ClarifyOutput:
    interpreted_query = output.interpreted_query or query
    assumptions = output.assumptions or []
    clarifying_questions = output.clarifying_questions or []
    is_clear_enough = output.is_clear_enough

    if clarifying_questions and is_clear_enough:
        is_clear_enough = False

    if _is_ambiguous(query):
        if not clarifying_questions:
            clarifying_questions = [
                "What is the target domain or industry?",
                "What time range or scope should we focus on?",
            ]
        is_clear_enough = False
    elif not is_clear_enough and not clarifying_questions:
        clarifying_questions = ["What specific scope or constraints should we use?"]

    if len(clarifying_questions) > 3:
        clarifying_questions = clarifying_questions[:3]

    return replace(
        output,
        interpreted_query=interpreted_query,
        assumptions=assumptions,
        clarifying_questions=clarifying_questions,
        is_clear_enough=is_clear_enough,
    )


def _is_ambiguous(query: str) -> bool:
    return len(query.split()) <= 4


def build_agents() -> DemoAgents:
    return DemoAgents(
        clarifier=OpenAIClarifier(),
        planner=MockPlanner(),
        searcher=MockSearcher(),
        extractor=MockExtractor(),
        verifier=MockVerifier(),
        writer=MockWriter(),
        visualizer=MockVisualizer(),
    )
