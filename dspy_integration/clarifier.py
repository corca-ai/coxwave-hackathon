from __future__ import annotations

from dataclasses import replace
from typing import Any, Optional

from main import ClarifyOutput

from .utils import configure_dspy, dspy, require_dspy, resolve_dspy_settings


def _coerce_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item) for item in value if str(item).strip()]
    if isinstance(value, str):
        return [value] if value.strip() else []
    return [str(value)]


def _is_ambiguous(query: str) -> bool:
    return len(query.split()) <= 4


def _normalize_output(output: ClarifyOutput, query: str) -> ClarifyOutput:
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


def prediction_to_output(prediction: Any, query: str) -> ClarifyOutput:
    output = ClarifyOutput(
        is_clear_enough=bool(getattr(prediction, "is_clear_enough", False)),
        clarifying_questions=_coerce_list(getattr(prediction, "clarifying_questions", None)),
        interpreted_query=str(getattr(prediction, "interpreted_query", "") or ""),
        assumptions=_coerce_list(getattr(prediction, "assumptions", None)),
    )
    return _normalize_output(output, query)


if dspy is not None:

    class ClarifySignature(dspy.Signature):
        """Clarify a research query with structured fields."""

        query: str = dspy.InputField(desc="User research query")
        is_clear_enough: bool = dspy.OutputField(
            desc="True if the query is specific enough to proceed"
        )
        clarifying_questions: list[str] = dspy.OutputField(
            desc="1-3 clarifying questions if needed"
        )
        interpreted_query: str = dspy.OutputField(desc="Normalized interpretation")
        assumptions: list[str] = dspy.OutputField(desc="Assumptions being made")


    class ClarifierModule(dspy.Module):
        def __init__(self) -> None:
            super().__init__()
            self.predict = dspy.ChainOfThought(ClarifySignature)

        def forward(self, query: str) -> Any:
            return self.predict(query=query)


class DSPyClarifier:
    def __init__(
        self,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        module: Optional[Any] = None,
        configure: bool = True,
    ) -> None:
        require_dspy()
        settings = resolve_dspy_settings(
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            agent_name="clarifier",
        )
        if configure:
            configure_dspy(settings)
        self._module = module or ClarifierModule()

    def run(self, query: str) -> ClarifyOutput:
        prediction = self._module(query=query)
        return prediction_to_output(prediction, query)
