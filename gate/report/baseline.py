"""Pre-existing debt: a High code-quality finding on a line that only moved is a comment, not a block.

A diff re-adds a line when the code around it changes: `score=int(payload.get("score", 0)),`
inside a constructor becomes `score = int(payload.get("score", 0))` two lines up. Whatever is
wrong with that line was already on the base branch, so blocking the PR makes its author pay
for debt they didn't write, and it punishes exactly the PRs that improve old code.

Only judgment rules about code quality are demoted (input handling, simplicity, logic).
Privacy, retention, minimization, secrets and tests never are: a moved secret or a moved
log of a minor's email is still a leak.
"""

from __future__ import annotations

import re
from dataclasses import replace

from gate.diff import DiffContext, git
from gate.report.finding import Finding

DEMOTABLE_RULES = {"AGENTS#5", "AGENTS#7", "AGENTS#9"}
MIN_CHARS = 12  # shorter lines (`return x`, `else:`) match anything and prove nothing
NOTE = (
    " Pre-existing: this line already exists on the base branch and the PR only moves it, "
    "so it doesn't block. Fix it here if it's cheap, otherwise open a ticket."
)


def _norm(line: str) -> str:
    return re.sub(r"\s+", "", line).rstrip(",")


def _base_lines(ctx: DiffContext, path: str, cache: dict[str, list[str] | None]) -> list[str] | None:
    if path not in cache:
        try:
            merge_base = git(ctx.repo, "merge-base", ctx.base, ctx.head).strip()
            cache[path] = [_norm(line) for line in git(ctx.repo, "show", f"{merge_base}:{path}").splitlines()]
        except RuntimeError:  # new file, or base not reachable: nothing can be pre-existing
            cache[path] = None
    return cache[path]


def _existed(ctx: DiffContext, f: Finding, cache: dict[str, list[str] | None]) -> bool:
    lines = (ctx.read(f.file) or "").splitlines()
    if not f.line or f.line > len(lines):
        return False
    new = _norm(lines[f.line - 1])
    if len(new) < MIN_CHARS:
        return False
    base = _base_lines(ctx, f.file, cache)
    return bool(base) and any(new in old for old in base)


def demote_preexisting(findings: list[Finding], ctx: DiffContext) -> list[Finding]:
    """High -> Medium for demotable rules on moved lines. Only in refs mode (CI, eval, `gate check`)."""
    if ctx.mode != "refs" or not ctx.base:
        return findings
    cache: dict[str, list[str] | None] = {}
    return [
        replace(f, severity="medium", message=f.message + NOTE)
        if f.severity == "high" and f.rule in DEMOTABLE_RULES and _existed(ctx, f, cache)
        else f
        for f in findings
    ]
