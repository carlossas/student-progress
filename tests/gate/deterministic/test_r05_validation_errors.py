from gate.deterministic import lint, validation
from gate.diff import DiffContext
from gate.report.merge import dedupe
from tests.gate.helpers import FIXTURES, by_rule, expected, located


def run(root):
    ctx = DiffContext.from_fixture(root)
    return by_rule(dedupe(validation.check(ctx) + lint.check(ctx)), "AGENTS#5")


def test_r05_validation_errors():
    violation = FIXTURES / "r05" / "violation"
    findings = run(violation)

    assert located(findings) == expected(violation)
    assert {f.severity for f in findings} == {"high"}
    assert any("Pydantic" in f.suggestion for f in findings if f.check == "A7")

    assert run(FIXTURES / "r05" / "compliant") == []
