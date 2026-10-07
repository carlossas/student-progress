import pytest

from tests.gate.helpers import FIXTURES, ai_findings, by_rule, requires_gemini

pytestmark = [pytest.mark.ai, requires_gemini]


def test_r09_logic_bugs_style_ai():
    violation = by_rule(ai_findings(FIXTURES / "r09-ai" / "violation"), "AGENTS#9")
    assert {f.severity for f in violation} & {"high"}, violation
    assert any(f.severity == "low" for f in violation)  # naming: x2
    compliant = by_rule(ai_findings(FIXTURES / "r09-ai" / "compliant"), "AGENTS#9")
    assert not [f for f in compliant if f.severity in ("critical", "high")], compliant
