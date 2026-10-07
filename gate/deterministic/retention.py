"""A3/A4 (AGENTS#3): every dataset has a retention period; minors' data at most 90 days.

A3 (critical) always checks `RETENTION_DAYS`: a retention violation anywhere blocks.
A4 (high) flags a new accumulating dataset (empty module-level collection, file or DB
write) in service code when the same change does not touch `RETENTION_DAYS`.
"""

from __future__ import annotations

import ast

from gate.config import MINOR_RETENTION_MAX_DAYS, is_service_python, is_source, module_assignment
from gate.deterministic.pii_flow import _name, is_collection_literal
from gate.diff import DiffContext
from gate.report.finding import Finding

PRIVACY = "app/privacy.py"
DB_OPENERS = {"connect", "open_database", "shelve.open"}


def check_minor_limits(ctx: DiffContext) -> list[Finding]:
    source = ctx.read(PRIVACY)
    found = module_assignment(source, "RETENTION_DAYS") if source else None
    if found is None or not isinstance(found[0], ast.Dict):
        return []
    findings = []
    for key, value in zip(found[0].keys, found[0].values, strict=True):
        if not (isinstance(key, ast.Constant) and isinstance(value, ast.Constant)):
            continue
        if (
            "minor" in str(key.value)
            and isinstance(value.value, int | float)
            and value.value > MINOR_RETENTION_MAX_DAYS
        ):
            findings.append(
                Finding(
                    rule="AGENTS#3",
                    severity="critical",
                    source="deterministic:retention",
                    check="A3",
                    file=PRIVACY,
                    line=key.lineno,
                    message=f"`{key.value}` keeps minors' data for {value.value} days; the maximum is {MINOR_RETENTION_MAX_DAYS}.",
                    suggestion=f'"{key.value}": {MINOR_RETENTION_MAX_DAYS},  # or document the legal basis in the PR',
                )
            )
    return findings


def _new_datasets(tree: ast.Module) -> list[tuple[int, str]]:
    datasets = []
    for node in tree.body:
        if isinstance(node, ast.Assign | ast.AnnAssign) and is_collection_literal(node.value):
            value = node.value
            empty = (
                (isinstance(value, ast.List | ast.Set) and not value.elts)
                or (isinstance(value, ast.Dict) and not value.keys)
                or (isinstance(value, ast.Call) and (not value.args or _name(value.func).endswith("defaultdict")))
            )
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            if empty:
                datasets += [
                    (node.lineno, f"module-level collection `{t.id}`") for t in targets if isinstance(t, ast.Name)
                ]
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            name = _name(node.func)
            if name.endswith(tuple(DB_OPENERS)):
                datasets.append((node.lineno, f"database `{name}()`"))
            elif name.split(".")[-1] == "open" and any(
                isinstance(a, ast.Constant) and str(a.value)[:1] in "wax" for a in node.args[1:2]
            ):
                datasets.append((node.lineno, "file written by `open()`"))
    return datasets


def check_new_datasets(ctx: DiffContext) -> list[Finding]:
    source = ctx.read(PRIVACY)
    registry = module_assignment(source, "RETENTION_DAYS") if source else None
    if registry is not None and ctx.is_changed(PRIVACY, registry[1], registry[2]):
        return []
    findings = []
    for path in ctx.files():
        if path == PRIVACY or not (is_source(path) and is_service_python(path)):
            continue
        try:
            tree = ast.parse(ctx.read(path) or "")
        except SyntaxError:
            continue
        for line, what in _new_datasets(tree):
            if ctx.is_changed(path, line):
                findings.append(
                    Finding(
                        rule="AGENTS#3",
                        severity="high",
                        source="deterministic:retention",
                        check="A4",
                        file=path,
                        line=line,
                        message=f"New dataset ({what}) without a retention category in `RETENTION_DAYS`.",
                        suggestion='Declare it in app/privacy.py, e.g. `"archive": 365, "archive_minor": 90`, and document its purpose.',
                    )
                )
    return findings


def check(ctx: DiffContext) -> list[Finding]:
    return check_minor_limits(ctx) + check_new_datasets(ctx)
