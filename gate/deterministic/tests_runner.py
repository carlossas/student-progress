"""A8, A10 (AGENTS#6): the suite passes and changed lines are >= 85% covered.

Runs the PR's tests in the PR checkout (never in the AI job, which holds the Gemini key).
"""

from __future__ import annotations

import tempfile
from pathlib import Path

from gate.config import COVERAGE_PACKAGES
from gate.diff import DiffContext
from gate.report.adapters import coverage_findings, junit_failures
from gate.report.finding import Finding
from gate.tools import run_module

NO_TESTS_COLLECTED = 5


def run(ctx: DiffContext, out_dir: Path | None = None) -> list[Finding]:
    return execute(ctx, out_dir)[0]


def execute(ctx: DiffContext, out_dir: Path | None = None, always: bool = False) -> tuple[list[Finding], str]:
    """(findings, pytest's summary line). Skipped when no Python changed, unless `always`."""
    if not always and not any(p.endswith(".py") for p in ctx.files()):
        return [], "skipped: no Python changes"
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(out_dir or tmp)
        out.mkdir(parents=True, exist_ok=True)
        junit, coverage = out / "junit.xml", out / "coverage.xml"
        args = [
            "-q",
            "-p",
            "no:cacheprovider",
            "-m",
            "not ai",
            "-o",
            "junit_family=xunit1",
            f"--junitxml={junit}",
            *[f"--cov={p}" for p in COVERAGE_PACKAGES],
            f"--cov-report=xml:{coverage}",
        ]
        result = run_module("pytest", args, ctx.repo, ok=(0, 1, NO_TESTS_COLLECTED), env={"PYTHONPATH": str(ctx.repo)})
        findings = junit_failures(junit.read_text(encoding="utf-8"), ctx.repo) if junit.exists() else []
        if result.returncode == 1 and not findings:
            raise RuntimeError(f"pytest failed without a test failure (collection error?): {result.stdout[-400:]}")
        if coverage.exists():
            changed = {p: ctx.lines(p) for p in ctx.files()}
            findings += coverage_findings(coverage.read_text(encoding="utf-8"), ctx.repo, changed)
    lines = [ln.strip("= ") for ln in result.stdout.strip().splitlines() if ln.strip()]
    return findings, (lines[-1] if lines else "no output")
