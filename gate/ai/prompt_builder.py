"""Builds the Gemini request: trusted instructions (system) + untrusted PR content (user).

AGENTS.md and the check prompts come from the gate's checkout (base branch); the PR can't
edit the instructions it is judged by.

Cost: the system prompt is byte-identical for every PR (no per-PR data in it), so Gemini's
implicit cache can serve it at 10% of the input rate. The user prompt puts the slow-changing
repository context before the PR itself to extend that cacheable prefix. The system prompt
only carries the AGENTS.md rules the AI judges; script-only rules are left out.

Large PRs: files over FULL_FILE_LINES are sent as changed hunks with HUNK_CONTEXT lines
around them, generated files are left out, and the files are packed into batches that fit
the input budget (GEMINI_MAX_INPUT_TOKENS); review.py sends one call per batch.
"""

from __future__ import annotations

import json
import re
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
# Rules Pipeline B judges (plan section 4). Script-only rules (7, 8, 10-19) and rule 9
# (restated as the severity policy in system.md) are not sent.
AI_RULES = frozenset({1, 2, 3, 4, 5, 6, 20, 21})
CONTEXT_FILES = ("app/models.py", "app/privacy.py", "docs/API-AND-BUSINESS-RULES.md")
FULL_FILE_LINES = 300  # small files go whole: the model sees the full function/flow
HUNK_CONTEXT = 30  # big files: changed lines +/- this many lines
NARROW_CONTEXT = 5  # a single file over the budget is retried with less context
# Generated or vendored content: no reviewable intent, only tokens.
AI_EXCLUDED_PREFIXES = ("eval/results/", "node_modules/", ".gate-cache/")
AI_EXCLUDED_NAMES = ("package-lock.json", "poetry.lock", "uv.lock", "coverage.xml", "junit.xml")
CHARS_PER_TOKEN = 3.0  # measured: 164.8k real tokens for ~490k chars of this repo (2026-10-07)
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


def agents_excerpt(text: str, rules: frozenset[int] = AI_RULES) -> str:
    """The personal-data field table plus the numbered rules in `rules`, verbatim from AGENTS.md."""
    lines = text.splitlines()
    out: list[str] = []
    start = next((i for i, ln in enumerate(lines) if ln.startswith("**Personal data fields**")), None)
    if start is not None:
        end = next((i for i in range(start, len(lines)) if re.match(r"^\d+\. ", lines[i])), len(lines))
        out += [ln for ln in lines[start:end] if ln.strip()] + [""]
    current = None
    for line in lines:
        match = re.match(r"^(\d+)\. ", line)
        if match:
            current = int(match.group(1))
        elif line.startswith("#"):
            current = None
        elif not line.startswith("   "):
            continue
        if current in rules:
            out.append(line)
    return "\n".join(out).strip()


def system_prompt() -> str:
    checks = "\n\n".join((PROMPTS / name).read_text(encoding="utf-8").strip() for name in CHECK_PROMPTS)
    template = (PROMPTS / "system.md").read_text(encoding="utf-8")
    agents = agents_excerpt(AGENTS_MD.read_text(encoding="utf-8"))
    return template.replace("{checks}", checks).replace("{agents}", agents)


def _line(n: int, text: str, changed: set[int]) -> str:
    return f"{'+' if n in changed else ' '}{n:5} | {text}"


def numbered(text: str, changed: set[int], context: int = HUNK_CONTEXT) -> str:
    """The whole file when small; otherwise only changed lines +/- `context`, gaps marked."""
    lines = text.splitlines()
    if len(lines) <= FULL_FILE_LINES:
        return "\n".join(_line(n, line, changed) for n, line in enumerate(lines, start=1))
    keep = sorted({k for n in changed for k in range(n - context, n + context + 1) if 1 <= k <= len(lines)})
    out, previous = [], 0
    for n in keep:
        if n != previous + 1:
            out.append(f"        ... lines {previous + 1}-{n - 1} unchanged, not shown")
        out.append(_line(n, lines[n - 1], changed))
        previous = n
    if previous < len(lines):
        out.append(f"        ... lines {previous + 1}-{len(lines)} unchanged, not shown")
    return "\n".join(out)


def estimate_tokens(text: str) -> int:
    return int(len(text) / CHARS_PER_TOKEN) + 1


def reviewable_files(ctx: DiffContext) -> list[str]:
    return [
        p
        for p in ctx.files()
        if p.endswith(REVIEWABLE_SUFFIXES)
        and not is_excluded(p)
        and not p.startswith(AI_EXCLUDED_PREFIXES)
        and Path(p).name not in AI_EXCLUDED_NAMES
    ]


def file_section(ctx: DiffContext, path: str, context: int = HUNK_CONTEXT) -> str:
    return "\n".join([f"### {path}", "```", numbered(ctx.read(path) or "", ctx.lines(path), context), "```", ""])


def _findings_section(findings: list[Finding]) -> str:
    if not findings:
        return "none"
    return "\n".join(f"- {f.severity} {f.rule} ({f.check}) {f.location}: {f.message}" for f in findings)


def _signals_section(signals: list[Signal]) -> str:
    if not signals:
        return "none"
    return "\n".join(f"- {s.kind} {s.file}:{s.line} {s.detail}" for s in signals)


def user_prompt(
    ctx: DiffContext,
    deterministic: list[Finding],
    signals: list[Signal],
    batch: list[str] | None = None,
    narrow: frozenset[str] = frozenset(),
) -> str:
    """The review request for `batch` (default: every reviewable file). `narrow` files use less context."""
    all_files = reviewable_files(ctx)
    files = all_files if batch is None else batch
    if batch is not None:  # only what concerns this batch
        deterministic = [f for f in deterministic if f.file in files]
        signals = [x for x in signals if x.file in files]
    # Slow-changing repository context first: identical across most PRs, so it extends the
    # prefix Gemini can serve from cache. It still comes from the PR checkout: untrusted.
    parts = ["<repository_context>", "Read-only context, not under review.", ""]
    for path in CONTEXT_FILES:
        text = ctx.read(path)
        if text is not None and path not in all_files:
            parts += [f"### {path}", "```", text.strip(), "```", ""]
    parts += [
        "</repository_context>",
        "",
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
        "## Changed files (`+` marks changed lines; only those can be reported)",
        "",
    ]
    if batch is not None and len(batch) < len(all_files):
        others = [p for p in all_files if p not in batch]
        parts += [
            f"Large PR: this request covers {len(batch)} of {len(all_files)} files. Also changed (reviewed "
            f"separately, do not report on them): {', '.join(others)}",
            "",
        ]
    for path in files:
        parts.append(file_section(ctx, path, NARROW_CONTEXT if path in narrow else HUNK_CONTEXT))
    parts += ["</pull_request>", "", f"Return JSON: {json.dumps({'findings': ['...']})}"]
    return "\n".join(parts)


def plan_batches(
    ctx: DiffContext, deterministic: list[Finding], signals: list[Signal], budget: int
) -> list[tuple[list[str], frozenset[str]]]:
    """Packs the reviewable files into requests of at most ~`budget` input tokens.

    Files keep their order, so related files (same directory) tend to share a request. A file
    that alone exceeds the budget is sent with narrow context, in a request of its own.
    """
    files = reviewable_files(ctx)
    fixed = estimate_tokens(system_prompt()) + estimate_tokens(user_prompt(ctx, deterministic, signals, batch=[]))
    room = max(budget - fixed, 1)
    batches: list[tuple[list[str], frozenset[str]]] = []
    current: list[str] = []
    used = 0
    for path in files:
        size = estimate_tokens(file_section(ctx, path))
        if size > room:
            if current:
                batches.append((current, frozenset()))
                current, used = [], 0
            batches.append(([path], frozenset({path})))
            continue
        if current and used + size > room:
            batches.append((current, frozenset()))
            current, used = [], 0
        current.append(path)
        used += size
    if current or not batches:
        batches.append((current, frozenset()))
    return batches
