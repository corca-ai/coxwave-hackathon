from __future__ import annotations

import os
from dataclasses import replace
from typing import Any, Optional

from env_loader import load_env
from main import ClarifyOutput
from src.shared.config import MODEL_HEAVY

try:
    import dspy  # type: ignore
except ImportError:  # pragma: no cover - optional dependency
    dspy = None


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


def _configure_dspy(model_name: str, api_key: str, temperature: float, max_tokens: int) -> None:
    if dspy is None:
        raise RuntimeError("DSPy is not installed.")

    lm_factory = None
    if hasattr(dspy, "OpenAI"):
        lm_factory = dspy.OpenAI
    elif hasattr(dspy, "LM"):
        lm_factory = dspy.LM

    if lm_factory is None:
        raise RuntimeError("DSPy OpenAI backend is not available.")

    lm = lm_factory(
        model=model_name,
        api_key=api_key,
        temperature=temperature,
        max_tokens=max_tokens,
    )

    if hasattr(dspy, "settings"):
        dspy.settings.configure(lm=lm)
    elif hasattr(dspy, "configure"):
        dspy.configure(lm=lm)
    else:
        raise RuntimeError("DSPy settings API is not available.")


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
    ) -> None:
        load_env(
            keys=[
                "OPENAI_API_KEY",
                "OPENAI_MODEL",
                "OPENAI_TEMPERATURE",
                "DSPY_MODEL",
                "DSPY_TEMPERATURE",
                "DSPY_MAX_TOKENS",
            ]
        )
        if dspy is None:
            raise RuntimeError("DSPy is not installed.")

        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY is not set.")

        resolved_model = (
            model
            or os.getenv("DSPY_MODEL")
            or os.getenv("OPENAI_MODEL")
            or MODEL_HEAVY
        )

        if temperature is None:
            temp_env = os.getenv("DSPY_TEMPERATURE") or os.getenv("OPENAI_TEMPERATURE")
            temperature = float(temp_env) if temp_env is not None else 0.2

        if max_tokens is None:
            max_env = os.getenv("DSPY_MAX_TOKENS")
            max_tokens = int(max_env) if max_env is not None else 1024

        _configure_dspy(resolved_model, api_key, temperature, max_tokens)
        self._module = ClarifierModule()

    def run(self, query: str) -> ClarifyOutput:
        prediction = self._module(query=query)
        output = ClarifyOutput(
            is_clear_enough=bool(getattr(prediction, "is_clear_enough", False)),
            clarifying_questions=_coerce_list(
                getattr(prediction, "clarifying_questions", None)
            ),
            interpreted_query=str(getattr(prediction, "interpreted_query", "") or ""),
            assumptions=_coerce_list(getattr(prediction, "assumptions", None)),
        )
        return _normalize_output(output, query)
