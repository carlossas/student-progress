"""Severity → PR action (AGENTS#9, plan section 2). Pure policy: no I/O.

| Severity | Job          | quality-gate/critical | quality-gate/high | Review          | Comment              |
|----------|--------------|-----------------------|-------------------|-----------------|----------------------|
| Critical | exit 1 + log | failure               | -                 | REQUEST_CHANGES | inline + suggestion  |
| High     | exit 0       | -                     | failure           | REQUEST_CHANGES | inline               |
| Medium   | exit 0       | -                     | -                 | COMMENT         | inline               |
| Low      | exit 0       | -                     | -                 | COMMENT         | grouped in summary   |

The two commit statuses are the required checks on protected branches; a production
override flips them to success (see override.py). In shadow mode nothing blocks.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

from gate.config import STATUS_CRITICAL, STATUS_HIGH
from gate.report.finding import Finding, sort_findings

MODES = ("enforce", "shadow")


@dataclass
class Decision:
    exit_code: int
    statuses: dict[str, tuple[str, str]]  # context -> (state, description)
    review_event: str | None  # REQUEST_CHANGES | COMMENT | None
    inline: list[Finding] = field(default_factory=list)
    summary_only: list[Finding] = field(default_factory=list)
    gate_errors: list[str] = field(default_factory=list)


def _count(findings: list[Finding], severity: str) -> int:
    return sum(1 for f in findings if f.severity == severity)


def decide(
    findings: list[Finding],
    mode: str = "enforce",
    gate_errors: list[str] | tuple[str, ...] = (),
    commentable: Callable[[Finding], bool] | None = None,
) -> Decision:
    if mode not in MODES:
        raise ValueError(f"GATE_MODE must be one of {MODES}, got {mode!r}")
    commentable = commentable or (lambda f: f.line is not None)
    findings = sort_findings(findings)
    criticals, highs = _count(findings, "critical"), _count(findings, "high")
    enforce = mode == "enforce"
    prefix = "" if enforce else "[shadow] "

    if gate_errors:
        critical_status = ("failure" if enforce else "success", f"{prefix}Gate error: {gate_errors[0]}"[:140])
    elif criticals:
        critical_status = ("failure" if enforce else "success", f"{prefix}{criticals} critical finding(s)")
    else:
        critical_status = ("success", "No critical findings")
    high_status = (
        ("failure" if enforce else "success", f"{prefix}{highs} high finding(s)")
        if highs
        else ("success", "No high findings")
    )

    if criticals or highs:
        event = "REQUEST_CHANGES" if enforce else "COMMENT"
    elif findings:
        event = "COMMENT"
    else:
        event = None

    inline = [f for f in findings if f.severity != "low" and commentable(f)]
    return Decision(
        exit_code=1 if enforce and (criticals or gate_errors) else 0,
        statuses={STATUS_CRITICAL: critical_status, STATUS_HIGH: high_status},
        review_event=event,
        inline=inline,
        summary_only=[f for f in findings if f not in inline],
        gate_errors=list(gate_errors),
    )


SEVERITY_ICON = {"critical": "🛑", "high": "⛔", "medium": "⚠️", "low": "💡"}


def comment_body(f: Finding) -> str:
    return (
        f"{SEVERITY_ICON[f.severity]} **{f.severity.upper()}** · `{f.rule}` · {f.check or f.source}\n\n"
        f"{f.message}\n\n**Suggested fix:**\n\n{f.suggestion}\n\n"
        f"<sub>{f.source}</sub>\n<!-- qg:{f.fingerprint()} -->"
    )


def render_summary(findings: list[Finding], decision: Decision, mode: str, extra: list[str] | None = None) -> str:
    """Markdown for the job summary and the sticky PR comment."""
    findings = sort_findings(findings)
    lines = ["## Quality gate", ""]
    if decision.gate_errors:
        lines += ["**Gate errors** (treated as blocking):", *[f"- {e}" for e in decision.gate_errors], ""]
    state = "blocked" if decision.exit_code or any(s == "failure" for s, _ in decision.statuses.values()) else "passing"
    counts = ", ".join(f"{_count(findings, s)} {s}" for s in ("critical", "high", "medium", "low"))
    lines += [f"Mode: `{mode}` · Result: **{state}** · {counts}", ""]
    if findings:
        lines += ["| Severity | Rule | Location | Finding | Source |", "|---|---|---|---|---|"]
        for f in findings:
            message = f.message.replace("|", "\\|").replace("\n", " ")
            lines.append(
                f"| {SEVERITY_ICON[f.severity]} {f.severity} | `{f.rule}` | `{f.location}` | {message} | {f.source} |"
            )
        lines.append("")
    else:
        lines += ["No findings. ✅", ""]
    if decision.summary_only:
        lines += ["<details><summary>Suggestions for findings without an inline comment</summary>", ""]
        for f in decision.summary_only:
            lines += [f"**`{f.location}`** ({f.severity}, `{f.rule}`): {f.suggestion}", ""]
        lines += ["</details>", ""]
    lines += extra or []
    return "\n".join(lines)
