"""Converts external tool output (ruff, vulture, pytest, coverage) into findings.

Every tool rule id goes through `gate/config/rule_map.yml`; an unmapped id raises instead
of being dropped (AGENTS#5, AGENTS#11).
"""

from __future__ import annotations

import json
import re
import xml.etree.ElementTree as ET
from functools import lru_cache
from pathlib import Path

import yaml

from gate.config import COVERAGE_PACKAGES, COVERAGE_THRESHOLD, RULE_MAP
from gate.report.finding import Finding


class UnmappedRuleError(KeyError):
    """A tool reported a rule id that rule_map.yml does not classify."""


@lru_cache
def _rule_map(path: Path = RULE_MAP) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def lookup(tool: str, code: str) -> dict:
    table = _rule_map().get(tool, {})
    if code in table:
        return table[code]
    prefixes = [k for k in table if k.endswith("*") and code.startswith(k[:-1])]
    if prefixes:
        return table[max(prefixes, key=len)]
    raise UnmappedRuleError(f"{tool} rule {code!r} is not mapped in rule_map.yml")


def _finding(tool: str, code: str, file: str, line: int | None, message: str, suggestion: str | None = None) -> Finding:
    entry = lookup(tool, code)
    return Finding(
        rule=entry["rule"],
        severity=entry["severity"],
        source=f"deterministic:{tool}",
        check=entry["check"],
        file=file,
        line=line,
        message=message,
        suggestion=suggestion or entry["suggestion"],
    )


def _relative(path: str, repo: Path) -> str:
    p = Path(path)
    if p.is_absolute():
        try:
            return p.resolve().relative_to(repo.resolve()).as_posix()
        except ValueError:
            return p.as_posix()
    return p.as_posix()


def ruff_findings(output: str, repo: Path) -> list[Finding]:
    """`ruff check --output-format json` output."""
    findings = []
    for item in json.loads(output or "[]"):
        fix = (item.get("fix") or {}).get("message")
        code = item.get("code") or "E999"  # syntax errors carry no code
        findings.append(
            _finding(
                "ruff",
                code,
                _relative(item["filename"], repo),
                item["location"]["row"],
                f"{code}: {item['message']}",
                f"{fix}." if fix else None,
            )
        )
    return findings


def ruff_format_findings(output: str, repo: Path) -> list[Finding]:
    """`ruff format --diff` output: one finding per reformatted hunk."""
    findings, current, old_line, reported = [], None, 0, True
    for line in output.splitlines():
        if line.startswith("--- "):
            current = _relative(line[4:].strip(), repo)
        elif line.startswith("+++ "):
            continue
        elif line.startswith("@@") and current:
            old_line, reported = int(re.match(r"^@@ -(\d+)", line).group(1)), False
        elif current and not reported and line.startswith(("-", "+")):
            # First line ruff would change (context lines precede it in the hunk).
            findings.append(
                _finding("ruff-format", "format", current, max(old_line, 1), "Code is not formatted with ruff.")
            )
            reported = True
        elif line.startswith(" "):
            old_line += 1
    return findings


def vulture_findings(output: str, repo: Path) -> list[Finding]:
    """Only unreachable code: unused imports/variables are already covered by ruff."""
    findings = []
    for line in output.splitlines():
        match = re.match(r"^(.+?):(\d+): (unreachable code.*?) \(\d+% confidence\)", line)
        if match:
            findings.append(
                _finding(
                    "vulture",
                    "unreachable",
                    _relative(match.group(1), repo),
                    int(match.group(2)),
                    match.group(3).capitalize() + ".",
                )
            )
    return findings


def junit_failures(xml_text: str, repo: Path) -> list[Finding]:
    """Failing/erroring tests from a pytest JUnit report (junit_family=xunit1)."""
    findings = []
    for case in ET.fromstring(xml_text).iter("testcase"):
        problem = case.find("failure")
        if problem is None:
            problem = case.find("error")
        if problem is None:
            continue
        file = case.get("file") or case.get("classname", "").replace(".", "/") + ".py"
        line = int(case.get("line")) + 1 if case.get("line") else None
        reason = (problem.get("message") or "").splitlines()[0][:200] if problem.get("message") else "failed"
        findings.append(
            _finding("pytest", "failure", _relative(file, repo), line, f"Test `{case.get('name')}` fails: {reason}")
        )
    return findings


def coverage_by_file(xml_text: str, repo: Path) -> dict[str, dict[int, int]]:
    """{repo-relative file: {line: hits}} from a Cobertura coverage.xml."""
    root = ET.fromstring(xml_text)
    sources = [Path(s.text) for s in root.iter("source") if s.text]
    result: dict[str, dict[int, int]] = {}
    for cls in root.iter("class"):
        filename = cls.get("filename", "")
        candidates = [src / filename for src in sources] + [repo / filename]
        path = next((c for c in candidates if c.is_file()), candidates[-1])
        rel = _relative(str(path), repo)
        result[rel] = {int(ln.get("number")): int(ln.get("hits")) for ln in cls.iter("line")}
    return result


def coverage_findings(xml_text: str, repo: Path, changed: dict[str, set[int]]) -> list[Finding]:
    """High finding per file with uncovered changed lines when changed-line coverage < threshold."""
    coverage = coverage_by_file(xml_text, repo)
    executable, uncovered = 0, {}
    for file, lines in changed.items():
        if file.split("/", 1)[0] not in COVERAGE_PACKAGES or file not in coverage:
            continue
        measured = {n: h for n, h in coverage[file].items() if n in lines}
        executable += len(measured)
        missing = sorted(n for n, h in measured.items() if h == 0)
        if missing:
            uncovered[file] = missing
    if not executable:
        return []
    percent = 100 * (executable - sum(len(v) for v in uncovered.values())) / executable
    if percent >= COVERAGE_THRESHOLD:
        return []
    return [
        _finding(
            "coverage",
            "changed-lines",
            file,
            missing[0],
            f"Changed-line coverage is {percent:.0f}% (minimum {COVERAGE_THRESHOLD:.0f}%). "
            f"Uncovered lines: {', '.join(map(str, missing))}.",
        )
        for file, missing in uncovered.items()
    ]
