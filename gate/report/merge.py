"""Merges both pipelines' findings: one finding per problem; deterministic wins.

Exact duplicates share (rule, file, line). Across pipelines the same problem can point at
different lines of one statement (the scripts flag `student.full_name` on line 59, the AI
flags `student.email` on line 60 of the same log call), so an AI finding within
SAME_PROBLEM_LINES of a deterministic finding with the same rule and file is the same problem.
This is the tolerance the eval uses to match findings to the ground truth.
"""

from __future__ import annotations

from gate.report.finding import SEVERITY_RANK, Finding

SAME_PROBLEM_LINES = 3


def _covered_by_script(f: Finding, scripts: list[Finding]) -> bool:
    return f.line is not None and any(
        s.rule == f.rule and s.file == f.file and s.line is not None and abs(s.line - f.line) <= SAME_PROBLEM_LINES
        for s in scripts
    )


def dedupe(findings: list[Finding]) -> list[Finding]:
    ordered = sorted(findings, key=lambda f: (f.source.startswith("ai:"), SEVERITY_RANK[f.severity]))
    kept: dict[tuple, Finding] = {}
    for f in ordered:
        kept.setdefault((f.rule, f.file, f.line), f)
    scripts = [f for f in kept.values() if not f.source.startswith("ai:")]
    return [f for f in kept.values() if not (f.source.startswith("ai:") and _covered_by_script(f, scripts))]
