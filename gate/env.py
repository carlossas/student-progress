"""Local settings from `.env` at the repo root (gitignored; template: `.env.example`).

So a developer sets GEMINI_API_KEY once instead of exporting it in every terminal. Real
environment variables win: CI passes the key as a secret and never has a `.env`. No
dependency on python-dotenv: KEY=VALUE lines, `#` comments, optional quotes.
"""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path

from gate.config import GATE_ROOT

LINE = re.compile(r"^\s*(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*?)\s*$")


def load_dotenv(path: Path = GATE_ROOT / ".env") -> list[str]:
    """Sets the variables from `path` that aren't already set. Returns the names it set."""
    if not path.is_file():
        return []
    loaded = []
    for number, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        match = LINE.match(raw)
        if not match:
            print(f"{path.name}:{number}: ignored, expected KEY=VALUE", file=sys.stderr)
            continue
        name, value = match.groups()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        if value and name not in os.environ:
            os.environ[name] = value
            loaded.append(name)
    return loaded
