#!/usr/bin/env python3
"""PostToolUse hook: auto-format files touched by Edit/Write.

Reads the hook payload from stdin, and if the edited file is a Python file it
runs `ruff format` on it. Keeps the model from spending turns on formatting.
Always exits 0 — a formatting failure must never block the edit itself.
"""

import json
import subprocess
import sys
from pathlib import Path


def main() -> None:
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return

    file_path = (payload.get("tool_input") or {}).get("file_path", "")
    if not file_path:
        return

    path = Path(file_path)
    if path.suffix == ".py" and path.exists():
        subprocess.run(
            [sys.executable, "-m", "ruff", "format", "--quiet", str(path)],
            capture_output=True,
            timeout=30,
        )


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass  # never fail the hook
    sys.exit(0)
