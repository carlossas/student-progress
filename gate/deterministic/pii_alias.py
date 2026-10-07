"""P4: identifiers that look like personal data on changed lines.

Signals only (never posted): they tell the AI where a renamed field might be hiding (B1).
"""

from __future__ import annotations

import ast

from gate.config import is_service_python, pii_fields
from gate.deterministic.pii_registry import tokens
from gate.diff import DiffContext
from gate.report.finding import Signal

ALIAS_TOKENS = {
    "name",
    "names",
    "mail",
    "email",
    "dob",
    "birth",
    "birthday",
    "age",
    "minor",
    "minors",
    "kid",
    "kids",
    "child",
    "children",
    "junior",
    "phone",
    "address",
    "contact",
}


def _identifiers(tree: ast.AST):
    for node in ast.walk(tree):
        if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store):
            yield node.id, node.lineno
        elif isinstance(node, ast.arg):
            yield node.arg, node.lineno
        elif isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            yield node.name, node.lineno
        elif isinstance(node, ast.keyword) and node.arg:
            yield node.arg, node.value.lineno
        elif isinstance(node, ast.Dict):
            for key in node.keys:
                if isinstance(key, ast.Constant) and isinstance(key.value, str):
                    yield key.value, key.lineno


def signals(ctx: DiffContext) -> list[Signal]:
    fields = pii_fields(ctx.read("app/privacy.py"))
    found: dict[tuple[str, int, str], Signal] = {}
    for path in ctx.files():
        if not is_service_python(path):
            continue
        try:
            tree = ast.parse(ctx.read(path) or "")
        except SyntaxError:
            continue
        for name, line in _identifiers(tree):
            if name in fields or not ctx.is_changed(path, line):
                continue
            hits = tokens(name) & ALIAS_TOKENS
            if hits:
                found[(path, line, name)] = Signal(
                    "P4", path, line, f"`{name}` may hold personal data ({', '.join(sorted(hits))})"
                )
    return list(found.values())
