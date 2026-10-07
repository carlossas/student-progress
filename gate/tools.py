"""Locating and running external tools the same way on Linux CI and on Windows laptops."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

GIT_BASH = Path(r"C:\Program Files\Git\bin\bash.exe")


def bash() -> str:
    """A POSIX bash. On Windows, Git Bash: `bash` on PATH may be WSL, which can't see this checkout."""
    if os.environ.get("GATE_BASH"):
        return os.environ["GATE_BASH"]
    if os.name == "nt" and GIT_BASH.exists():
        return str(GIT_BASH)
    found = shutil.which("bash")
    if not found:
        raise RuntimeError("bash not found; set GATE_BASH")
    return found


def run_module(
    module: str, args: list[str], cwd: Path, ok: tuple[int, ...], env: dict | None = None, timeout: int = 900
):
    """Runs `python -m module`; an exit code outside `ok` is a gate error, never ignored."""
    result = subprocess.run(
        [sys.executable, "-m", module, *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env={**os.environ, **(env or {})},
        timeout=timeout,
    )
    if result.returncode not in ok:
        tail = (result.stderr or result.stdout).strip()[-600:]
        raise RuntimeError(f"{module} exited {result.returncode}: {tail}")
    return result
