"""Merges both pipelines' findings: one finding per problem; deterministic wins.

Exact duplicates share (rule, file, line). Across pipelines the same problem can point at
different lines of one statement (the scripts flag `student.full_name` on line 59, the AI
flags `student.email` on line 60 of the same log call), so an AI finding within
SAME_PROBLEM_LINES of a deterministic finding with the same rule and file is the same problem.
This is the tolerance the eval uses to match findings to the ground truth.

One root cause, one finding: when no test was touched at all (A9), the changed-line coverage
finding (A10) says the same thing and is dropped.
"""

from __future__ import annotations

from gate.report.finding import SEVERITY_RANK, Finding

SAME_PROBLEM_LINES = 3


def _covered_by_script(f: Finding, scripts: list[Finding]) -> bool:
    return f.line is not None and any(
        s.rule == f.rule and s.file == f.file and s.line is not None and abs(s.line - f.line) <= SAME_PROBLEM_LINES
        for s in scripts
    )


def _collapse_untested(findings: list[Finding]) -> list[Finding]:
    """No tests touched (A9) already explains low changed-line coverage (A10): report it once."""
    if not any(f.check == "A9" for f in findings):
        return findings
    return [f for f in findings if f.check != "A10"]


def dedupe(findings: list[Finding]) -> list[Finding]:
    ordered = sorted(findings, key=lambda f: (f.source.startswith("ai:"), SEVERITY_RANK[f.severity]))
    kept: dict[tuple, Finding] = {}
    for f in ordered:
        kept.setdefault((f.rule, f.file, f.line), f)
    scripts = [f for f in kept.values() if not f.source.startswith("ai:")]
    unique = [f for f in kept.values() if not (f.source.startswith("ai:") and _covered_by_script(f, scripts))]
    return _collapse_untested(unique)
