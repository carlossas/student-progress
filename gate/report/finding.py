"""The finding contract (AGENTS#11), shared by both pipelines. See schema.json."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path

from gate.config import SEVERITIES

SCHEMA_PATH = Path(__file__).with_name("schema.json")
RULE_PATTERN = re.compile(r"^AGENTS#\d+$")
SEVERITY_RANK = {s: i for i, s in enumerate(SEVERITIES)}  # critical = 0


class FindingError(ValueError):
    """A finding that does not satisfy the schema. Never posted."""


@dataclass(frozen=True)
class Finding:
    rule: str
    severity: str
    source: str
    file: str
    message: str
    suggestion: str
    line: int | None = None
    check: str = ""

    @property
    def location(self) -> str:
        return f"{self.file}:{self.line}" if self.line else self.file

    def fingerprint(self) -> str:
        """Stable id across runs, used to avoid re-posting the same inline comment."""
        raw = f"{self.rule}|{self.check}|{self.file}|{self.line}|{self.message}"
        return hashlib.sha1(raw.encode()).hexdigest()[:12]

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class Signal:
    """A hint for the AI pipeline (P4 alias, A5 outbound). Never posted on its own."""

    kind: str
    file: str
    line: int
    detail: str

    def to_dict(self) -> dict:
        return asdict(self)


def validate_finding(data: dict, valid_rules: frozenset[str] | None = None) -> Finding:
    """Builds a `Finding` from untrusted data, raising `FindingError` with the reason."""
    if not isinstance(data, dict):
        raise FindingError("not an object")
    for key in ("rule", "severity", "source", "file", "message", "suggestion"):
        value = data.get(key)
        if not isinstance(value, str) or not value.strip():
            raise FindingError(f"missing {key}")
    if not RULE_PATTERN.match(data["rule"]):
        raise FindingError(f"malformed rule {data['rule']!r}")
    if valid_rules is not None and data["rule"] not in valid_rules:
        raise FindingError(f"unknown rule {data['rule']}")
    if data["severity"] not in SEVERITIES:
        raise FindingError(f"unknown severity {data['severity']!r}")
    line = data.get("line")
    if line is not None and (not isinstance(line, int) or isinstance(line, bool) or line < 1):
        raise FindingError(f"invalid line {line!r}")
    unknown = set(data) - {"rule", "severity", "source", "check", "file", "line", "message", "suggestion"}
    if unknown:
        raise FindingError(f"unknown fields {sorted(unknown)}")
    return Finding(
        rule=data["rule"],
        severity=data["severity"],
        source=data["source"],
        file=data["file"],
        message=data["message"].strip(),
        suggestion=data["suggestion"].strip(),
        line=line,
        check=data.get("check") or "",
    )


def sort_findings(findings: list[Finding]) -> list[Finding]:
    return sorted(findings, key=lambda f: (SEVERITY_RANK[f.severity], f.file, f.line or 0, f.rule))


def write_json(path: Path, items: list) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps([i.to_dict() for i in items], indent=2), encoding="utf-8")


def read_findings(path: Path) -> list[Finding]:
    return [validate_finding(d) for d in json.loads(path.read_text(encoding="utf-8"))]


def read_signals(path: Path) -> list[Signal]:
    if not path.exists():
        return []
    return [Signal(**d) for d in json.loads(path.read_text(encoding="utf-8"))]
