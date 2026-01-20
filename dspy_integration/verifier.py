from __future__ import annotations

import json
from dataclasses import asdict
from typing import Any, AsyncGenerator, Optional

from main import NextAction, Verification, VerifyOutput

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


def _parse_extract(context: str) -> dict[str, Any]:
    try:
        payload = json.loads(context)
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def _extract_claims(payload: dict[str, Any]) -> list[dict[str, Any]]:
    claims = payload.get("claims")
    if not isinstance(claims, list):
        return []
    return [item for item in claims if isinstance(item, dict)]


def _default_verdict(claim: dict[str, Any]) -> Verification:
    claim_text = str(claim.get("claim") or "")
    evidence = str(claim.get("evidence") or "")
    source_id = str(claim.get("source_id") or "")
    verdict = "supported" if evidence.strip() else "weak"
    confidence = 0.6 if verdict == "supported" else 0.4
    rationale = "Evidence provided." if evidence.strip() else "Evidence is limited."
    return Verification(
        claim=claim_text or "Unknown claim",
        verdict=verdict,
        rationale=rationale,
        confidence=confidence,
        source_id=source_id or None,
        required_evidence=[],
    )


def _normalize_verdicts(raw: Any, claims: list[dict[str, Any]]) -> list[Verification]:
    allowed = {"supported", "weak", "unsupported", "conflicting"}
    verdicts: list[Verification] = []
    if isinstance(raw, list):
        for item in raw:
            if isinstance(item, Verification):
                verdicts.append(item)
                continue
            if not isinstance(item, dict):
                continue
            claim_text = str(item.get("claim") or "").strip()
            if not claim_text:
                continue
            verdict = str(item.get("verdict") or "").strip().lower()
            if verdict not in allowed:
                verdict = "weak"
            rationale = str(item.get("rationale") or "").strip()
            confidence = float(item.get("confidence") or 0.0)
            confidence = max(0.0, min(1.0, confidence))
            source_id = item.get("source_id")
            required_evidence = _coerce_list(item.get("required_evidence"))
            verdicts.append(
                Verification(
                    claim=claim_text,
                    verdict=verdict,
                    rationale=rationale or "No rationale provided.",
                    confidence=confidence,
                    source_id=str(source_id) if source_id else None,
                    required_evidence=required_evidence,
                )
            )

    if not verdicts:
        verdicts = [_default_verdict(claim) for claim in claims]
    return verdicts


def _normalize_actions(raw: Any) -> list[NextAction]:
    actions: list[NextAction] = []
    if not isinstance(raw, list):
        return actions
    for item in raw:
        if isinstance(item, NextAction):
            actions.append(item)
            continue
        if not isinstance(item, dict):
            continue
        action_type = str(item.get("action_type") or item.get("type") or "").strip()
        if action_type not in {"search_expand", "search_more_papers", "reextract", "stop"}:
            continue
        priority = int(item.get("priority") or 1)
        why = str(item.get("why") or "").strip()
        suggested = _coerce_list(item.get("suggested_queries"))
        concepts = _coerce_list(item.get("target_concepts"))
        actions.append(
            NextAction(
                action_type=action_type,
                priority=priority,
                why=why,
                suggested_queries=suggested,
                target_concepts=concepts,
            )
        )
    return actions


def prediction_to_output(prediction: Any, payload: dict[str, Any]) -> VerifyOutput:
    claims = _extract_claims(payload)
    verdicts = _normalize_verdicts(getattr(prediction, "verdicts", None), claims)
    is_enough = bool(getattr(prediction, "is_enough", False))
    next_search_queries = _coerce_list(getattr(prediction, "next_search_queries", None))
    next_actions = _normalize_actions(getattr(prediction, "next_actions", None))

    if not next_actions:
        if is_enough:
            next_actions = [
                NextAction(
                    action_type="stop",
                    priority=1,
                    why="Sufficient evidence collected.",
                    suggested_queries=[],
                    target_concepts=[],
                )
            ]
        else:
            next_actions = [
                NextAction(
                    action_type="search_expand",
                    priority=1,
                    why="Evidence is insufficient; expand search.",
                    suggested_queries=next_search_queries,
                    target_concepts=[],
                )
            ]
    return VerifyOutput(
        verdicts=verdicts,
        is_enough=is_enough,
        next_search_queries=next_search_queries,
        next_actions=next_actions,
    )


if dspy is not None:

    class VerifySignature(dspy.Signature):
        """Verify extracted claims and decide next actions."""

        extract_json: str = dspy.InputField(desc="Extract output JSON")
        verdicts: list[dict] = dspy.OutputField(desc="Claim verdicts")
        is_enough: bool = dspy.OutputField(desc="True if evidence is sufficient")
        next_search_queries: list[str] = dspy.OutputField(desc="Suggested follow-up queries")
        next_actions: list[dict] = dspy.OutputField(desc="Next actions for orchestrator")


    class VerifierModule(dspy.Module):
        def __init__(self) -> None:
            super().__init__()
            self.predict = dspy.ChainOfThought(VerifySignature)

        def forward(self, extract_json: str) -> Any:
            return self.predict(extract_json=extract_json)


class DSPyVerifier:
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
            agent_name="verifier",
        )
        if configure:
            configure_dspy(settings)
        self._module = module or VerifierModule()

    def run(self, context: str) -> VerifyOutput:
        payload = _parse_extract(context)
        prediction = self._module(extract_json=json.dumps(payload, ensure_ascii=True))
        return prediction_to_output(prediction, payload)

    async def run_stream(self, context: str) -> AsyncGenerator[StreamEvent, None]:
        seq = 0
        yield StreamEvent(
            type=StreamEventTypes.AGENT_START,
            payload={"input": context},
            agent="verifier",
            sequence=seq,
        )
        seq += 1
        try:
            output = self.run(context)
            yield StreamEvent(
                type=StreamEventTypes.AGENT_COMPLETE,
                payload={"output": asdict(output)},
                agent="verifier",
                stage="verify",
                sequence=seq,
            )
        except Exception as exc:
            yield StreamEvent(
                type=StreamEventTypes.ERROR,
                payload={"error": str(exc), "error_type": type(exc).__name__},
                agent="verifier",
                sequence=seq,
            )
            raise
