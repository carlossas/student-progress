"""R15 (AGENTS#15): every change goes through the gate.

Checks the gate workflow itself: PRs to all branches, no path filters, no skip conditions,
the deterministic job unconditional, the AI job only for develop/main.
"""

from __future__ import annotations

import re

import yaml

from gate.diff import DiffContext
from gate.report.finding import Finding

GATE_WORKFLOW = ".github/workflows/quality-gate.yml"
SKIP_PATTERN = re.compile(r"labels|\.title|skip|draft|head_ref|\.body|github\.actor", re.I)


def problems(text: str) -> list[str]:
    data = yaml.safe_load(text) or {}
    triggers = data.get("on", data.get(True)) or {}
    found = []
    pr = triggers.get("pull_request") if isinstance(triggers, dict) else None
    if pr is None and not (isinstance(triggers, list) and "pull_request" in triggers):
        found.append("does not run on `pull_request`")
    if isinstance(pr, dict):
        for key in ("paths", "paths-ignore", "branches-ignore"):
            if key in pr:
                found.append(f"`pull_request.{key}` lets changes skip the gate")
        if "branches" in pr and pr["branches"] not in (["**"], ["*"]):
            found.append("`pull_request.branches` limits which PRs are checked")
    jobs = data.get("jobs") or {}
    for name, job in jobs.items():
        conditions = [str(job.get("if", ""))] + [str(s.get("if", "")) for s in job.get("steps", []) or []]
        for condition in conditions:
            if condition and SKIP_PATTERN.search(condition):
                found.append(f"job `{name}` has a skip condition: `{condition.strip()}`")
    if "deterministic" not in jobs:
        found.append("missing the `deterministic` job")
    elif jobs["deterministic"].get("if"):
        found.append("the `deterministic` job must run on every PR (no `if`)")
    ai_if = str((jobs.get("ai") or {}).get("if", ""))
    if "ai" not in jobs:
        found.append("missing the `ai` job")
    elif not ("base_ref" in ai_if and "'main'" in ai_if and "'develop'" in ai_if):
        found.append("the `ai` job must run exactly for PRs into `develop` and `main`")
    return found


def check(ctx: DiffContext) -> list[Finding]:
    if ctx.mode == "staged" or not any(p.startswith(".github/workflows/") for p in ctx.changed):
        return []
    text = ctx.read(GATE_WORKFLOW)
    issues = ["the gate workflow was removed"] if text is None else problems(text)
    return [
        Finding(
            rule="AGENTS#15",
            severity="high",
            source="deterministic:workflow_policy",
            check="R15",
            file=GATE_WORKFLOW,
            message=f"Gate workflow {issue}.",
            suggestion="Every PR must go through the gate. If a change needs different handling, change the gate's checks, not its triggers.",
        )
        for issue in issues
    ]
