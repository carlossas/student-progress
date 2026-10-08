from gate.deterministic import retention
from gate.diff import DiffContext
from tests.gate.helpers import FIXTURES, by_rule, expected, located


def test_r03_retention():
    violation = FIXTURES / "r03" / "violation"
    findings = by_rule(retention.check(DiffContext.from_fixture(violation)), "AGENTS#3")

    assert located(findings) == expected(violation)
    by_check = {f.check: f for f in findings}
    assert by_check["A3"].severity == "critical"
    assert "90" in by_check["A3"].suggestion
    assert by_check["A4"].severity == "high"

    assert retention.check(DiffContext.from_fixture(FIXTURES / "r03" / "compliant")) == []
