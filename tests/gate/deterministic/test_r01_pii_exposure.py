from gate.deterministic import pii_flow, pii_registry
from gate.diff import DiffContext
from tests.gate.helpers import FIXTURES, by_rule, expected, located


def run(root):
    ctx = DiffContext.from_fixture(root)
    return by_rule(pii_registry.check(ctx) + pii_flow.check(ctx), "AGENTS#1")


def test_r01_pii_exposure():
    violation = FIXTURES / "r01" / "violation"
    findings = run(violation)

    # One Critical per violation line: phone not registered, email logged, email returned,
    # asdict(student) logged, f"{student}" in an exception message.
    assert located(findings) == expected(violation)
    assert len(findings) == 5
    assert {f.severity for f in findings} == {"critical"}
    assert {f.check for f in findings} == {"P1", "P2", "P3"}
    assert all(
        "redact" in f.suggestion or "PII_FIELDS" in f.suggestion or "student_id" in f.suggestion for f in findings
    )

    assert run(FIXTURES / "r01" / "compliant") == []
