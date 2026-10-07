import json

import pytest

from gate.report.adapters import (
    UnmappedRuleError,
    coverage_findings,
    junit_failures,
    ruff_findings,
    vulture_findings,
)
from gate.report.finding import SCHEMA_PATH, validate_finding
from tests.gate.helpers import FIXTURES

R11 = FIXTURES / "r11"


def read(name):
    return (R11 / name).read_text(encoding="utf-8")


def test_r11_finding_schema():
    # Violation input: an unmapped tool rule id must raise, never be dropped silently.
    with pytest.raises(UnmappedRuleError):
        ruff_findings(read("ruff-unmapped.json"), R11)

    # Compliant input: every mapped item becomes a schema-valid, actionable finding.
    findings = (
        ruff_findings(read("ruff.json"), R11)
        + vulture_findings(read("vulture.txt"), R11)
        + junit_failures(read("junit.xml"), R11)
        + coverage_findings(read("coverage.xml"), R11, {"app/main.py": {10, 11, 12, 13}})
    )

    required = set(json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))["required"])
    assert [(f.rule, f.severity, f.check) for f in findings] == [
        ("AGENTS#5", "high", "A6"),  # E722
        ("AGENTS#7", "medium", "A11"),  # F401
        ("AGENTS#7", "low", "A13"),  # E501
        ("AGENTS#7", "medium", "A11"),  # unreachable (unused variable is ruff's job)
        ("AGENTS#6", "high", "A8"),  # failing test
        ("AGENTS#6", "high", "A10"),  # 50% changed-line coverage
    ]
    for finding in findings:
        data = finding.to_dict()
        assert required <= {k for k, v in data.items() if v}
        assert validate_finding(data) == finding
        assert finding.file and finding.suggestion
