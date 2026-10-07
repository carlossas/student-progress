"""Keeps only valid, actionable AI findings (AGENTS#11). Invalid items are dropped and logged, never posted."""

from __future__ import annotations

import json
import logging

from gate.diff import DiffContext
from gate.report.finding import Finding, FindingError, validate_finding

log = logging.getLogger("gate.ai")
LINE_TOLERANCE = 3


class AIOutputError(RuntimeError):
    """The whole response is unusable (not JSON, wrong shape). A gate error, not an empty review."""


def parse_items(raw: str) -> list:
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        raise AIOutputError(f"Gemini response is not JSON: {e}") from e
    items = data.get("findings") if isinstance(data, dict) else data
    if not isinstance(items, list):
        raise AIOutputError("Gemini response has no `findings` array")
    return items


def validate_ai_output(
    raw: str, ctx: DiffContext, valid_rules: frozenset[str]
) -> tuple[list[Finding], list[tuple[dict, str]]]:
    """Returns (kept findings, [(dropped item, reason)])."""
    files = set(ctx.files())
    kept: list[Finding] = []
    dropped: list[tuple[dict, str]] = []
    for item in parse_items(raw):
        if isinstance(item, dict):
            item = {**item, "source": "ai:gemini"}
            if item.get("line") in (0, None):
                item["line"] = None
        try:
            finding = validate_finding(item, valid_rules)
            if finding.file not in files:
                raise FindingError(f"file {finding.file!r} is not part of the diff")
            if finding.line is not None:
                changed = ctx.lines(finding.file)
                if not any(abs(finding.line - n) <= LINE_TOLERANCE for n in changed):
                    raise FindingError(f"line {finding.line} is outside the changed lines of {finding.file}")
        except FindingError as e:
            dropped.append((item, str(e)))
            log.warning("dropped AI finding: %s — %s", e, json.dumps(item)[:300])
            continue
        kept.append(finding)
    return kept, dropped
