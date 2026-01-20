from __future__ import annotations

import json
from dataclasses import asdict
from typing import Any, AsyncGenerator, Optional

from main import PlanOutput

from .utils import configure_dspy, dspy, require_dspy, resolve_dspy_settings
from stream_events import StreamEvent, StreamEventTypes


def _coerce_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str):
        return [value] if value.strip() else []
    return [str(value)]


def _parse_context(context: str) -> dict[str, Any]:
    try:
        payload = json.loads(context)
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def _extract_goal(context: str, payload: dict[str, Any]) -> str:
    clarifier = payload.get("clarifier")
    if isinstance(clarifier, dict):
        final = clarifier.get("final")
        if isinstance(final, dict):
            interpreted = final.get("interpreted_query")
            if isinstance(interpreted, str) and interpreted.strip():
                return interpreted.strip()
        original = clarifier.get("original_query")
        if isinstance(original, str) and original.strip():
            return original.strip()
    original = payload.get("original_query")
    if isinstance(original, str) and original.strip():
        return original.strip()
    return context.strip() or "Unknown goal"


def _default_plan_output(goal: str) -> PlanOutput:
    return PlanOutput(
        plan_summary=f"Define scope and run the research plan for: {goal}",
        steps=[
            "Clarify scope and constraints",
            "Collect primary sources",
            "Extract claims and evidence",
            "Verify claims and resolve gaps",
            "Synthesize report",
        ],
        success_criteria=["At least 3 supported claims", "Clear limitations"],
        data_needs=["Primary sources", "Recent surveys"],
    )


def _normalize_output(output: PlanOutput, goal: str) -> PlanOutput:
    default = _default_plan_output(goal)
    plan_summary = (output.plan_summary or "").strip() or default.plan_summary

    steps = _coerce_list(output.steps) or default.steps
    if len(steps) < 3:
        steps = default.steps
    if len(steps) > 6:
        steps = steps[:6]

    success_criteria = _coerce_list(output.success_criteria) or default.success_criteria
    data_needs = _coerce_list(output.data_needs) or default.data_needs

    return PlanOutput(
        plan_summary=plan_summary,
        steps=steps,
        success_criteria=success_criteria,
        data_needs=data_needs,
    )


def prediction_to_output(prediction: Any, goal: str) -> PlanOutput:
    output = PlanOutput(
        plan_summary=str(getattr(prediction, "plan_summary", "") or ""),
        steps=_coerce_list(getattr(prediction, "steps", None)),
        success_criteria=_coerce_list(getattr(prediction, "success_criteria", None)),
        data_needs=_coerce_list(getattr(prediction, "data_needs", None)),
    )
    return _normalize_output(output, goal)


if dspy is not None:

    class PlanSignature(dspy.Signature):
        """Create a research plan from clarifier context JSON."""

        context_json: str = dspy.InputField(desc="Clarifier context JSON")
        plan_summary: str = dspy.OutputField(desc="One-sentence plan summary")
        steps: list[str] = dspy.OutputField(desc="3-6 ordered steps")
        success_criteria: list[str] = dspy.OutputField(desc="Measurable success criteria")
        data_needs: list[str] = dspy.OutputField(desc="Data sources or needs")


    class PlannerModule(dspy.Module):
        def __init__(self) -> None:
            super().__init__()
            self.predict = dspy.ChainOfThought(PlanSignature)

        def forward(self, context_json: str) -> Any:
            return self.predict(context_json=context_json)


class DSPyPlanner:
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
            agent_name="planner",
        )
        if configure:
            configure_dspy(settings)
        self._module = module or PlannerModule()

    def run(self, context: str) -> PlanOutput:
        payload = _parse_context(context)
        goal = _extract_goal(context, payload)
        prediction = self._module(context_json=json.dumps(payload, ensure_ascii=True))
        return prediction_to_output(prediction, goal)

    async def run_stream(self, context: str) -> AsyncGenerator[StreamEvent, None]:
        seq = 0
        yield StreamEvent(
            type=StreamEventTypes.AGENT_START,
            payload={"input": context},
            agent="planner",
            sequence=seq,
        )
        seq += 1
        try:
            output = self.run(context)
            yield StreamEvent(
                type=StreamEventTypes.AGENT_COMPLETE,
                payload={"output": asdict(output)},
                agent="planner",
                stage="plan",
                sequence=seq,
            )
        except Exception as exc:
            yield StreamEvent(
                type=StreamEventTypes.ERROR,
                payload={"error": str(exc), "error_type": type(exc).__name__},
                agent="planner",
                sequence=seq,
            )
            raise
