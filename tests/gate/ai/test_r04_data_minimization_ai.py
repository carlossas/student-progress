import pytest

from tests.gate.helpers import FIXTURES, ai_findings, by_rule, requires_gemini

pytestmark = [pytest.mark.ai, requires_gemini]


def test_r04_data_minimization_ai():
    violation = by_rule(ai_findings(FIXTURES / "r04-ai" / "violation"), "AGENTS#4")
    assert {f.severity for f in violation} & {"critical"}, violation
    assert {f.file for f in violation} == {"app/support.py"}
    compliant = by_rule(ai_findings(FIXTURES / "r04-ai" / "compliant"), "AGENTS#4")
    assert compliant == [], compliant
