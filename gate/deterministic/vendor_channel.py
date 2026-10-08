"""A18 (AGENTS#2): a module that sets up a third-party channel for personal data.

pii_flow catches personal data reaching an outbound *call*. Scaffolding has no call yet:
golden PR `email-reminders` holds a SendGrid key and a function taking the student's email,
and logs instead of sending. That is the cheapest moment to stop minors' data leaving the
service, so the design is judged: a changed module that names a known vendor (import,
identifier or string) and has a function handling a personal field gets a High, unless the
PR documents a legal basis (`Legal basis:` in the description, TEAM-STANDARDS §3).

Modules that already call the vendor are left to pii_flow, which follows the data itself.
"""

from __future__ import annotations

import ast
import re

from gate.config import is_service_python, pii_fields
from gate.diff import DiffContext
from gate.report.finding import Finding

VENDORS = (
    "sendgrid", "mailchimp", "mailgun", "postmark", "twilio", "segment", "mixpanel", "amplitude",
    "posthog", "braze", "intercom", "zendesk", "freshdesk", "hubspot", "salesforce", "firebase",
)  # fmt: skip
VENDOR = re.compile(rf"(?i)(?<![a-z])({'|'.join(VENDORS)})(?![a-z])")
LEGAL_BASIS = re.compile(r"(?i)legal\s+basis\s*:")


def _vendor(text: str) -> str | None:
    match = VENDOR.search(text)
    return match.group(1).lower() if match else None


def _calls_vendor(tree: ast.AST) -> bool:
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func = node.func
            while isinstance(func, ast.Attribute):
                func = func.value
            if isinstance(func, ast.Name) and _vendor(func.id):
                return True
    return False


def _personal_fields(fn: ast.FunctionDef | ast.AsyncFunctionDef, fields: frozenset[str]) -> list[str]:
    params = {a.arg for a in [*fn.args.posonlyargs, *fn.args.args, *fn.args.kwonlyargs]}
    attrs = {n.attr for n in ast.walk(fn) if isinstance(n, ast.Attribute)}
    return sorted((params | attrs) & fields)


def check(ctx: DiffContext) -> list[Finding]:
    if LEGAL_BASIS.search(ctx.pr_body or ""):
        return []
    fields = pii_fields(ctx.read("app/privacy.py"))
    findings = []
    for path in ctx.files():
        if not is_service_python(path):
            continue
        text = ctx.read(path) or ""
        changed = ctx.lines(path)
        lines = text.splitlines()
        vendor = next((v for n in sorted(changed) if n <= len(lines) and (v := _vendor(lines[n - 1]))), None)
        if vendor is None:
            continue
        try:
            tree = ast.parse(text)
        except SyntaxError:
            continue
        if _calls_vendor(tree):
            continue
        for fn in (n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef | ast.AsyncFunctionDef)):
            personal = _personal_fields(fn, fields)
            if personal and ctx.is_changed(path, fn.lineno, fn.end_lineno):
                findings.append(
                    Finding(
                        rule="AGENTS#2",
                        severity="high",
                        source="deterministic:vendor_channel",
                        check="A18",
                        file=path,
                        line=fn.lineno,
                        message=(
                            f"`{fn.name}` prepares personal data (`{'`, `'.join(personal)}`) for {vendor}, a third "
                            "party. For minors that data can't leave the service without minimization and a "
                            "documented legal basis."
                        ),
                        suggestion=(
                            "Pass `student_id` and resolve the contact inside the service; for minors use the "
                            "guardian's contact with verifiable parental consent (COPPA) or skip them. Then add "
                            "`Legal basis: ...` to the PR description."
                        ),
                    )
                )
    return findings
