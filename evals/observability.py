from __future__ import annotations

import json
import os
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any


def _artifact_dir() -> Path:
    path = Path(os.getenv("EVAL_ARTIFACT_DIR", "evals/_artifacts"))
    path.mkdir(parents=True, exist_ok=True)
    return path


def write_artifact(filename: str, content: str) -> Path:
    path = _artifact_dir() / filename
    path.write_text(content)
    return path


def write_json_artifact(filename: str, data: Any) -> Path:
    payload = asdict(data) if is_dataclass(data) else data
    text = json.dumps(payload, indent=2, ensure_ascii=True)
    return write_artifact(filename, text)
