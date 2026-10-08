"""A7 (AGENTS#5): route handlers take validated models, not raw dicts.

A raw `dict` body skips FastAPI validation, so bad input becomes a 500 instead of a 422.
(A6, broad/silent `except`, is ruff's job: see lint.py.)
"""

from __future__ import annotations

import ast

from gate.config import is_service_python
from gate.deterministic.pii_flow import _is_route
from gate.diff import DiffContext
from gate.report.finding import Finding

UNVALIDATED = {"dict", "Dict", "Any", "object", "Mapping", "MutableMapping"}


def _unvalidated(annotation: ast.expr | None) -> bool:
    if annotation is None:
        return False
    base = annotation.value if isinstance(annotation, ast.Subscript) else annotation
    name = base.attr if isinstance(base, ast.Attribute) else getattr(base, "id", "")
    return name in UNVALIDATED


def check(ctx: DiffContext) -> list[Finding]:
    findings = []
    for path in ctx.files():
        if not is_service_python(path):
            continue
        try:
            tree = ast.parse(ctx.read(path) or "")
        except SyntaxError:
            continue
        for func in ast.walk(tree):
            if not isinstance(func, ast.FunctionDef | ast.AsyncFunctionDef) or not _is_route(func):
                continue
            for arg in [*func.args.args, *func.args.kwonlyargs]:
                if _unvalidated(arg.annotation) and ctx.is_changed(path, arg.lineno):
                    model = "".join(p.capitalize() for p in func.name.split("_")) + "In"
                    findings.append(
                        Finding(
                            rule="AGENTS#5",
                            severity="high",
                            source="deterministic:validation",
                            check="A7",
                            file=path,
                            line=arg.lineno,
                            message=f"`{func.name}` takes `{arg.arg}: {ast.unparse(arg.annotation)}`: the body is not validated, so bad input fails with a 500.",
                            suggestion=(
                                f"Declare a Pydantic model and use it as the type:\n\n```python\nclass {model}(BaseModel):\n"
                                f"    lesson_id: str\n    score: int = Field(0, ge=0, le=100)\n\n"
                                f"def {func.name}(..., {arg.arg}: {model}):\n```"
                            ),
                        )
                    )
    return findings
