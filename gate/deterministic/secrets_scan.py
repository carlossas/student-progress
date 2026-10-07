"""A1 (AGENTS#8): secrets in the diff and in every commit of the PR.

Pattern-based, like gitleaks, but dependency-free so the same code runs in CI and in the
pre-commit hook. A secret removed in a later commit is still reported: it lives in history,
so it must be rotated.
"""

from __future__ import annotations

import re
from pathlib import PurePosixPath

from gate.config import SECRET_ALLOWLIST
from gate.diff import DiffContext
from gate.report.finding import Finding

PATTERNS = [
    ("Google API key", re.compile(r"AIza[0-9A-Za-z_\-]{35}")),
    ("SendGrid API key", re.compile(r"SG\.[A-Za-z0-9_\-]{16,32}\.[A-Za-z0-9_\-]{30,50}")),
    ("AWS access key", re.compile(r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b")),
    ("GitHub token", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{36,}\b")),
    ("Slack token", re.compile(r"\bxox[abprs]-[A-Za-z0-9-]{10,}")),
    ("Stripe key", re.compile(r"\b[sr]k_live_[A-Za-z0-9]{20,}")),
    ("Private key", re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----")),
    (
        "Hardcoded credential",
        re.compile(r"""(?i)\b\w*(?:api[_-]?key|secret|token|passw(?:or)?d)\w*\s*[:=]\s*["']([^"'\s]{12,})["']"""),
    ),
]
SECRET_FILES = re.compile(r"(^|/)(\.env(\.[\w-]+)?|id_rsa|id_ed25519|.+\.pem|.+\.p12|credentials\.json)$")
SAFE_ENV_FILES = (".env.example", ".env.sample", ".env.template")


def _allowlist() -> set[str]:
    lines = SECRET_ALLOWLIST.read_text(encoding="utf-8").splitlines() if SECRET_ALLOWLIST.exists() else []
    return {ln.strip() for ln in lines if ln.strip() and not ln.startswith("#")}


def _mask(value: str) -> str:
    return value[:4] + "…" if len(value) > 4 else "…"


def scan_text(text: str) -> tuple[str, str] | None:
    """(kind, masked value) of the first secret in `text`, or None."""
    for kind, pattern in PATTERNS:
        match = pattern.search(text)
        if match:
            value = match.group(1) if match.groups() else match.group(0)
            if kind == "Hardcoded credential" and re.search(
                r"environ|getenv|\{\{|\$\{|<.*>|example|changeme", text, re.I
            ):
                continue
            return kind, _mask(value)
    return None


def _variable(line: str) -> str:
    match = re.match(r"\s*([A-Za-z_][A-Za-z0-9_]*)\s*[:=]", line)
    return match.group(1) if match else "THE_SECRET"


def _finding(file: str, line: int | None, message: str, variable: str) -> Finding:
    return Finding(
        rule="AGENTS#8",
        severity="critical",
        source="deterministic:secrets",
        check="A1",
        file=file,
        line=line,
        message=message,
        suggestion=(
            "Treat it as leaked: rotate it now (it is in git history), remove it, and read it from the environment: "
            f'`{variable} = os.environ["{variable}"]` with the value stored as a GitHub/CI secret.'
        ),
    )


def check(ctx: DiffContext) -> list[Finding]:
    allow = _allowlist()
    findings: list[Finding] = []
    reported: set[tuple[str, str]] = set()
    for path in ctx.files():
        if path in allow:
            continue
        name = PurePosixPath(path).name
        if SECRET_FILES.search(path) and name not in SAFE_ENV_FILES:
            findings.append(
                _finding(path, None, f"`{name}` is a secrets file and must never be committed.", "THE_SECRET")
            )
            continue
        text = ctx.read(path) or ""
        for number, line in enumerate(text.splitlines(), start=1):
            if number not in ctx.lines(path):
                continue
            hit = scan_text(line)
            if hit:
                kind, masked = hit
                reported.add((path, masked))
                findings.append(
                    _finding(path, number, f"{kind} committed in plain text (`{masked}`).", _variable(line))
                )
    for commit, path, line in ctx.history_added_lines():
        if path in allow:
            continue
        hit = scan_text(line)
        if hit and (path, hit[1]) not in reported:
            reported.add((path, hit[1]))
            findings.append(
                _finding(
                    path,
                    None,
                    f"{hit[0]} (`{hit[1]}`) was committed in {commit[:8]} and is still in git history.",
                    _variable(line),
                )
            )
    return findings
