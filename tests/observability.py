from __future__ import annotations

import json
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any


ARTIFACT_DIR = Path("tests/_artifacts")


def write_artifact(filename: str, content: str) -> Path:
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    path = ARTIFACT_DIR / filename
    path.write_text(content)
    return path


def write_json_artifact(filename: str, data: Any) -> Path:
    if is_dataclass(data):
        payload = asdict(data)
    else:
        payload = data
    text = json.dumps(payload, indent=2, ensure_ascii=True)
    return write_artifact(filename, text)
