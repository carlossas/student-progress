"""A6, A11, A13 (AGENTS#5, #7): ruff lint + format and vulture on changed Python files.

The ruff config is the gate's own (gate/config/ruff.toml), not the PR's.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

from gate.config import RUFF_CONFIG
from gate.diff import DiffContext
from gate.report.adapters import ruff_findings, ruff_format_findings, vulture_findings
from gate.report.finding import Finding
from gate.tools import run_module


def _materialize(ctx: DiffContext, files: list[str], into: Path) -> Path:
    """Staged mode: lint what is in the index, not the working tree."""
    for path in files:
        target = into / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(ctx.read(path) or "", encoding="utf-8")
    return into


def _lint(root: Path, files: list[str]) -> list[Finding]:
    config = ["--config", str(RUFF_CONFIG), "--no-cache"]
    check = run_module("ruff", ["check", *config, "--output-format", "json", *files], root, ok=(0, 1))
    fmt = run_module("ruff", ["format", *config, "--diff", *files], root, ok=(0, 1))
    dead = run_module("vulture", [*files, "--min-confidence", "100"], root, ok=(0, 3))
    return (
        ruff_findings(check.stdout, root) + ruff_format_findings(fmt.stdout, root) + vulture_findings(dead.stdout, root)
    )


def check(ctx: DiffContext) -> list[Finding]:
    files = [p for p in ctx.files() if p.endswith(".py")]
    if not files:
        return []
    if ctx.mode == "staged":
        with tempfile.TemporaryDirectory() as tmp:
            findings = _lint(_materialize(ctx, files, Path(tmp)), files)
    else:
        findings = _lint(ctx.repo, files)
    return [f for f in findings if f.line is None or ctx.is_changed(f.file, f.line)]
