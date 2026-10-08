"""Diff-shape policies: A9 tests touched (AGENTS#6), A14 docs touched (AGENTS#20), A16 records (AGENTS#18).

No skip labels: refactors count too (AGENTS#15).
"""

from __future__ import annotations

import re

from gate.config import DOC_FILES, RECORD_FILES, TEST_DIR, is_source
from gate.diff import DiffContext
from gate.report.finding import Finding


def _source_files(ctx: DiffContext) -> list[str]:
    return [p for p in ctx.files() if is_source(p)]


def tests_touched(ctx: DiffContext) -> list[Finding]:
    sources = _source_files(ctx)
    if not sources or any(p.startswith(f"{TEST_DIR}/") for p in ctx.files()):
        return []
    return [
        Finding(
            rule="AGENTS#6",
            severity="high",
            source="deterministic:change_policy",
            check="A9",
            file=sources[0],
            message=f"Service code changed ({', '.join(sources)}) but no test under `{TEST_DIR}/` was added or updated (this also covers the changed-line coverage gap).",
            suggestion="Add tests that fail if this behavior breaks, including edge cases (refactors too: prove nothing changed).",
        )
    ]


def docs_touched(ctx: DiffContext) -> list[Finding]:
    sources = _source_files(ctx)
    if not sources:
        return []
    missing = [d for d in DOC_FILES if d not in ctx.changed]
    if not missing:
        return []
    return [
        Finding(
            rule="AGENTS#20",
            severity="medium",  # process rule: comment, never a block (DECISIONS ADR-3)
            source="deterministic:change_policy",
            check="A14",
            file=sources[0],
            message=f"Service code changed but {', '.join(f'`{d}`' for d in missing)} {'was' if len(missing) == 1 else 'were'} not updated.",
            suggestion="Update the docs in the same PR: modules/diagrams/flows in ARCHITECTURE.md; endpoints, business rules and known gaps in API-AND-BUSINESS-RULES.md.",
        )
    ]


def records(ctx: DiffContext) -> list[Finding]:
    """Repo-level: DECISIONS.md and AI-USAGE.md exist and have content beyond a title."""
    if ctx.mode == "staged":
        return []
    findings = []
    for name in RECORD_FILES:
        text = ctx.read(name)
        problem = None
        if text is None:
            problem = f"`{name}` is missing."
        elif len(re.findall(r"^#{1,6} ", text, flags=re.M)) < 2:
            problem = f"`{name}` has no content sections."
        if problem:
            findings.append(
                Finding(
                    rule="AGENTS#18",
                    severity="low",
                    source="deterministic:change_policy",
                    check="A16",
                    file=name,
                    message=problem,
                    suggestion=f"Record it in `{name}`: decisions and trade-offs in DECISIONS.md, AI tools/prompts/corrections in AI-USAGE.md.",
                )
            )
    return findings
