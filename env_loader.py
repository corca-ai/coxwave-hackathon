from __future__ import annotations

import os
from pathlib import Path
from typing import Iterable


def load_env(path: str = ".env", keys: Iterable[str] | None = None) -> None:
    """Load KEY=VALUE pairs from a .env file into os.environ if missing.

    This is a minimal loader: supports lines like KEY=VALUE, ignores comments and blanks.
    """
    env_path = Path(path)
    if not env_path.exists():
        return

    wanted = set(keys) if keys else None

    for line in env_path.read_text().splitlines():
        raw = line.strip()
        if not raw or raw.startswith("#") or "=" not in raw:
            continue
        key, value = raw.split("=", 1)
        key = key.strip()
        value = value.strip().strip("\"'")
        if wanted is not None and key not in wanted:
            continue
        if not os.getenv(key):
            os.environ[key] = value
