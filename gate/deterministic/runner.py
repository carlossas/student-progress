"""Runs Pipeline A. A check that crashes is a gate error (blocking), never a silent pass."""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from gate.deterministic import (
    change_policy,
    lint,
    pii_alias,
    pii_flow,
    pii_registry,
    prompt_injection,
    retention,
    secrets_scan,
    tests_runner,
    todo_ticket,
    validation,
    workflow_policy,
)
from gate.diff import DiffContext
from gate.report.baseline import demote_preexisting
from gate.report.finding import Finding, Signal
from gate.report.merge import dedupe

log = logging.getLogger("gate.deterministic")

# Fast checks: also run by the pre-commit hook (target < 10 s).
FAST: dict[str, Callable[[DiffContext], list[Finding]]] = {
    "secrets": secrets_scan.check,
    "pii_registry": pii_registry.check,
    "pii_flow": pii_flow.check,
    "retention": retention.check,
    "validation": validation.check,
    "lint": lint.check,
    "todo": todo_ticket.check,
    "prompt_injection": prompt_injection.check,
}
POLICY: dict[str, Callable[[DiffContext], list[Finding]]] = {
    "tests_touched": change_policy.tests_touched,
    "docs_touched": change_policy.docs_touched,
    "records": change_policy.records,
    "workflow_policy": workflow_policy.check,
}


@dataclass
class Result:
    findings: list[Finding] = field(default_factory=list)
    signals: list[Signal] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


def _guarded(result: Result, name: str, fn: Callable[[], list]) -> list:
    try:
        return fn()
    except Exception as e:  # noqa: BLE001 - recorded as a blocking gate error, not swallowed
        log.exception("check %s crashed", name)
        result.errors.append(f"{name}: {e}")
        return []


def run(ctx: DiffContext, *, fast_only: bool = False, with_tests: bool = True, out_dir: Path | None = None) -> Result:
    result = Result()
    checks = FAST if fast_only else {**FAST, **POLICY}
    for name, fn in checks.items():
        result.findings += _guarded(result, name, lambda fn=fn: fn(ctx))
    if with_tests:
        result.findings += _guarded(result, "tests", lambda: tests_runner.run(ctx, out_dir))
    if not fast_only:
        result.signals += _guarded(result, "pii_alias", lambda: pii_alias.signals(ctx))
        result.signals += _guarded(result, "outbound", lambda: pii_flow.outbound_signals(ctx))
    result.findings = demote_preexisting(dedupe(result.findings), ctx)
    return result
