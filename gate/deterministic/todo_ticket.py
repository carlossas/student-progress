"""A12 (AGENTS#7): every TODO/FIXME comment references a ticket (e.g. `TODO(OE-123)`)."""

from __future__ import annotations

import io
import re
import tokenize

from gate.diff import DiffContext
from gate.report.finding import Finding

MARKER = re.compile(r"\b(TODO|FIXME|XXX|HACK)\b")
TICKET = re.compile(r"\b[A-Z][A-Z0-9]+-\d+\b")
HASH_COMMENT_FILES = (".sh", ".yml", ".yaml", ".toml", ".cfg", ".ini")
SLASH_COMMENT_FILES = (".js", ".ts", ".mjs", ".cjs")


def _comments(path: str, text: str):
    """(line, comment text) pairs; string literals are not comments."""
    if path.endswith(".py"):
        try:
            for tok in tokenize.generate_tokens(io.StringIO(text).readline):
                if tok.type == tokenize.COMMENT:
                    yield tok.start[0], tok.string
        except (tokenize.TokenError, SyntaxError):
            return
        return
    marker = "#" if path.endswith(HASH_COMMENT_FILES) else "//" if path.endswith(SLASH_COMMENT_FILES) else None
    if marker is None:
        return
    for number, line in enumerate(text.splitlines(), start=1):
        if marker in line:
            yield number, line[line.index(marker) :]


def check(ctx: DiffContext) -> list[Finding]:
    findings = []
    for path in ctx.files():
        for line, comment in _comments(path, ctx.read(path) or ""):
            match = MARKER.search(comment)
            if match and not TICKET.search(comment) and ctx.is_changed(path, line):
                findings.append(
                    Finding(
                        rule="AGENTS#7",
                        severity="medium",
                        source="deterministic:todo",
                        check="A12",
                        file=path,
                        line=line,
                        message=f"`{match.group(1)}` without a ticket reference: `{comment.strip()[:80]}`",
                        suggestion=f"Create a ticket and reference it, e.g. `# {match.group(1)}(OE-123): ...`, or do it now.",
                    )
                )
    return findings
