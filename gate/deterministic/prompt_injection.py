"""A17 (AGENTS#15): text in the PR that tries to steer the AI reviewer.

The system prompt already tells Gemini to treat PR content as data. This is the second
layer: an attempt to talk the reviewer out of a finding is a reason for a human to look,
whether or not the model fell for it. Pattern-based on purpose (AGENTS#10): it must not
depend on the model it protects.
"""

from __future__ import annotations

import re

from gate.diff import DiffContext
from gate.report.finding import Finding

PATTERNS = re.compile(
    r"(?i)("
    r"ignore\s+(all\s+|any\s+)?(the\s+)?(previous|prior|above|earlier)\s+(instructions|rules|prompts?)"
    r"|disregard\s+(the\s+)?(rules|instructions|system\s+prompt)"
    r"|(note|message|instructions?)\s+(to|for)\s+(the\s+)?(ai|llm|gemini|claude|reviewer|review\s+bot)"
    r"|(report|return)\s+(no|zero|an?\s+empty\s+list\s+of)\s+findings"
    r"|\{\s*\"findings\"\s*:\s*\[\s*\]\s*\}"
    r"|(already|pre-?)\s*approved\s+by\s+(legal|security|privacy|the\s+gate)"
    r")"
)
# The gate's own prompts and tests talk about injection; they're reviewed as gate code.
OWN_PREFIXES = ("gate/", "tests/gate/")


def _finding(file: str, line: int | None, snippet: str) -> Finding:
    return Finding(
        rule="AGENTS#15",
        severity="high",
        source="deterministic:prompt_injection",
        check="A17",
        file=file,
        line=line,
        message=f"Text aimed at the AI reviewer (`{snippet[:60]}`). Findings can't be negotiated from inside a PR.",
        suggestion="Remove it. If a finding is wrong, say why in the PR and ask a production approver for `/gate-override <reason>`.",
    )


def check(ctx: DiffContext) -> list[Finding]:
    findings = []
    for field_name, text in (("PR title", ctx.pr_title), ("PR description", ctx.pr_body)):
        match = PATTERNS.search(text or "")
        if match:
            findings.append(_finding(f"({field_name})", None, match.group(0)))
    for path in ctx.files():
        if path.startswith(OWN_PREFIXES):
            continue
        changed = ctx.lines(path)
        for number, line in enumerate((ctx.read(path) or "").splitlines(), start=1):
            match = PATTERNS.search(line) if number in changed else None
            if match:
                findings.append(_finding(path, number, match.group(0)))
    return findings
