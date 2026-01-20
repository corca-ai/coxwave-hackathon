from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from urllib.error import URLError
from urllib.request import Request, urlopen


def _wait_for_health(url: str, timeout: float) -> dict:
    deadline = time.monotonic() + timeout
    last_error: str | None = None
    while time.monotonic() < deadline:
        try:
            req = Request(url, headers={"Accept": "application/json"})
            with urlopen(req, timeout=2) as response:
                payload = json.loads(response.read().decode("utf-8"))
                return payload
        except (URLError, json.JSONDecodeError, ConnectionError) as exc:
            last_error = str(exc)
            time.sleep(0.4)
    raise RuntimeError(f"Health check timed out. Last error: {last_error}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Smoke test for server.py")
    parser.add_argument("--host", default="http://localhost")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--timeout", type=float, default=15.0)
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[1]
    server_cmd = [sys.executable, "server.py"]
    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"

    process = subprocess.Popen(
        server_cmd,
        cwd=repo_root,
        env=env,
        stdout=None,
        stderr=None,
    )

    try:
        health_url = f"{args.host}:{args.port}/health"
        payload = _wait_for_health(health_url, timeout=args.timeout)
        print("Health check response:")
        print(json.dumps(payload, indent=2, ensure_ascii=True))
        if payload.get("status") != "ok":
            return 2
    except Exception as exc:
        print(f"Smoke test failed: {exc}")
        return 1
    finally:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
