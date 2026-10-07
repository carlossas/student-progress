"""Merges both pipelines' findings: one finding per (rule, file, line); deterministic wins."""

from __future__ import annotations

from gate.report.finding import SEVERITY_RANK, Finding


def dedupe(findings: list[Finding]) -> list[Finding]:
    ordered = sorted(findings, key=lambda f: (f.source.startswith("ai:"), SEVERITY_RANK[f.severity]))
    kept: dict[tuple, Finding] = {}
    for f in ordered:
        kept.setdefault((f.rule, f.file, f.line), f)
    return list(kept.values())
