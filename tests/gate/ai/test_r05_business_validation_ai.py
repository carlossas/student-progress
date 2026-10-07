import pytest

from tests.gate.helpers import FIXTURES, ai_findings, by_rule, requires_gemini

pytestmark = [pytest.mark.ai, requires_gemini]


def test_r05_business_validation_ai():
    violation = by_rule(ai_findings(FIXTURES / "r05-ai" / "violation"), "AGENTS#5")
    assert {f.severity for f in violation} & {"high"}, violation
    assert len(violation) >= 2  # score range and unknown lesson
    compliant = by_rule(ai_findings(FIXTURES / "r05-ai" / "compliant"), "AGENTS#5")
    assert compliant == [], compliant
