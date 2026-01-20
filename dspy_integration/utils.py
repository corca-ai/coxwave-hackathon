from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional

from env_loader import load_env

try:
    import dspy  # type: ignore
except ImportError:  # pragma: no cover - optional dependency
    dspy = None


@dataclass(frozen=True)
class DSPySettings:
    api_key: str
    model: str
    temperature: float
    max_tokens: int


def require_dspy():
    if dspy is None:
        raise RuntimeError("DSPy is not installed.")
    return dspy


def _normalize_agent_name(agent_name: Optional[str]) -> Optional[str]:
    if not agent_name:
        return None
    return agent_name.strip().upper().replace("-", "_")


def _get_prefixed_env(agent_name: Optional[str], suffix: str) -> Optional[str]:
    normalized = _normalize_agent_name(agent_name)
    if not normalized:
        return None
    return os.getenv(f"DSPY_{normalized}_{suffix}")


def resolve_dspy_settings(
    model: Optional[str] = None,
    temperature: Optional[float] = None,
    max_tokens: Optional[int] = None,
    agent_name: Optional[str] = None,
) -> DSPySettings:
    agent_keys: list[str] = []
    normalized_agent = _normalize_agent_name(agent_name)
    if normalized_agent:
        agent_keys = [
            f"DSPY_{normalized_agent}_MODEL",
            f"DSPY_{normalized_agent}_TEMPERATURE",
            f"DSPY_{normalized_agent}_MAX_TOKENS",
        ]
    load_env(
        keys=[
            "OPENAI_API_KEY",
            "OPENAI_MODEL",
            "OPENAI_TEMPERATURE",
            "DSPY_MODEL",
            "DSPY_TEMPERATURE",
            "DSPY_MAX_TOKENS",
            *agent_keys,
        ]
    )
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not set.")

    resolved_model = (
        model
        or _get_prefixed_env(agent_name, "MODEL")
        or os.getenv("DSPY_MODEL")
        or os.getenv("OPENAI_MODEL")
        or "gpt-4o-mini"
    )

    if temperature is None:
        temp_env = (
            _get_prefixed_env(agent_name, "TEMPERATURE")
            or os.getenv("DSPY_TEMPERATURE")
            or os.getenv("OPENAI_TEMPERATURE")
        )
        temperature = float(temp_env) if temp_env is not None else 0.2

    if max_tokens is None:
        max_env = _get_prefixed_env(agent_name, "MAX_TOKENS") or os.getenv("DSPY_MAX_TOKENS")
        max_tokens = int(max_env) if max_env is not None else 1024

    return DSPySettings(
        api_key=api_key,
        model=resolved_model,
        temperature=temperature,
        max_tokens=max_tokens,
    )


def configure_dspy(settings: DSPySettings) -> None:
    dspy_module = require_dspy()

    lm_factory = None
    if hasattr(dspy_module, "OpenAI"):
        lm_factory = dspy_module.OpenAI
    elif hasattr(dspy_module, "LM"):
        lm_factory = dspy_module.LM

    if lm_factory is None:
        raise RuntimeError("DSPy OpenAI backend is not available.")

    lm = lm_factory(
        model=settings.model,
        api_key=settings.api_key,
        temperature=settings.temperature,
        max_tokens=settings.max_tokens,
    )

    if hasattr(dspy_module, "settings"):
        dspy_module.settings.configure(lm=lm)
    elif hasattr(dspy_module, "configure"):
        dspy_module.configure(lm=lm)
    else:
        raise RuntimeError("DSPy settings API is not available.")
