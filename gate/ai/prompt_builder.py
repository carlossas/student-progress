"""Builds the Gemini request: trusted instructions (system) + untrusted PR content (user).

AGENTS.md and the check prompts come from the gate's checkout (base branch); the PR can't
edit the instructions it is judged by.
"""

from __future__ import annotations

import json
from pathlib import Path

from gate.config import AGENTS_MD, is_excluded
from gate.diff import DiffContext
from gate.report.finding import Finding, Signal

PROMPTS = Path(__file__).with_name("prompts")
CHECK_PROMPTS = (
    "r01_pii.md",
    "r02_outbound.md",
    "r03_copies.md",
    "r04_minimization.md",
    "r05_validation.md",
    "r06_test_quality.md",
    "r09_logic_style.md",
    "r20_docs.md",
    "r21_single_source.md",
)
CONTEXT_FILES = ("app/models.py", "app/privacy.py", "docs/API-AND-BUSINESS-RULES.md")
MAX_LINES_PER_FILE = 600
REVIEWABLE_SUFFIXES = (".py", ".md", ".yml", ".yaml", ".toml", ".txt", ".json", ".cfg", ".ini", ".sh", ".env")


def response_schema() -> dict:
    """Gemini structured output: the finding schema minus `source` (the gate sets it)."""
    finding = {
        "type": "object",
        "properties": {
            "rule": {"type": "string", "description": "AGENTS#<n>"},
            "severity": {"type": "string", "enum": ["critical", "high", "medium", "low"]},
            "check": {"type": "string"},
            "file": {"type": "string"},
            "line": {"type": "integer"},
            "message": {"type": "string"},
            "suggestion": {"type": "string"},
        },
        "required": ["rule", "severity", "check", "file", "message", "suggestion"],
    }
    return {"type": "object", "properties": {"findings": {"type": "array", "items": finding}}, "required": ["findings"]}


def system_prompt() -> str:
    checks = "\n\n".join((PROMPTS / name).read_text(encoding="utf-8").strip() for name in CHECK_PROMPTS)
    template = (PROMPTS / "system.md").read_text(encoding="utf-8")
    return template.replace("{checks}", checks).replace("{agents}", AGENTS_MD.read_text(encoding="utf-8"))


def numbered(text: str, changed: set[int]) -> str:
    lines = text.splitlines()
    out = [
        f"{'+' if n in changed else ' '}{n:5} | {line}" for n, line in enumerate(lines[:MAX_LINES_PER_FILE], start=1)
    ]
    if len(lines) > MAX_LINES_PER_FILE:
        out.append(f"   ... {len(lines) - MAX_LINES_PER_FILE} more lines not shown")
    return "\n".join(out)


def _findings_section(findings: list[Finding]) -> str:
    if not findings:
        return "none"
    return "\n".join(f"- {f.severity} {f.rule} ({f.check}) {f.location}: {f.message}" for f in findings)


def _signals_section(signals: list[Signal]) -> str:
    if not signals:
        return "none"
    return "\n".join(f"- {s.kind} {s.file}:{s.line} {s.detail}" for s in signals)


def user_prompt(ctx: DiffContext, deterministic: list[Finding], signals: list[Signal]) -> str:
    files = [p for p in ctx.files() if p.endswith(REVIEWABLE_SUFFIXES) and not is_excluded(p)]
    parts = [
        "<pull_request>",
        f"Title: {ctx.pr_title or '(none)'}",
        "Description:",
        ctx.pr_body or "(none)",
        "",
        "## Already reported by deterministic checks (do not repeat)",
        _findings_section(deterministic),
        "",
        "## Hints from scripts (verify; may be false alarms)",
        _signals_section(signals),
        "",
        "## Context (read-only, not under review)",
    ]
    for path in CONTEXT_FILES:
        text = ctx.read(path)
        if text is not None and path not in files:
            parts += [f"### {path}", "```", text.strip(), "```", ""]
    parts += ["## Changed files (`+` marks changed lines; only those can be reported)", ""]
    for path in files:
        parts += [f"### {path}", "```", numbered(ctx.read(path) or "", ctx.lines(path)), "```", ""]
    parts += ["</pull_request>", "", f"Return JSON: {json.dumps({'findings': ['...']})}"]
    return "\n".join(parts)
