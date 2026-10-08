"""P1 (AGENTS#1): every personal-looking model field is registered in `PII_FIELDS`.

`redact()` and the gate only protect what `PII_FIELDS` lists, so a new `phone` field that
nobody registered would leak silently. Reported when the model or the registry changes.
"""

from __future__ import annotations

import ast
import re

from gate.config import literal_assignment, module_assignment
from gate.diff import DiffContext
from gate.report.finding import Finding

MODELS, PRIVACY = "app/models.py", "app/privacy.py"
PERSONAL_TOKENS = {
    "name",
    "mail",
    "email",
    "birth",
    "birthdate",
    "birthday",
    "dob",
    "age",
    "phone",
    "mobile",
    "address",
    "minor",
    "document",
    "passport",
    "ssn",
    "nationalid",
    "contact",
}


def tokens(identifier: str) -> set[str]:
    spaced = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", identifier).lower()
    return {t for t in spaced.split("_") if t}


def looks_personal(field: str) -> bool:
    return bool(tokens(field) & PERSONAL_TOKENS)


def dataclass_fields(source: str) -> list[tuple[str, str, int]]:
    """(class, field, line) for every annotated field of a @dataclass."""
    fields = []
    for node in ast.walk(ast.parse(source)):
        if not isinstance(node, ast.ClassDef):
            continue
        decorators = {ast.unparse(d).split("(")[0].split(".")[-1] for d in node.decorator_list}
        if "dataclass" not in decorators:
            continue
        for stmt in node.body:
            if isinstance(stmt, ast.AnnAssign) and isinstance(stmt.target, ast.Name):
                fields.append((node.name, stmt.target.id, stmt.lineno))
    return fields


def check(ctx: DiffContext) -> list[Finding]:
    models, privacy = ctx.read(MODELS), ctx.read(PRIVACY)
    if models is None:
        return []
    registered = set(literal_assignment(privacy, "PII_FIELDS") or ()) if privacy else set()
    registry = module_assignment(privacy, "PII_FIELDS") if privacy else None
    registry_changed = registry is not None and ctx.is_changed(PRIVACY, registry[1], registry[2])
    try:
        fields = dataclass_fields(models)
    except SyntaxError:
        return []
    return [
        Finding(
            rule="AGENTS#1",
            severity="critical",
            source="deterministic:pii_registry",
            check="P1",
            file=MODELS,
            line=line,
            message=f"`{cls}.{field}` looks like personal data but is not in `PII_FIELDS`, so `redact()` will not mask it.",
            suggestion=f'Add "{field}" to `PII_FIELDS` in app/privacy.py and to the Personal data fields table in AGENTS.md.',
        )
        for cls, field, line in fields
        if looks_personal(field) and field not in registered and (registry_changed or ctx.is_changed(MODELS, line))
    ]
