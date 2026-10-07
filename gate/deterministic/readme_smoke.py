"""A15 (AGENTS#16): a new developer can follow the README's "Running locally" in < 15 minutes.

Extracts the `bash` blocks of that section and runs them in order on a fresh runner. A
long-running `uvicorn` command is started in the background and probed with GET /health.
"""

from __future__ import annotations

import re
import subprocess
import tempfile
from pathlib import Path

from gate.report.finding import Finding
from gate.tools import bash

SECTION = "## Running locally"
TIME_LIMIT_SECONDS = 15 * 60
PORT = 8765
MARKER = "::readme-smoke-step::"


def extract_commands(readme: str) -> list[tuple[int, str]]:
    """(README line, command) for every line of the bash blocks in the section."""
    commands, in_section, in_block = [], False, False
    for number, line in enumerate(readme.splitlines(), start=1):
        if line.startswith("## "):
            in_section = line.strip() == SECTION
            continue
        if not in_section:
            continue
        if line.strip().startswith("```"):
            in_block = not in_block and line.strip() in ("```bash", "```sh", "```shell")
            continue
        if in_block and line.strip() and not line.strip().startswith("#"):
            commands.append((number, line.strip()))
    return commands


def build_script(commands: list[tuple[int, str]]) -> str:
    lines = [
        "set -e",
        'cleanup() { [ -f .smoke.pid ] && kill "$(cat .smoke.pid)" 2>/dev/null; rm -f .smoke.pid; }',
        "trap cleanup EXIT",
    ]
    for number, command in commands:
        lines.append(f"echo '{MARKER}{number}'")
        if re.match(r"^uvicorn\b", command):
            server = re.sub(r"\s--reload\b", "", command) + f" --port {PORT}"
            lines += [
                f"{server} > .smoke-server.log 2>&1 & echo $! > .smoke.pid",
                f"for i in $(seq 1 30); do curl -fsS http://127.0.0.1:{PORT}/health && break; sleep 1; done",
                f"curl -fsS http://127.0.0.1:{PORT}/health",
            ]
        else:
            lines.append(command)
    return "\n".join(lines) + "\n"


def _finding(line: int | None, message: str) -> Finding:
    return Finding(
        rule="AGENTS#16",
        severity="medium",
        source="deterministic:readme_smoke",
        check="A15",
        file="README.md",
        line=line,
        message=message,
        suggestion="Fix the README so its 'Running locally' steps work on a clean machine, or fix the setup they describe.",
    )


def run(repo: Path, time_limit: int = TIME_LIMIT_SECONDS) -> list[Finding]:
    readme = (repo / "README.md").read_text(encoding="utf-8") if (repo / "README.md").exists() else ""
    commands = extract_commands(readme)
    if not commands:
        return [_finding(None, f"README.md has no `bash` commands under '{SECTION}'.")]
    by_line = dict(commands)
    with tempfile.NamedTemporaryFile("w", suffix=".sh", delete=False, encoding="utf-8", newline="\n") as script:
        script.write(build_script(commands))
    try:
        result = subprocess.run([bash(), script.name], cwd=repo, capture_output=True, text=True, timeout=time_limit)
    except subprocess.TimeoutExpired:
        return [
            _finding(
                None, f"Following the README took longer than {time_limit // 60 or 1} minute(s) (limit {time_limit}s)."
            )
        ]
    finally:
        Path(script.name).unlink(missing_ok=True)
    if result.returncode == 0:
        return []
    steps = re.findall(rf"{re.escape(MARKER)}(\d+)", result.stdout)
    line = int(steps[-1]) if steps else None
    output = (result.stderr or result.stdout).strip().splitlines()[-1:] or [""]
    return [_finding(line, f"README step `{by_line.get(line, '?')}` fails on a clean runner: {output[0][:200]}")]
