import pytest

from tests.gate.helpers import FIXTURES, ai_findings, by_rule, requires_gemini

pytestmark = [pytest.mark.ai, requires_gemini]


def test_r03_secondary_copies_ai():
    violation = by_rule(ai_findings(FIXTURES / "r03-ai" / "violation"), "AGENTS#3")
    assert {f.severity for f in violation} & {"critical"}, violation

    compliant = by_rule(ai_findings(FIXTURES / "r03-ai" / "compliant"), "AGENTS#3")
    assert compliant == [], compliant
