import pytest

from tests.gate.helpers import FIXTURES, ai_findings, by_rule, requires_gemini

pytestmark = [pytest.mark.ai, requires_gemini]


def test_r01_pii_exposure_ai():
    violation = by_rule(ai_findings(FIXTURES / "r01-ai" / "violation"), "AGENTS#1")
    assert {f.severity for f in violation} & {"critical"}, violation
    assert len([f for f in violation if f.severity == "critical"]) >= 3
    assert {f.file for f in violation} <= {"app/main.py", "app/notify.py"}
    compliant = by_rule(ai_findings(FIXTURES / "r01-ai" / "compliant"), "AGENTS#1")
    assert compliant == [], compliant
