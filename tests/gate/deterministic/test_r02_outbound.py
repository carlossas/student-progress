from gate.deterministic import pii_flow
from gate.diff import DiffContext
from tests.gate.helpers import FIXTURES, by_rule, expected, located


def test_r02_outbound_minors_data():
    violation = FIXTURES / "r02" / "violation"
    findings = by_rule(pii_flow.check(DiffContext.from_fixture(violation)), "AGENTS#2")
    assert located(findings) == expected(violation)
    assert [f.severity for f in findings] == ["critical"]

    # Compliant: nothing posted, but the new outbound channel is a signal for the AI (A5).
    compliant = DiffContext.from_fixture(FIXTURES / "r02" / "compliant")
    assert pii_flow.check(compliant) == []
    signals = pii_flow.outbound_signals(compliant)
    assert {s.kind for s in signals} == {"A5"}
    assert any("httpx" in s.detail for s in signals)
