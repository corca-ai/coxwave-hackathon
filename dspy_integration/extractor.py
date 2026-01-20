from __future__ import annotations

import json
from dataclasses import asdict
from typing import Any, AsyncGenerator, Optional

from main import Claim, ExtractOutput

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


def _parse_search(context: str) -> dict[str, Any]:
    try:
        payload = json.loads(context)
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def _source_ids(payload: dict[str, Any]) -> list[str]:
    sources = payload.get("sources")
    if not isinstance(sources, list):
        return []
    ids: list[str] = []
    for source in sources:
        if isinstance(source, dict):
            source_id = str(source.get("source_id") or "")
            if source_id:
                ids.append(source_id)
    return ids


def _fallback_claim(payload: dict[str, Any]) -> Claim:
    sources = payload.get("sources")
    if isinstance(sources, list) and sources:
        first = sources[0] if isinstance(sources[0], dict) else {}
    else:
        first = {}
    source_id = str(first.get("source_id") or "unknown")
    snippet = str(first.get("snippet") or "")
    claim_text = snippet.strip() or "No claims extracted from provided sources."
    evidence = snippet.strip() or "Evidence unavailable in provided sources."
    return Claim(claim=claim_text, evidence=evidence, source_id=source_id, confidence=0.3)


def _normalize_claims(raw_claims: Any, source_ids: list[str]) -> list[Claim]:
    if not isinstance(raw_claims, list):
        raw_claims = []
    claims: list[Claim] = []
    seen: set[str] = set()
    min_evidence_chars = 20
    for item in raw_claims:
        if isinstance(item, Claim):
            candidate = item
        elif isinstance(item, dict):
            claim_text = str(item.get("claim") or "").strip()
            evidence = str(item.get("evidence") or "").strip()
            source_id = str(item.get("source_id") or "").strip()
            confidence = float(item.get("confidence") or 0.0)
            candidate = Claim(
                claim=claim_text,
                evidence=evidence,
                source_id=source_id,
                confidence=confidence,
            )
        else:
            continue

        if not candidate.claim:
            continue
        if candidate.claim in seen:
            continue
        if not candidate.evidence or len(candidate.evidence) < min_evidence_chars:
            continue
        if candidate.source_id and source_ids and candidate.source_id not in source_ids:
            continue
        if not candidate.source_id and source_ids:
            candidate = Claim(
                claim=candidate.claim,
                evidence=candidate.evidence,
                source_id=source_ids[0],
                confidence=candidate.confidence,
            )
        candidate_conf = max(0.0, min(1.0, candidate.confidence))
        candidate = Claim(
            claim=candidate.claim,
            evidence=candidate.evidence,
            source_id=candidate.source_id or (source_ids[0] if source_ids else "unknown"),
            confidence=candidate_conf,
        )
        claims.append(candidate)
        seen.add(candidate.claim)
        if len(claims) >= 8:
            break
    return claims


def prediction_to_output(prediction: Any, payload: dict[str, Any]) -> ExtractOutput:
    source_ids = _source_ids(payload)
    claims = _normalize_claims(getattr(prediction, "claims", None), source_ids)
    if not claims:
        claims = [_fallback_claim(payload)]
    gaps = _coerce_list(getattr(prediction, "gaps", None))
    if not gaps:
        gaps = ["Need more evidence to support additional claims."]
    return ExtractOutput(claims=claims, gaps=gaps)


if dspy is not None:

    class ExtractSignature(dspy.Signature):
        """Extract claims from search output JSON."""

        search_json: str = dspy.InputField(desc="Search output JSON (refined_query + sources)")
        claims: list[dict] = dspy.OutputField(
            desc="Claims with claim, evidence, source_id, confidence"
        )
        gaps: list[str] = dspy.OutputField(desc="Remaining gaps or follow-up needs")


    class ExtractorModule(dspy.Module):
        def __init__(self) -> None:
            super().__init__()
            self.predict = dspy.ChainOfThought(ExtractSignature)

        def forward(self, search_json: str) -> Any:
            return self.predict(search_json=search_json)


class DSPyExtractor:
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
            agent_name="extractor",
        )
        if configure:
            configure_dspy(settings)
        self._module = module or ExtractorModule()

    def run(self, context: str) -> ExtractOutput:
        payload = _parse_search(context)
        prediction = self._module(search_json=json.dumps(payload, ensure_ascii=True))
        return prediction_to_output(prediction, payload)

    async def run_stream(self, context: str) -> AsyncGenerator[StreamEvent, None]:
        seq = 0
        yield StreamEvent(
            type=StreamEventTypes.AGENT_START,
            payload={"input": context},
            agent="extractor",
            sequence=seq,
        )
        seq += 1
        try:
            output = self.run(context)
            yield StreamEvent(
                type=StreamEventTypes.AGENT_COMPLETE,
                payload={"output": asdict(output)},
                agent="extractor",
                stage="extract",
                sequence=seq,
            )
        except Exception as exc:
            yield StreamEvent(
                type=StreamEventTypes.ERROR,
                payload={"error": str(exc), "error_type": type(exc).__name__},
                agent="extractor",
                sequence=seq,
            )
            raise
